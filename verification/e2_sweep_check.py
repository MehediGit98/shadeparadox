"""
Check E2 in four further orientation-depth cells, with both the reduced window
used for the default E2 cell and the full E1/E3 window.

The window is an explicit argument of ``e2_encoding_vs_algorithm`` and is
recorded in the output, because whether any blind closes (and therefore
whether encodings or optimisers can differ) depends on it.  These runs are
exploratory: one optimiser seed, April and July only, budget 16.

    python verification/e2_sweep_check.py --compare
    python verification/e2_sweep_check.py [output.json] [--compare]

The default destination is reproduced/e2_sweep_check.json. The archived
verification/e2_sweep_check.json is never overwritten by the default command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
sys.path.insert(0, str(SOURCE / "streetlux"))
sys.path.insert(0, str(SOURCE / "shadeparadox"))

from streetlux.reference_data import load_publication_references

load_publication_references(SOURCE / "reference_data")
from shadeparadox import __version__
from shadeparadox.experiment import e2_encoding_vs_algorithm

CELLS = ((0, 2.5), (90, 2.5), (180, 2.5), (270, 2.5))
WINDOWS = {"reduced": (0.55, 2.4), "full": (0.85, 2.7)}


def run(out_path: Path) -> dict:
    rows = []
    for window, (width_frac, head_m) in WINDOWS.items():
        for orientation, depth in CELLS:
            result = e2_encoding_vs_algorithm(
                orientation=orientation, depth=depth, budget=16,
                n_directions=192, dt_h=0.5,
                window_width_frac=width_frac, window_head_m=head_m)
            ratio = result["encoding_over_algorithm_ratio"]
            rows.append({
                "window": window, "window_width_frac": width_frac,
                "window_head_m": head_m,
                "orientation_deg": orientation, "depth_m": depth,
                "algorithm_dispersion": result["dispersion_from_algorithm"]["mean"],
                "encoding_dispersion": result["dispersion_from_encoding"]["mean"],
                "ratio": ratio,
                "active_parameters": result["parameter_sensitivity"]["active_parameters"],
                "degenerate_outcome_dims": result["degenerate_outcome_dims"]})
    flat = [r for r in rows
            if r["algorithm_dispersion"] == 0 and r["encoding_dispersion"] == 0]
    data = {
        "study": "shadeparadox",
        "check": "E2 in four further orientation-depth cells, two window sizes",
        "package_version": __version__,
        "cells": rows,
        "n_cells": len(rows),
        "n_cells_with_zero_dispersion": len(flat),
        "zero_dispersion_windows": sorted({r["window"] for r in flat}),
        "interpretation": (
            "Exploratory (one optimiser seed). Whether the contrast is flat "
            "depends on the window: compare the 'reduced' and 'full' rows. "
            "No comparative encoding-versus-optimiser claim is made."),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,
                        default=ROOT/'reproduced/e2_sweep_check.json')
    parser.add_argument('--compare',action='store_true',
                        help='Compare with the archived eight-cell sweep.')
    args=parser.parse_args()
    if args.compare and args.output.name != 'e2_sweep_check.json':
        parser.error('--compare requires the output filename e2_sweep_check.json')
    if args.output.resolve() == (ROOT/'verification/e2_sweep_check.json').resolve():
        parser.error('Choose a fresh output path; preserve the archived sweep.')
    run(args.output)
    print(f"Wrote {args.output}")
    if args.compare:
        sys.path.insert(0,str(ROOT))
        from compare_results import compare_results
        count=compare_results('shadeparadox_e2_sweep',ROOT/'verification',args.output.parent)
        print(f'PASS: {count} numeric fields match the archived E2 sweep (rtol=1e-9, atol=1e-8).')
