# ShadeParadox

ShadeParadox is a reproducible spectral office model for examining blind
operation, melanopic exposure at the eye, viewing direction and lighting
control objectives. This repository contains the simulation code, reference
inputs, archived numerical results, CSV tables, figures and verification tools.
Everything needed for the calculations is local after installing dependencies.

The model release is **0.3.2**. Experiment settings are defined in `pipeline.py`:

- **E1:** six blind-operation rules across four orientations, three depths and
  five behavioural seeds over four weighted representative dates.
- **E2:** six objective encodings crossed with four optimisers, with activation
  diagnostics and an additional eight-cell orientation/window sweep.
- **E3:** twelve viewing headings for four control rules in a west-facing room.
- **Sensitivity analyses:** stochastic closing intercept, independent dates,
  directional sampling, melanopic-rule equivalence and model diagnostics.

## Install and reproduce all results

Use Python 3.12. Extract this archive or clone the repository, then open a
terminal in the directory containing `reproduce.py`.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe reproduce.py --include-e2-sweep
```

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reproduce.py --include-e2-sweep
```

The command reruns the experiments, sensitivities, additional model checks and
eight-cell sweep. It generates all nine CSV tables and all six PNG/SVG figure
pairs, and compares computed values with the archived baselines. New outputs
are written to `reproduced/`; the supplied baselines remain in `results/`,
`figures/` and `verification/`. Runtime depends on the CPU; the full numerical
sweep takes substantially longer than plotting from existing results.

`--out PATH` selects a different fresh destination. Omitting
`--include-e2-sweep` omits only that additional eight-cell sweep.
`--strict-figures` also requires exact agreement of PNG pixels. Numerical
differences above the declared tolerances raise an error. Rendering can vary
across platforms, so ordinary runs report pixel differences for inspection.
`--skip-comparison` is a maintenance option and does not constitute verification.

## Regenerate tables and figures from saved results

These commands read the archived JSON and recreate the exports:

```bash
python make_tables.py
python make_figures.py
python verification/check_tables.py
python verification/check_figures.py --strict
```

Both generators accept `--data PATH` and `--out PATH`. The default output is
`reproduced/` for CSV tables and `reproduced/figures/` for graphics.

## Archived outputs

| Location | Contents |
|---|---|
| `results/e1.json`, `e2.json`, `e3.json` | Full experiment records and summaries |
| `results/sensitivity.json` | All main sensitivity and diagnostic results |
| `results/shadeparadox_results.json` | Combined results and provenance |
| `results/table2_blind_operation.csv` | Blind-operation summary |
| `results/table3_view_direction.csv` | Heading and coverage summary |
| `results/e1_cell_retention.csv`, `e1_per_seed.csv` | Cell and seed-level E1 data |
| `results/e2_cells.csv`, `e3_headings.csv` | Selected E2 solutions and E3 heading records |
| `results/sensitivity_*.csv` | Three sensitivity tables |
| `results/run_metadata.json`, `metrology_checks.json` | Environment, settings, reference digests and calibration checks |
| `verification/e2_sweep_check.json` | Additional eight-cell E2 sweep |
| `verification/additional_checks.json` | Source DER, shade transmission, fixed load, paired headings and electric-light checks |
| `figures/` | Room geometry, blind trade-offs, heading dependence, optimisation diagnostic, stochastic sensitivity and graphical summary |

Figure filenames are stable output identifiers. The five scientific figures
are 600-dpi PNGs; the graphical summary is 3000 × 1500 pixels at 300 dpi. SVG
versions are included. Descriptions are in `docs/FIGURE_CAPTIONS.md`.

## Verification and interpretation

```bash
python verify.py
python verification/check_additional_details.py --compare
python verification/e2_sweep_check.py --compare
python make_manifest.py --check
```

The regression suite has 19 tests: 15 apply to the bundled code and four tests
for the separate SpecDebt package are skipped. Numerical comparisons use
relative tolerance 1e-9 and absolute tolerance 1e-8. CSV comparisons check
headers, dimensions, categorical values and numbers; PNG comparisons check
dimensions and decoded pixels. SVG timestamps and metadata may differ.
`verification/computational_validation.json` records checks performed on this
public package, including their scope. Matching an archive establishes
computational repeatability of this model, not physical accuracy.

`MANIFEST_SHA256.json` records the public files. `make_manifest.py --check`
checks their integrity while excluding local files covered by `.gitignore`.
`--write` updates the manifest after an intentional public code/data change;
it does not verify the scientific meaning of that change.

## Model definitions and limits

Equations, control rules, thresholds and proxies are described in
`docs/MODEL_EQUATIONS.md`. The objective scores and optimiser implementations
are executable in `source/shadeparadox/shadeparadox/control.py`; experimental
settings, outcome scaling and parameter bounds are in `experiment.py`.
The bundled `source/streetlux/` supplies shared spectral/metrology functions.

One controller carries state across four representative dates. This is an
assumed memory sequence, not a continuous annual-weather simulation. Counter
totals sum date increments without annual weighting. Stochastic coefficients
are assumed, and glare and energy are reduced proxies. No matched physical,
Radiance/evalglare or physiological validation is supplied for these scenes.
The flat default E2 comparison supports no optimiser-dominance claim; the
additional configuration sweeps are exploratory.

## Dependencies and third-party terms

`requirements.txt` pins NumPy 2.3.5, Matplotlib 3.10.8, FontTools 4.61.1 and
Pillow 12.3.0. The bundled source font removes the need for system-font
installation; see `fonts/README.md` and `fonts/OFL.txt`. Reference-data sources,
checksums and limitations are described in `source/reference_data/README.md`.
Third-party font/data terms apply to those materials. No licence for the
project's own code is assigned by this package.
