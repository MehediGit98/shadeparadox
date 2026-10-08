# shadeparadox 0.3.2

Reduced spectral office model and blind-operation experiments used by the
ShadeParadox experiments. See the package-root `README.md` for the tested
reproduction commands and `docs/MODEL_EQUATIONS.md` for the equations.

| Module | Content |
|---|---|
| `optics.py` | Room, glazing, shade devices, sky-to-eye radiance and illuminance solver |
| `metrics.py` | mEDI, DGP proxy, energy proxy, per-step metrics |
| `behaviour.py` | Occupancy and blind-operation rules |
| `sim.py` | Representative dates, time stepping, aggregation |
| `experiment.py` | E1 (rule × orientation × depth), E2 (encoding × optimiser), E3 (view heading) |
| `sensitivity.py` | Sensitivity analyses and model diagnostics for the declared configurations |
| `tables.py` | Summary tables computed from saved results |
| `control.py`, `report.py`, `__main__.py` | Objective encodings, HTML report, command line |
