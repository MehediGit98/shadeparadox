"""Summary tables derived directly from saved results (no hand-typed values)."""

from __future__ import annotations

TABLE2_ORDER = (("always_open", "Always open"),
                ("glare_only", "Glare trigger"),
                ("thermal_only", "Solar trigger"),
                ("thermal_and_glare", "Glare or solar"),
                ("illustrative_stochastic", "Illustrative stochastic"),
                ("circadian_aware", "Melanopic-aware"))
TABLE3_ORDER = (("always_open", "Always open"),
                ("thermal_and_glare", "Glare or solar"),
                ("illustrative_stochastic", "Illustrative stochastic"),
                ("circadian_aware", "Melanopic-aware"))


def table2(e1: dict) -> list[dict]:
    rows = []
    for key, name in TABLE2_ORDER:
        c = e1["by_controller"][key]
        rows.append({
            "rule": name, "controller_key": key,
            "medi_retained_pct": round(100.0 * c["medi_retained"]["mean"], 2),
            "delta_250lx_time_pp": round(c["compliance_delta_pp"]["mean"], 2),
            "delta_glare_time_pp": round(c["dgp_delta_pp"]["mean"], 2),
            "delta_energy_pct": round(c["energy_delta_pct"]["mean"], 2),
            "cell_interval_lo_pct": round(100.0 * c["medi_retained"]["lo"], 1),
            "cell_interval_hi_pct": round(100.0 * c["medi_retained"]["hi"], 1),
            "seed_interval_lo_pct": round(
                100.0 * c["medi_retained_across_seeds"]["lo"], 1),
            "seed_interval_hi_pct": round(
                100.0 * c["medi_retained_across_seeds"]["hi"], 1)})
    return rows


def table3(e3: dict) -> list[dict]:
    by = {r["controller"]: r for r in e3["rows"]}
    rows = []
    for key, name in TABLE3_ORDER:
        r = by[key]
        rows.append({
            "rule": name, "controller_key": key,
            "medi_min_lx": round(r["medi_min"], 1),
            "medi_max_lx": round(r["medi_max"], 1),
            "ratio": round(r["medi_ratio"], 2),
            "coverage_range_pp": round(100.0 * r["coverage_range"], 2),
            "seed_ratio_lo": round(r["medi_ratio_seed_lo"], 2),
            "seed_ratio_hi": round(r["medi_ratio_seed_hi"], 2)})
    return rows


def cell_retention(e1: dict) -> list[dict]:
    """Per-cell retention (replaces a pooled interval over a designed grid)."""
    return [{"orientation_deg": r["orientation_deg"], "depth_m": r["depth_m"],
             "controller_key": r["controller"],
             "medi_retained_pct": round(100.0 * r["medi_retained"], 1)}
            for r in e1["rows"]]


def sensitivity_tables(sens: dict) -> dict[str, list[dict]]:
    sweep = [{"intercept": r["intercept"], "slope": r["slope"],
              "medi_retained_pct": round(100.0 * r["medi_retained"], 1)}
             for r in sens["stochastic_intercept_sweep"]["rows"]]
    dates = [{"controller_key": k,
              "medi_retained_pct": round(100.0 * v["medi_retained"], 1),
              "delta_glare_time_pp": round(v["dgp_delta_pp"], 2),
              "delta_250lx_time_pp": round(v["compliance_delta_pp"], 2)}
             for k, v in sens["independent_dates"]["controllers"].items()]
    conv = [{"controller_key": k, **{kk: (round(vv, 3) if isinstance(vv, float)
                                         else vv) for kk, vv in row.items()}}
            for k, rows in sens["heading_convergence"]["results"].items()
            for row in rows]
    return {"sensitivity_intercept_sweep": sweep,
            "sensitivity_independent_dates": dates,
            "sensitivity_heading_convergence": conv}
