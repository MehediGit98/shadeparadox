"""Reproduce the additional optical and electric-light model checks.

Uses the main release's source, reference data and results. The E2 electric-
light check reruns one selected parameter set for behavioural seeds 7–9.
"""
from pathlib import Path
import argparse, json, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def run(archive_root=ROOT,results_dir=None,out_file=None):
    root = Path(archive_root).resolve()
    data = Path(results_dir) if results_dir is not None else root / "results"
    for name in ('streetlux', 'shadeparadox'):
        sys.path.insert(0, str(root / 'source' / name))
    import numpy as np
    from streetlux.reference_data import load_publication_references
    from streetlux import spectra, photometry
    from shadeparadox.experiment import _room
    from shadeparadox.behaviour import ControllerParams, controller
    from shadeparadox.optics import SHADES
    from shadeparadox.sim import run, REPRESENTATIVE_DAYS

    load_publication_references(root / 'source' / 'reference_data')
    d65 = spectra.d65()
    clear = spectra.glazing('clear_float')
    shade = SHADES['roller_dark']
    fabric = spectra.glazing(shade.fabric)
    def effective(tau, weight):
        return float(np.trapezoid(tau * weight * d65, spectra.WL)
                     / np.trapezoid(weight * d65, spectra.WL))
    clear_t = effective(clear, spectra.V_LAMBDA)
    fabric_after_clear = effective(fabric * clear, spectra.V_LAMBDA) / clear_t
    closed_t = shade.openness + shade.diffuse_transmittance * fabric_after_clear
    result = {
        'release': '0.3.2',
        'assumed_4000K_source_melanopic_DER': float(photometry.der(spectra.daylight_spd(4000))),
        'fabric_photopic_D65': effective(fabric, spectra.V_LAMBDA),
        'fabric_melanopic_D65': effective(fabric, spectra.S_MEL),
        'fabric_photopic_after_clear_glazing_D65': fabric_after_clear,
        'closed_photopic_transmission_relative_to_clear': closed_t,
        'closed_photopic_formula': '0.02 + 0.09 * fabric_photopic_after_clear_glazing_D65',
        'fixed_proxy_kWh_per_occupied_day': (18 + 12) * 48 / 3 * 1.12 * 7.5 / 1000,
    }
    e3 = json.loads((data / 'e3.json').read_text())
    result['e3_window_and_back_wall'] = {}
    for row in e3['rows']:
        result['e3_window_and_back_wall'][row['controller']] = {
            str(q['heading_deg']): {k: q[k] for k in ('medi_mean', 'mean_coverage')}
            for q in row['values'] if q['heading_deg'] in (90, 270)
        }
    e2 = json.loads((data / 'e2.json').read_text())
    cell = e2['cells'][0]
    params = ControllerParams(**cell['params'])
    room = _room(270, 6.5, window_width_frac=0.55, window_head_m=2.4)
    checks = []
    for seed in (7, 8, 9):
        sim = run(room, lambda s: controller('circadian_aware', params, s),
                  shade, n_directions=192, dt_h=0.5,
                  days=[REPRESENTATIVE_DAYS[1], REPRESENTATIVE_DAYS[2]], seed=seed)
        steps = [st for day in sim.days for st in day.steps if st.occupied]
        a = sim.aggregates()
        checks.append({
            'seed': seed, 'occupied_steps': len(steps),
            'steps_with_electric_light': sum(st.electric_fraction > 1e-10 for st in steps),
            'electric_fraction_min': min(st.electric_fraction for st in steps),
            'electric_fraction_max': max(st.electric_fraction for st in steps),
            'coverage_min': min(st.coverage for st in steps),
            'coverage_max': max(st.coverage for st in steps),
            'medi_mean': a['medi_mean'], 'total_energy_proxy_kWh': a['electric_kwh'],
        })
    result['e2_selected_solution_check'] = {
        'encoding': cell['encoding'], 'optimiser': cell['optimiser'],
        'params': cell['params'], 'runs': checks,
        'scope': 'One of the 24 archived selected parameter sets, tested over all three E2 behavioural seeds.'
    }
    if out_file is not None:
        out_file=Path(out_file)
        out_file.parent.mkdir(parents=True,exist_ok=True)
        out_file.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=ROOT/'results')
    parser.add_argument('--out-dir',type=Path,default=ROOT/'reproduced')
    parser.add_argument('--compare',action='store_true')
    args=parser.parse_args()
    output=args.out_dir.resolve()
    if output==ROOT.resolve() or any(output==(ROOT/n).resolve() or (ROOT/n).resolve() in output.parents for n in ('results','verification','source','figures','fonts','docs')):
        parser.error('--out-dir must be a fresh output directory, such as reproduced/')
    run(results_dir=args.results_dir,out_file=output/'additional_checks.json')
    print('Additional model checks written to',output/'additional_checks.json')
    if args.compare:
        from compare_results import compare_results
        count=compare_results('shadeparadox_details',ROOT/'verification',output)
        print(f'PASS: {count} numerical fields match the archived additional checks.')
