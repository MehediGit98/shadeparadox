"""Independent regression checks; standard library unittest, no pytest required."""
from pathlib import Path
import itertools, json, math, sys, unittest
import numpy as np
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'master' if (ROOT/'master').exists() else ROOT/'source'
for name in ['streetlux','shadeparadox','specdebt']:
    if (SOURCE/name).exists():sys.path.insert(0,str(SOURCE/name))

class SharedChecks(unittest.TestCase):
    def test_spectral_reference(self):
        from streetlux.reference_data import load_publication_references
        from streetlux import photometry,self_check,spectra
        load_publication_references(SOURCE/'reference_data')
        self.assertEqual(photometry.K_MEL_V_D65_OFFICIAL,.0013262)
        self.assertTrue(spectra.provenance()['official_action_spectra'])
        self.assertLess(abs(self_check()['der_d65']-1),.001)

    def test_strict_json(self):
        from streetlux.jsonio import dumps
        self.assertEqual(json.loads(dumps({'undefined':float('nan'),'infinite':float('inf')})),{'undefined':None,'infinite':None})

class StreetChecks(unittest.TestCase):
    def route(self):
        from streetlux.route import load_route
        return load_route(SOURCE/'streetlux/examples/dhaka_mirpur_motijheel.json')

    def test_design_invariants(self):
        from streetlux.scenarios import STANDARD_SCENARIOS
        route=self.route(); scenarios={s.key:s for s in STANDARD_SCENARIOS}
        for old,new in zip(route.sections,scenarios['widen_18'].apply(route).sections):
            self.assertGreaterEqual(new.width_m,old.width_m); new.validate()
            self.assertEqual(new.eye_offset_m,old.eye_offset_m)
        under=route.sections[3]
        for key in ['canopy_40','canopy_70']:
            new=scenarios[key].apply(route).sections[3]
            self.assertEqual(new.canopy,under.canopy)
        new=scenarios['pale_paving'].apply(route)
        self.assertEqual(new.sections[0].ground_material,'brick_pavement')
        self.assertEqual(new.sections[1].ground_material,'concrete_pavement')

    def test_invalid_eye_location(self):
        r=self.route(); r.sections[0].eye_offset_m=100
        with self.assertRaises(ValueError):r.sections[0].validate()

    def test_pareto_indices(self):
        from streetlux.scenarios import pareto_front
        rows=[{'objectives':{'x':1,'y':2}},{'objectives':{'x':4,'y':4}},{'objectives':{'x':2,'y':1}}]
        self.assertEqual(pareto_front(rows,('x','y')),[1])

@unittest.skipUnless((SOURCE/'specdebt').exists(),'SpecDebt not included')
class SpecDebtChecks(unittest.TestCase):
    def example(self):
        from specdebt.spec import Specification
        from specdebt.study import run_study,Threshold
        sp=Specification(name='interaction');sp.add('a',(0,1),'Binary levels for interaction regression');sp.add('b',(0,1),'Binary levels for interaction regression');sp.add('inert',(0,1),'Binary levels for interaction regression')
        return run_study(lambda s:s['a']^s['b'],sp,Threshold(.5),'XOR')

    def test_interactions_require_joint_declaration(self):
        r=self.example();self.assertEqual(r.flip_rate(),.5)
        self.assertEqual(len(r.minimum_declaration_set(0)['set']),2)
        self.assertEqual([x['residual_flip_rate'] for x in r.sufficiency_curve()],[.5,.5,0,0])

    def test_fail_fast(self):
        from specdebt.study import run_study,Threshold
        sp=self.example().spec
        with self.assertRaises(ValueError):run_study(lambda s:float('nan'),sp,Threshold(.5),'bad')
        with self.assertRaises(RuntimeError):run_study(lambda s:1/0,sp,Threshold(.5),'bad')

    def test_ties_are_distinct(self):
        from specdebt.spec import Specification
        from specdebt.study import run_study,Comparison
        sp=Specification(name='ties');sp.add('x',(-1,0,1),'Negative, zero and positive comparison scores')
        r=run_study(lambda s:s['x'],sp,Comparison(),'comparison')
        self.assertEqual(r.debt()['comparison_outcomes'],{'A_wins':1,'B_wins':1,'ties':1})
        self.assertAlmostEqual(r.flip_rate(),1/3)

    def test_weighted_residual_is_not_cell_guarantee(self):
        r=self.example()
        self.assertEqual(r.cell_residuals(('a',))['max_cell_residual'],.5)
        self.assertEqual(r.cell_residuals(('a','b'))['max_cell_residual'],0)

@unittest.skipUnless((SOURCE/'shadeparadox').exists(),'ShadeParadox not included')
class ShadeParadoxChecks(unittest.TestCase):
    """Fast regression checks of the ShadeParadox optics and controllers."""

    @classmethod
    def setUpClass(cls):
        from streetlux.reference_data import load_publication_references
        load_publication_references(SOURCE/'reference_data')

    def _state(self,room,month,day,hour,cloud):
        from shadeparadox.sim import geometry_for,sky_for,Site
        geo=geometry_for(room,256); sky,dome=sky_for(Site(),geo,2026,month,day,hour,cloud)
        return geo,sky,dome

    def test_partial_coverage_matches_equivalent_smaller_window(self):
        """An opaque shade over the top 25% of the window must light the room
        about as much as a window whose head is lowered by that amount.  The
        uncovered aperture was once attenuated twice (ratios 0.78-0.83); the
        corrected model gives 0.93-0.98 (the rest is patch geometry)."""
        from shadeparadox.optics import ShadeDevice,solve
        from shadeparadox.experiment import _room
        op=ShadeDevice('opaque','opaque','bronze_tinted',openness=0.0,diffuse_transmittance=0.0)
        for ori,month,day,hour,cloud in [(270,4,15,10.25,.30),(0,1,15,9.25,.15),(270,7,15,15.75,.80)]:
            room=_room(ori,2.5); geo,sky,dome=self._state(room,month,day,hour,cloud)
            with_shade=solve(room,geo,dome,sky,op,0.25,0.0)
            room2=_room(ori,2.5,window_head_m=op.covered_band(room,0.25))
            geo2,sky2,dome2=self._state(room2,month,day,hour,cloud)
            lowered=solve(room2,geo2,dome2,sky2,op,0.0,0.0)
            ratio=with_shade.lux_vertical/lowered.lux_vertical
            self.assertGreater(ratio,0.90,(ori,month,ratio)); self.assertLess(ratio,1.01,(ori,month,ratio))

    def test_daylight_melanopic_edi_never_increases_with_coverage(self):
        from shadeparadox.optics import SHADES,solve
        from shadeparadox.experiment import _room
        room=_room(270,2.5)
        for month,day,hour,cloud in [(4,15,10.25,.30),(7,15,15.75,.80),(1,15,16.25,.15),(10,15,12.75,.35)]:
            geo,sky,dome=self._state(room,month,day,hour,cloud)
            vals=[solve(room,geo,dome,sky,SHADES['roller_dark'],c,0.0).medi for c in (0,.25,.5,.75,1.0)]
            self.assertTrue(all(b<=a*(1+1e-9) for a,b in zip(vals,vals[1:])),vals)

    def test_stochastic_defaults_and_registry(self):
        from shadeparadox.behaviour import ControllerParams,CONTROLLERS,REFERENCE_CONTROLLERS
        p=ControllerParams(); self.assertEqual((p.stochastic_intercept,p.stochastic_slope),(-8.0,1.6))
        self.assertIn('illustrative_stochastic',CONTROLLERS); self.assertNotIn('haldi_stochastic',CONTROLLERS)
        self.assertIn('minimum_admissible_coverage',REFERENCE_CONTROLLERS)
        self.assertNotIn('minimum_admissible_coverage',CONTROLLERS)

    def _run(self,key,seed=0,params=None,ori=270,depth=2.5):
        from shadeparadox.behaviour import ControllerParams,controller
        from shadeparadox.experiment import _room
        from shadeparadox.optics import SHADES
        from shadeparadox.sim import run
        return run(_room(ori,depth),lambda s:controller(key,params or ControllerParams(),s),SHADES['roller_dark'],n_directions=128,dt_h=1.0,seed=seed).aggregates()

    def test_runs_are_deterministic(self):
        a=self._run('illustrative_stochastic',3); b=self._run('illustrative_stochastic',3)
        self.assertEqual(a,b)

    def test_persistent_controller_counts_each_event_once(self):
        """Four dates contain eight arrivals, not 2 + 4 + 6 + 8 arrivals.

        Date weights affect exposure summaries, not raw diagnostic counts.
        The controller's lifetime counters and state must not be reset.
        """
        from shadeparadox.behaviour import controller
        from shadeparadox.experiment import _room
        from shadeparadox.optics import SHADES
        from shadeparadox.sim import run
        ctrl=controller('always_open')
        result=run(_room(270,2.5),lambda seed:ctrl,SHADES['roller_dark'],
                   n_directions=64,dt_h=0.5)
        self.assertEqual([d.counters['arrivals'] for d in result.days],[2]*4)
        self.assertEqual([d.counters['steps_evaluated'] for d in result.days],[24]*4)
        total=result.aggregates()['counters']
        self.assertEqual(total['arrivals'],8)
        self.assertEqual(total['steps_evaluated'],96)
        self.assertEqual(total,ctrl.counters)

    def test_independent_controllers_also_sum_all_dates(self):
        """Taking only the last cumulative snapshot would fail this case."""
        from shadeparadox.behaviour import controller,Occupancy
        from shadeparadox.experiment import _room
        from shadeparadox.metrics import EnergyModel
        from shadeparadox.optics import SHADES
        from shadeparadox.sim import RunResult,REPRESENTATIVE_DAYS,Site,geometry_for,simulate_day
        room=_room(270,2.5); geo=geometry_for(room,64)
        result=RunResult(room=room.name,controller='always_open',
                         controller_label='Blinds never operated',shade='roller_dark',dt_h=0.5)
        for d in REPRESENTATIVE_DAYS:
            result.days.append(simulate_day(
                room,geo,controller('always_open'),SHADES['roller_dark'],Site(),
                2026,d['month'],d['day'],d['cloud'],Occupancy(),EnergyModel(),
                dt_h=0.5,day_key=d['key'],weight=d['weight']))
        self.assertEqual([d.counters['arrivals'] for d in result.days],[2]*4)
        self.assertEqual(result.aggregates()['counters']['arrivals'],8)
        self.assertEqual(result.aggregates()['counters']['steps_evaluated'],96)

    def test_empty_date_does_not_repeat_previous_events(self):
        from shadeparadox.behaviour import controller,Occupancy
        from shadeparadox.experiment import _room
        from shadeparadox.metrics import EnergyModel
        from shadeparadox.optics import SHADES
        from shadeparadox.sim import Site,geometry_for,simulate_day
        room=_room(270,2.5); geo=geometry_for(room,64)
        ctrl=controller('always_open')
        args=(room,geo,ctrl,SHADES['roller_dark'],Site(),2026,1,15,0.15,
              Occupancy(),EnergyModel())
        first=simulate_day(*args)
        before=dict(ctrl.counters)
        empty=simulate_day(*args,start_h=7.0,end_h=7.0)
        self.assertEqual(empty.steps,[])
        self.assertEqual(empty.counters,{key:0 for key in before})
        self.assertEqual(ctrl.counters,before)
        self.assertEqual(first.counters['arrivals'],2)

    def test_melanopic_rule_equals_memoryless_minimum_coverage(self):
        keys=('medi_mean','frac_dgp_above_035','electric_kwh','mean_coverage')
        for seed in (0,1):
            a=self._run('circadian_aware',seed); b=self._run('minimum_admissible_coverage',seed)
            for k in keys:self.assertAlmostEqual(a[k],b[k],places=9,msg=(seed,k))

    def test_intercept_controls_closing(self):
        from shadeparadox.behaviour import ControllerParams
        base=self._run('always_open')['medi_mean']
        low=self._run('illustrative_stochastic',2,ControllerParams(stochastic_intercept=-10.0))['medi_mean']/base
        high=self._run('illustrative_stochastic',2,ControllerParams(stochastic_intercept=-6.0))['medi_mean']/base
        self.assertGreater(low,high)

    def test_glare_and_solar_never_closes_more_than_needed_when_deep(self):
        """Deep cells never exceed the glare/solar limits, so no closure occurs."""
        r=self._run('glare_only',0,ori=180,depth=6.5); o=self._run('always_open',0,ori=180,depth=6.5)
        self.assertEqual(r['medi_mean'],o['medi_mean'])

if __name__=='__main__':unittest.main(verbosity=2)
