"""
Sensitivity analyses that qualify the E1, E2 and E3 results.

Each function performs one model sensitivity or diagnostic check:

``stochastic_intercept_sweep``
    How the mEDI retained by the illustrative stochastic rule depends on the
    assumed intercept of its closing logit.
``independent_dates``
    E1 repeated with a freshly initialised controller on each representative
    date, so that no blind state is carried between dates.
``heading_convergence``
    The E3 heading ratio recomputed at several angular resolutions.
``melanopic_equivalence``
    Whether the melanopic-aware rule ever behaves differently from the
    memoryless smallest-admissible-coverage rule, and an audit of whether
    melanopic EDI ever increases with coverage.
``e2_full_window``
    The E2 routine run with the full E1/E3 window instead of the reduced
    window used for the default (degenerate) E2 cell.  Exploratory: one
    optimiser seed, so no comparative claim is drawn from it.

All functions are deterministic.  ``run_all(e1)`` runs every analysis and
reuses the always-open baselines already computed by E1.
"""

from __future__ import annotations

import time

import numpy as np

from .behaviour import Controller, ControllerParams, Occupancy, controller
from .experiment import _room, e2_encoding_vs_algorithm
from .metrics import EnergyModel
from .optics import SHADES
from .sim import (REPRESENTATIVE_DAYS, RunResult, Site, geometry_for, run,
                  simulate_day)

ORIENTATIONS = (0, 90, 180, 270)
DEPTHS = (2.5, 4.5, 6.5)
SEEDS = (0, 1, 2, 3, 4)
INTERCEPTS = (-10, -9.5, -9, -8.5, -8, -7, -6)


def _cells(orientations, depths):
    return [(o, d) for o in orientations for d in depths]


def _agg(room, key, seed, shade, n_directions, dt_h, params=None):
    return run(room, lambda s: controller(key, params or ControllerParams(), s),
               shade, n_directions=n_directions, dt_h=dt_h,
               seed=seed).aggregates()


def baseline_from_e1(e1: dict) -> dict:
    """Always-open mean mEDI per (orientation, depth, seed) from an E1 result."""
    return {(r["orientation_deg"], r["depth_m"], s["seed"]): s["medi_mean"]
            for r in e1["rows"] if r["controller"] == "always_open"
            for s in r["per_seed"]}


def stochastic_intercept_sweep(intercepts=INTERCEPTS, slope: float = 1.6,
                               orientations=ORIENTATIONS, depths=DEPTHS,
                               seeds=SEEDS, shade_key="roller_dark",
                               n_directions: int = 256, dt_h: float = 0.5,
                               baseline: dict | None = None) -> dict:
    shade = SHADES[shade_key]
    cells = _cells(orientations, depths)
    base = baseline or {
        (o, d, s): _agg(_room(o, d), "always_open", s, shade, n_directions,
                        dt_h)["medi_mean"] for (o, d) in cells for s in seeds}
    rows = []
    for a in intercepts:
        p = ControllerParams(stochastic_intercept=float(a),
                             stochastic_slope=float(slope))
        by_seed = []
        for s in seeds:
            ret = [_agg(_room(o, d), "illustrative_stochastic", s, shade,
                        n_directions, dt_h, p)["medi_mean"] / base[(o, d, s)]
                   for (o, d) in cells]
            by_seed.append(float(np.mean(ret)))
        rows.append({"intercept": float(a), "slope": float(slope),
                     "medi_retained": float(np.mean(by_seed)),
                     "medi_retained_by_seed": by_seed})
    return {"analysis": "stochastic_intercept_sweep",
            "controller": "illustrative_stochastic",
            "default_intercept": ControllerParams().stochastic_intercept,
            "default_slope": ControllerParams().stochastic_slope,
            "seeds": list(seeds), "n_cells": len(cells), "rows": rows}


def _run_independent_dates(room, key, seed, shade, n_directions, dt_h):
    geo = geometry_for(room, n_directions)
    site, occ, en = Site(), Occupancy(), EnergyModel()
    res = RunResult(room=room.name, controller=key, controller_label=key,
                    shade=shade.key, dt_h=dt_h)
    for i, d in enumerate(REPRESENTATIVE_DAYS):
        # a separate, deterministically seeded controller for every date
        c = controller(key, ControllerParams(), seed * 100 + i)
        res.days.append(simulate_day(
            room, geo, c, shade, site, 2026, d["month"], d["day"], d["cloud"],
            occ, en, dt_h=dt_h, day_key=d["key"], weight=d["weight"]))
    return res.aggregates()


def independent_dates(controllers=("glare_only", "thermal_only",
                                   "illustrative_stochastic",
                                   "circadian_aware"),
                      orientations=ORIENTATIONS, depths=DEPTHS, seeds=SEEDS,
                      shade_key="roller_dark", n_directions: int = 256,
                      dt_h: float = 0.5) -> dict:
    shade = SHADES[shade_key]
    cells = _cells(orientations, depths)
    base = {(o, d, s): _run_independent_dates(_room(o, d), "always_open", s,
                                              shade, n_directions, dt_h)
            for (o, d) in cells for s in seeds}
    out = {}
    for ck in controllers:
        per_seed = []
        for s in seeds:
            r, g, c = [], [], []
            for (o, d) in cells:
                a = _run_independent_dates(_room(o, d), ck, s, shade,
                                           n_directions, dt_h)
                b = base[(o, d, s)]
                r.append(a["medi_mean"] / b["medi_mean"])
                g.append(100.0 * (a["frac_dgp_above_035"]
                                  - b["frac_dgp_above_035"]))
                c.append(100.0 * (a["frac_medi_above_250"]
                                  - b["frac_medi_above_250"]))
            per_seed.append((float(np.mean(r)), float(np.mean(g)),
                             float(np.mean(c))))
        m = np.mean(per_seed, axis=0)
        out[ck] = {"medi_retained": float(m[0]),
                   "dgp_delta_pp": float(m[1]),
                   "compliance_delta_pp": float(m[2]),
                   "medi_retained_by_seed": [x[0] for x in per_seed]}
    return {"analysis": "independent_dates", "seeds": list(seeds),
            "n_cells": len(cells),
            "seed_rule": "controller seed = 100 * behavioural seed + date index",
            "controllers": out}


def heading_convergence(orientation=270, depth=2.5, n_headings: int = 12,
                        controllers=("thermal_and_glare", "circadian_aware",
                                     "illustrative_stochastic"),
                        n_directions_open=(128, 256, 512, 1024, 2048),
                        n_directions_controlled=(128, 256, 512, 1024),
                        seed: int = 0, shade_key="roller_dark",
                        dt_h: float = 0.5) -> dict:
    shade = SHADES[shade_key]
    headings = [orientation - 180.0 + i * (360.0 / n_headings)
                for i in range(n_headings)]

    def sweep(key, n):
        m, cv = [], []
        for h in headings:
            a = _agg(_room(orientation, depth, view_heading_deg=h), key, seed,
                     shade, n, dt_h)
            m.append(a["medi_mean"])
            cv.append(a["mean_coverage"])
        return {"n_directions": n, "medi_min": float(min(m)),
                "medi_max": float(max(m)),
                "medi_ratio": float(max(m) / min(m)),
                "coverage_range_pp": float(100.0 * (max(cv) - min(cv)))}

    out = {"always_open": [sweep("always_open", n) for n in n_directions_open]}
    for ck in controllers:
        out[ck] = [sweep(ck, n) for n in n_directions_controlled]
    return {"analysis": "heading_convergence", "seed": seed,
            "orientation_deg": orientation, "depth_m": depth,
            "n_headings": n_headings, "results": out}


def melanopic_equivalence(orientations=ORIENTATIONS, depths=DEPTHS,
                          seeds=SEEDS, shade_key="roller_dark",
                          n_directions: int = 256, dt_h: float = 0.5,
                          audit_seed: int = 0) -> dict:
    shade = SHADES[shade_key]
    cells = _cells(orientations, depths)
    keys = ("medi_mean", "frac_dgp_above_035", "electric_kwh", "mean_coverage")
    runs = differing = 0
    max_abs = 0.0
    for (o, d) in cells:
        room = _room(o, d)
        for s in seeds:
            a = _agg(room, "circadian_aware", s, shade, n_directions, dt_h)
            b = _agg(room, "minimum_admissible_coverage", s, shade,
                     n_directions, dt_h)
            diff = max(abs(a[k] - b[k]) for k in keys)
            runs += 1
            differing += int(diff > 1e-9)
            max_abs = max(max_abs, diff)

    records: list = []

    class _Audit(Controller):
        key, label = "audit", "audit (probes every coverage, keeps blind open)"

        def act(self, probe, t, occupied):
            self.arrival(occupied)
            if not occupied:
                return self._settle(probe, 0.0)
            cands = [(c, self._settle(probe, c)) for c in self._allowed()]
            records.append([(c, m.medi, m.dgp, m.solar_on_occupant_w_m2)
                            for c, m in cands])
            self._set(0.0)
            return cands[0][1]

    p = ControllerParams()
    for (o, d) in cells:
        run(_room(o, d), lambda s: _Audit(ControllerParams(), s), shade,
            n_directions=n_directions, dt_h=dt_h, seed=audit_seed)
    non_monotone = argmax_differs = 0
    worst_rise = 0.0
    for rec in records:
        meds = [x[1] for x in rec]
        for u, v in zip(meds, meds[1:]):
            if v > u + 1e-9:
                non_monotone += 1
                worst_rise = max(worst_rise, (v - u) / max(u, 1e-9))
                break
        ok = [x for x in rec
              if x[2] <= p.dgp_close and x[3] <= p.solar_close_w_m2]
        if ok:
            best = max(ok, key=lambda x: x[1])
            smallest = min(ok, key=lambda x: x[0])
            argmax_differs += int(abs(best[0] - smallest[0]) > 1e-9)
    return {"analysis": "melanopic_equivalence",
            "comparison_rule": "minimum_admissible_coverage",
            "runs_compared": runs, "runs_differing": differing,
            "max_abs_difference": float(max_abs),
            "audit_seed": audit_seed,
            "occupied_steps_audited": len(records),
            "steps_with_medi_increasing_in_coverage": non_monotone,
            "worst_relative_rise": float(worst_rise),
            "steps_where_highest_medi_admissible_is_not_smallest": argmax_differs}


def e2_full_window(orientation=270, depth=2.5, budget: int = 16,
                   n_directions: int = 192, dt_h: float = 0.5,
                   shade_key="roller_dark") -> dict:
    out = {}
    for label, days in (("april_july", None),
                        ("all_four", list(REPRESENTATIVE_DAYS))):
        r = e2_encoding_vs_algorithm(
            orientation=orientation, depth=depth, shade_key=shade_key,
            budget=budget, n_directions=n_directions, dt_h=dt_h, days=days,
            window_width_frac=0.85, window_head_m=2.7)
        keep = {k: r[k] for k in (
            "dispersion_from_algorithm", "dispersion_from_encoding",
            "encoding_over_algorithm_ratio", "distinct_outcomes_per_encoding",
            "distinct_outcomes_per_optimiser", "parameter_sensitivity",
            "degenerate_outcome_dims", "unique_evaluations", "days",
            "window_width_frac", "window_head_m")}
        keep["cells"] = [{k: c[k] for k in ("encoding", "optimiser", "outcome",
                                            "params")} for c in r["cells"]]
        out[label] = keep
    return {"analysis": "e2_full_window", "orientation_deg": orientation,
            "depth_m": depth, "budget": budget, "optimiser_seed": 11,
            "exploratory": True, "results": out}


def model_diagnostics(shade_key="roller_dark", n_directions: int = 256,
                      dt_h: float = 0.5) -> dict:
    """
    Model properties computed directly from the simulation and reference data.

    * ``dgp_illuminance_term``: for open-blind runs, the share of occupied
      time with DGP >= 0.35 that the vertical-illuminance term of the DGP
      formula (5.87e-5 Ev + 0.16) reaches on its own.
    * ``shade_transmittance``: D65-weighted transmittance of the fabric and of
      a fully lowered shade relative to clear glazing.
    * ``fixed_load``: the cooling-plant electricity attributed to the fixed
      envelope and internal gains per occupied day.
    * ``materials_550nm``: reflectances at 550 nm of the room materials.
    """
    from streetlux import spectra
    shade = SHADES[shade_key]
    cells = ((270, 2.5), (0, 2.5), (90, 2.5), (0, 4.5))
    share = []
    for (o, d) in cells:
        r = run(_room(o, d), lambda s: controller("always_open",
                ControllerParams(), s), shade, n_directions=n_directions,
                dt_h=dt_h, seed=0)
        tot = ev_only = wsum = 0.0
        for day in r.days:
            for st in day.steps:
                if not st.occupied:
                    continue
                wsum += day.weight
                if st.dgp >= 0.35:
                    tot += day.weight
                    if 5.87e-5 * st.lux_vertical + 0.16 >= 0.35:
                        ev_only += day.weight
        share.append({"orientation_deg": o, "depth_m": d,
                      "frac_time_dgp_ge_035": tot / wsum,
                      "share_reached_by_illuminance_term":
                          ev_only / max(tot, 1e-12)})
    v, s_mel, d65 = spectra.V_LAMBDA, spectra.S_MEL, spectra.d65()

    def eff(tau, w):
        return float(np.trapezoid(tau * w * d65, spectra.WL)
                     / np.trapezoid(w * d65, spectra.WL))

    clear = spectra.glazing("clear_float")
    fab = spectra.glazing(shade.fabric)
    closed = (shade.diffuse_transmittance * eff(fab * clear, v)
              + shade.openness * eff(clear, v)) / eff(clear, v)
    room = _room(270, 2.5)
    em = EnergyModel()
    hours = Occupancy().hours
    fixed_w = ((em.envelope_load_w_m2 + em.internal_gain_w_m2)
               * room.floor_area / em.cop_cooling * (1.0 + em.fan_fraction))
    i550 = int(np.argmin(np.abs(spectra.WL - 550.0)))
    return {
        "analysis": "model_diagnostics", "shade": shade_key,
        "dgp_illuminance_term": {
            "ev_threshold_lx": (0.35 - 0.16) / 5.87e-5, "cells": share},
        "shade_transmittance": {
            "fabric_photopic_d65": eff(fab, v),
            "fabric_melanopic_d65": eff(fab, s_mel),
            "clear_glazing_photopic_d65": eff(clear, v),
            "closed_shade_photopic_relative_to_clear": float(closed)},
        "fixed_load": {"cooling_electric_kwh_per_occupied_day":
                       float(fixed_w * hours / 1000.0),
                       "occupied_hours": float(hours),
                       "floor_area_m2": float(room.floor_area)},
        "materials_550nm": {m: float(spectra.material(m)[i550]) for m in
                            ("whitewash", "grey_concrete", "asphalt")},
        "glazing_solar_to_visible": float(room.glazing_solar_to_visible)}


def run_all(e1: dict | None = None, quick: bool = False) -> dict:
    """Run every analysis; ``quick`` shrinks grids for a smoke test only."""
    t0 = time.time()
    if quick:
        ori, dep, seeds, n, dt = (90, 270), (2.5, 6.5), (0, 1), 192, 1.0
        icpt = (-9, -8)
        n_open, n_ctrl, nh, budget = (128, 192), (128, 192), 6, 4
    else:
        ori, dep, seeds, n, dt = ORIENTATIONS, DEPTHS, SEEDS, 256, 0.5
        icpt = INTERCEPTS
        n_open, n_ctrl, nh, budget = ((128, 256, 512, 1024, 2048),
                                      (128, 256, 512, 1024), 12, 16)
    base = baseline_from_e1(e1) if (e1 and not quick) else None
    res = {"experiment": "S", "quick": quick}
    res["stochastic_intercept_sweep"] = stochastic_intercept_sweep(
        icpt, orientations=ori, depths=dep, seeds=seeds, n_directions=n,
        dt_h=dt, baseline=base)
    print("  sensitivity: intercept sweep complete", flush=True)
    res["independent_dates"] = independent_dates(
        orientations=ori, depths=dep, seeds=seeds, n_directions=n, dt_h=dt)
    print("  sensitivity: independent dates complete", flush=True)
    res["heading_convergence"] = heading_convergence(
        n_headings=nh, n_directions_open=n_open,
        n_directions_controlled=n_ctrl, dt_h=dt)
    print("  sensitivity: heading convergence complete", flush=True)
    res["melanopic_equivalence"] = melanopic_equivalence(
        orientations=ori, depths=dep, seeds=seeds, n_directions=n, dt_h=dt)
    print("  sensitivity: melanopic equivalence complete", flush=True)
    res["e2_full_window"] = e2_full_window(
        budget=budget, n_directions=192, dt_h=dt)
    print("  sensitivity: E2 full-window diagnostic complete", flush=True)
    res["model_diagnostics"] = model_diagnostics(n_directions=n, dt_h=dt)
    print("  sensitivity: model diagnostics complete", flush=True)
    res["wall_clock_s"] = round(time.time() - t0, 2)
    return res
