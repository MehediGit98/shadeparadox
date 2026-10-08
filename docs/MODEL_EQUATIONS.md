# ShadeParadox model equations (as implemented in v0.3.2)

Each statement below is taken from the code named in brackets. All quantities
are model outputs for a synthetic office; none has been validated against
measurement or Radiance.

## 1 Melanopic EDI at the eye  [`streetlux/photometry.py`, `optics.solve`]

With eye-plane spectral irradiance E_λ(t) (vertical, view direction),

    mEDI(t) = [ ∫ E_e,λ(λ,t) s_mel(λ) dλ ] / K ,   K = 0.0013262 W lm⁻¹

where E_e,λ is the spectral irradiance at the eye (vertical, in the view
direction), s_mel the CIE S 026 melanopic action spectrum and K the D65
melanopic daylight efficacy of radiation. The reported mEDI includes the
dimmed electric-lighting contribution.

## 2 Aggregation  [`sim.py`]

For one run, with occupied half-hour steps *i* on representative date *d*
(weights w_d = 90, 90, 120, 65 days):

    mEDI_mean = Σ_d w_d · mean_i∈d(mEDI_i) / Σ_d w_d
    frac_250  = Σ_d w_d · mean_i∈d[mEDI_i ≥ 250 lx] / Σ_d w_d
    frac_DGP  = Σ_d w_d · mean_i∈d[DGP_i ≥ 0.35]  / Σ_d w_d

Retention for rule *k* in cell *c* [`experiment.e1_behaviour`]:

    R_k,c = mean_seeds(mEDI_mean,k,c) / mean_seeds(mEDI_mean,open,c)

Table 2 reports the mean of R_k,c over the 12 cells; the paired by-seed values
R_k,c,s = mEDI_mean,k,c,s / mEDI_mean,open,c,s are used for the seed interval.

Diagnostic counters use per-date increments of the controller's cumulative
counters. Their sum counts events across the actual simulated dates, with no
representative-day weighting or annual extrapolation. The controller state and
random generator persist between dates. For example, two arrivals on each of
four dates give eight arrivals. E1 cell-level counters are means of these run
totals across seeds. 

## 3 Glare proxy  [`metrics.dgp`]

    DGP = 5.87×10⁻⁵ E_v + 0.0918 log₁₀(1 + Σ_s L_s² ω_s / (E_v^1.87 P_s²)) + 0.16

clipped to [0, 1]. Sources are directions in the field of view with luminance
above max(source_factor · mean field luminance, 500 cd m⁻²); P_s is the
position index. If no source is found and there is no point source, only the
illuminance term is used. A proxy computed from 256 sampled directions; it is
not evalglare.

## 4 Energy proxy  [`metrics.EnergyModel`]

    P_cool = (P_solar,transmitted + P_light + (18 + 12) W m⁻² · A_floor) / COP · (1 + f_fan)
    P_total = P_cool + P_light ,   COP = 3.0 ,  f_fan = 0.12 ,  A_floor = 48 m²

summed over occupied half-hours. The fixed term contributes 4.03 kWh per
occupied day (7.5 h).

## 5 Blind-operation rules  [`behaviour.py`]

* **always_open** – coverage 0.
* **glare_only** – if DGP > 0.38 at the current coverage, move to the smallest
  higher allowed coverage with DGP ≤ 0.38, or to the largest allowed coverage if
  none qualifies. It never opens except through arrival reopening.
* **thermal_only** – the same, triggered by solar irradiance on the occupant
  > 100 W m⁻².
* **thermal_and_glare** – the same, triggered by either condition and requiring
  both limits to be met by the new coverage.
* **illustrative_stochastic** – at an occupied step with vertical illuminance
  E_v (lx), move to the next higher allowed coverage with probability

      p = 1 / (1 + exp(−z)) ,   z = a + b · log₁₀(max(E_v, 1)) ,   a = −8 , b = 1.6

  (assumed coefficients; varied in `sensitivity.stochastic_intercept_sweep`).
* **circadian_aware** – among coverages with DGP ≤ 0.38 and solar ≤ 100 W m⁻²
  choose the highest mEDI; if none qualifies choose the lowest DGP, then the
  highest mEDI. Total mEDI did not increase with coverage in the tested E1
  audit (`sensitivity.melanopic_equivalence`); the tested runs had the same
  aggregate outcomes as **minimum_admissible_coverage**. This is a finding
  within those E1 conditions, not universal monotonicity: electric-light
  output can increase as daylight falls, and different spectra or views
  may change the ordering.

All rules except always_open reopen a closed blind with probability
`reopen_prob` when the occupant arrives or returns from lunch; state is carried
across the ordered representative dates unless `sensitivity.independent_dates`
is used.

## 6 Reporting thresholds

Closure triggers use DGP 0.38; glare-time metrics use DGP ≥ 0.35. The exposure
reference threshold is mEDI ≥ 250 lx (Brown et al., 2022 daytime recommendation
for healthy adults); meeting a modelled threshold is not physiological compliance.
