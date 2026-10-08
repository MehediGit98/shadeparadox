"""Compare generated PNG pixels against the archived figures."""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('figure_1_office_geometry', 'figure_2_blind_tradeoffs',
         'figure_3_view_direction', 'figure_4_unidentifiable_comparison',
         'figure_s1_stochastic_sensitivity', 'ShadeParadox_graphical_abstract')


def pixels(source):
    with Image.open(source) as im:
        return im.size, hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()


def check(actual, expected=ROOT/'figures'):
    actual, expected = Path(actual), Path(expected)
    checks = []
    for name in NAMES:
        actual_pixels = pixels(actual/(name+'.png'))
        expected_pixels = pixels(expected/(name+'.png'))
        checks.append({'figure': name, 'pixels_match': actual_pixels == expected_pixels,
                       'dimensions': actual_pixels[0], 'rgba_sha256': actual_pixels[1]})
    return {'png_checks': checks,
            'all_pixels_match': all(c['pixels_match'] for c in checks)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures-dir', type=Path, default=ROOT/'reproduced'/'figures')
    parser.add_argument('--strict', action='store_true',
                        help='Exit with an error if PNG pixels differ.')
    args = parser.parse_args()
    result = check(args.figures_dir)
    print(json.dumps(result, indent=2))
    if not result['all_pixels_match']:
        print('Rendering differs; inspect the figures and plotting versions. '
              'Pixel equality can depend on the platform.')
    raise SystemExit(1 if args.strict and not result['all_pixels_match'] else 0)
