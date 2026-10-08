"""Compare regenerated CSV tables with archived values, ignoring line endings."""
from pathlib import Path
import argparse
import csv
import json
import math

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('table2_blind_operation.csv', 'table3_view_direction.csv',
         'e1_cell_retention.csv', 'e1_per_seed.csv', 'e2_cells.csv', 'e3_headings.csv',
         'sensitivity_intercept_sweep.csv', 'sensitivity_independent_dates.csv',
         'sensitivity_heading_convergence.csv')


def values(path):
    with path.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.reader(handle))
    def decode(value):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return [[decode(v) for v in row] for row in rows]


def check(actual, expected=ROOT/'results'):
    count = 0
    def compare(a, b, location):
        nonlocal count
        if isinstance(a, dict):
            if not isinstance(b, dict) or set(a) != set(b):
                raise AssertionError('Different fields: '+location)
            for key in a: compare(a[key], b[key], location+'/'+key)
        elif isinstance(a, list):
            if not isinstance(b, list) or len(a) != len(b):
                raise AssertionError('Different row/column count: '+location)
            for i, (first, second) in enumerate(zip(a, b)):
                compare(first, second, location+'/'+str(i))
        elif isinstance(a, (int, float)) and not isinstance(a, bool):
            if not isinstance(b, (int, float)) or isinstance(b, bool) or not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-8):
                raise AssertionError(f'{location}: {a} != {b}')
            count += 1
        elif a != b:
            raise AssertionError('Different value: '+location)
    for name in NAMES:
        compare(values(Path(expected)/name), values(Path(actual)/name), name)
    return {'tables_matched': list(NAMES), 'numeric_fields_matched': count,
            'relative_tolerance': 1e-9, 'absolute_tolerance': 1e-8, 'status': 'pass'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=ROOT/'reproduced')
    args = parser.parse_args()
    print(json.dumps(check(args.results_dir), indent=2))
