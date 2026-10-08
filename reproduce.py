"""Reproduce ShadeParadox using bundled source; no sibling archive needed."""
from pathlib import Path
import argparse

from pipeline import reproduce
from make_figures import main as figures
from compare_results import compare_results
from verification.check_additional_details import run as additional_checks
from verification.check_figures import check as check_figures
from verification.check_tables import check as check_tables

ROOT = Path(__file__).resolve().parent


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'reproduced')
    parser.add_argument('--include-e2-sweep', action='store_true',
                        help='Also run and compare the supplementary eight-cell E2 sweep.')
    parser.add_argument('--skip-comparison', action='store_true',
                        help='Generate fresh outputs without comparing (release maintenance only).')
    parser.add_argument('--strict-figures', action='store_true',
                        help='Require exact PNG pixel agreement with archived figures.')
    args = parser.parse_args()
    output = args.out.resolve()
    # Protect the archived results from accidental in-place regeneration.
    if output == ROOT.resolve() or any(
            output == (ROOT/name).resolve() or (ROOT/name).resolve() in output.parents
            for name in ('results', 'verification', 'source', 'figures', 'fonts', 'docs')):
        parser.error('--out must be a fresh results directory, such as reproduced/')
    reproduce('shadeparadox', output)
    additional_checks(ROOT, output, output/'additional_checks.json')
    if args.include_e2_sweep:
        from verification.e2_sweep_check import run as run_e2_sweep
        run_e2_sweep(output/'e2_sweep_check.json')
        print('Supplementary eight-cell E2 sweep complete', flush=True)
    if not args.skip_comparison:
        count = compare_results('shadeparadox', ROOT/'results', output)
        print(f'PASS: {count} numeric fields match the archived results (rtol=1e-9, atol=1e-8).')
        count = compare_results('shadeparadox_details', ROOT/'verification', output)
        print(f'PASS: {count} numeric fields match the additional model checks.')
        table_check = check_tables(output)
        print(f"PASS: all {len(table_check['tables_matched'])} CSV tables match the archived values.")
        if args.include_e2_sweep:
            count = compare_results('shadeparadox_e2_sweep', ROOT/'verification', output)
            print(f'PASS: {count} numeric fields match the archived E2 sweep (rtol=1e-9, atol=1e-8).')
    figures('shadeparadox', output, output/'figures')
    figure_check = check_figures(output/'figures')
    import json
    (output/'figure_reproduction_check.json').write_text(json.dumps(figure_check, indent=2)+'\n')
    if figure_check['all_pixels_match']:
        print('PASS: all 6 archived figure PNGs match archived pixels.')
    elif args.strict_figures:
        raise AssertionError('PNG rendering differs from the archived figures; inspect plotting environment.')
    else:
        print('NOTE: PNG pixels differ; rendering can vary by platform. Inspect figures and plotting versions.')
