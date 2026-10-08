"""Regenerate all nine CSV tables from the archived or freshly computed JSON."""
from pathlib import Path
import argparse
import json
from pipeline import csvsave
from shadeparadox import tables

ROOT = Path(__file__).resolve().parent


def main(data=None, out=None):
    data = Path(data) if data is not None else ROOT/'results'
    out = Path(out) if out is not None else ROOT/'reproduced'
    out.mkdir(parents=True, exist_ok=True)
    e1, e2, e3, sens = [json.loads((data/name).read_text(encoding='utf-8'))
                        for name in ('e1.json','e2.json','e3.json','sensitivity.json')]
    csvsave(out/'table2_blind_operation.csv', tables.table2(e1))
    csvsave(out/'table3_view_direction.csv', tables.table3(e3))
    csvsave(out/'e1_cell_retention.csv', tables.cell_retention(e1))
    for name, rows in tables.sensitivity_tables(sens).items():
        csvsave(out/(name+'.csv'), rows)
    csvsave(out/'e1_per_seed.csv', (
        {'orientation_deg':r['orientation_deg'], 'depth_m':r['depth_m'],
         'controller':r['controller'], **value}
        for r in e1['rows'] for value in r['per_seed']))
    csvsave(out/'e2_cells.csv', (
        {'encoding':c['encoding'], 'optimiser':c['optimiser'], **c} for c in e2['cells']))
    csvsave(out/'e3_headings.csv', (
        {'controller':r['controller'], **value} for r in e3['rows'] for value in r['values']))
    print('Nine CSV tables written to', out, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT/'results')
    parser.add_argument('--out', type=Path, default=ROOT/'reproduced')
    args = parser.parse_args()
    if args.out.resolve() == ROOT.resolve() or any(
        args.out.resolve() == (ROOT/n).resolve() or (ROOT/n).resolve() in args.out.resolve().parents
        for n in ('results','source','verification','figures','fonts','docs')):
        parser.error('Choose a fresh output directory such as reproduced/.')
    main(args.data, args.out)
