"""
Blind-operation rules.

Each controller is an assumed rule for how a blind is operated, not a fitted
behavioural model.  ``always_open`` is the counterfactual.  Every other rule
inherits ``Controller.arrival``: a closed blind reopens with probability
``reopen_prob`` when the occupant arrives or returns from lunch, so all rules
are seed-dependent.  Whether the resulting persistence changes melanopic
exposure is a result of the experiments, not an assumption of this module.

All stochastic models take a seed and are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .metrics import THRESHOLDS, StepMetrics

COVERAGE_STEPS = np.array([0.0, 0.25, 0.5, 0.75, 1.0])


@dataclass
class Occupancy:
    """Arrival, departure and a mid-day absence."""
    arrive_h: float = 9.0
    leave_h: float = 17.5
    lunch_start_h: float = 13.0
    lunch_end_h: float = 14.0

    def occupied(self, t: float) -> bool:
        if not (self.arrive_h <= t < self.leave_h):
            return False
        return not (self.lunch_start_h <= t < self.lunch_end_h)

    @property
    def hours(self) -> float:
        return ((self.leave_h - self.arrive_h)
                - (self.lunch_end_h - self.lunch_start_h))


@dataclass
class ControllerParams:
    """
    Every tunable in one place, so that an optimiser can search them and a
    report can print exactly what was searched.
    """
    dgp_close: float = 0.38
    solar_close_w_m2: float = 100.0
    reopen_prob: float = 0.22          # probability of reopening on arrival
    medi_target: float = 250.0
    workplane_target: float = 500.0
    max_coverage: float = 1.0
    # Logit of the closing probability of IllustrativeStochastic:
    # z = stochastic_intercept + stochastic_slope * log10(Ev / lx).
    # Assumed values, not fitted to field data (see sensitivity.py).
    stochastic_intercept: float = -8.0
    stochastic_slope: float = 1.6

    def as_dict(self) -> dict:
        return self.__dict__.copy()


class Controller:
    """Base class.  ``probe(coverage, electric)`` returns a StepMetrics."""
    key = "base"
    label = "base"
    uses_circadian = False

    def __init__(self, params: ControllerParams | None = None, seed: int = 0):
        self.p = params or ControllerParams()
        self.rng = np.random.default_rng(seed)
        self.coverage = 0.0
        self._was_occupied = False
        self.counters = {"close_events": 0, "open_events": 0,
                         "glare_triggers": 0, "thermal_triggers": 0,
                         "circadian_overrides": 0, "steps_evaluated": 0,
                         "arrivals": 0, "arrival_reopenings": 0}

    # -- helpers ----------------------------------------------------------
    def _allowed(self):
        return COVERAGE_STEPS[COVERAGE_STEPS <= self.p.max_coverage + 1e-9]

    def _dim_to_target(self, probe, coverage) -> tuple[float, StepMetrics]:
        """Dim electric lighting to just meet the work-plane target."""
        m0 = probe(coverage, 0.0)
        if m0.lux_workplane >= self.p.workplane_target:
            return 0.0, m0
        m1 = probe(coverage, 1.0)
        if m1.lux_workplane <= self.p.workplane_target:
            return 1.0, m1
        gain = max(m1.lux_workplane - m0.lux_workplane, 1e-6)
        f = float(np.clip(
            (self.p.workplane_target - m0.lux_workplane) / gain, 0.0, 1.0))
        return f, probe(coverage, f)

    def _settle(self, probe, coverage):
        f, m = self._dim_to_target(probe, coverage)
        return m

    # -- interface --------------------------------------------------------
    def act(self, probe, t: float, occupied: bool) -> StepMetrics:
        raise NotImplementedError

    def arrival(self, occupied: bool) -> bool:
        """
        Detect the unoccupied -> occupied transition and apply the reopening
        rule.

        Blinds are a ratchet within the day.  Longitudinal field studies find
        closing is frequent and reopening is rare and concentrated at arrival;
        modelling reopening as a per-timestep probability would erase the
        persistence that drives the whole effect.
        """
        arrived = occupied and not self._was_occupied
        self._was_occupied = occupied
        if arrived:
            self.counters["arrivals"] += 1
            if self.coverage > 0 and self.rng.random() < self.p.reopen_prob:
                self.counters["arrival_reopenings"] += 1
                self._set(0.0)
                return True
        return False

    def _set(self, new):
        if new > self.coverage + 1e-9:
            self.counters["close_events"] += 1
        elif new < self.coverage - 1e-9:
            self.counters["open_events"] += 1
        self.coverage = float(new)


class AlwaysOpen(Controller):
    key, label = "always_open", "Blinds never operated"

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        self._set(0.0)
        return self._settle(probe, 0.0)


class AlwaysClosed(Controller):
    key, label = "always_closed", "Blinds permanently drawn"

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        self._set(self.p.max_coverage)
        return self._settle(probe, self.p.max_coverage)


class GlareOnly(Controller):
    key, label = "glare_only", "Closes on glare only"

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        if not occupied:
            return self._settle(probe, self.coverage)
        m = self._settle(probe, self.coverage)
        if m.dgp > self.p.dgp_close:
            self.counters["glare_triggers"] += 1
            for c in self._allowed():
                if c <= self.coverage:
                    continue
                cand = self._settle(probe, c)
                if cand.dgp <= self.p.dgp_close:
                    self._set(c)
                    return cand
            self._set(self._allowed()[-1])
            return self._settle(probe, self.coverage)
        return m


class ThermalOnly(Controller):
    key, label = "thermal_only", "Closes on radiant discomfort only"

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        m = self._settle(probe, self.coverage)
        if not occupied:
            return m
        if m.solar_on_occupant_w_m2 > self.p.solar_close_w_m2:
            self.counters["thermal_triggers"] += 1
            for c in self._allowed():
                if c <= self.coverage:
                    continue
                cand = self._settle(probe, c)
                if cand.solar_on_occupant_w_m2 <= self.p.solar_close_w_m2:
                    self._set(c)
                    return cand
            self._set(self._allowed()[-1])
            return self._settle(probe, self.coverage)
        return m


class ThermalAndGlare(Controller):
    key, label = "thermal_and_glare", "Closes on glare or radiant discomfort"

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        m = self._settle(probe, self.coverage)
        if not occupied:
            return m
        need = (m.dgp > self.p.dgp_close
                or m.solar_on_occupant_w_m2 > self.p.solar_close_w_m2)
        if need:
            if m.dgp > self.p.dgp_close:
                self.counters["glare_triggers"] += 1
            if m.solar_on_occupant_w_m2 > self.p.solar_close_w_m2:
                self.counters["thermal_triggers"] += 1
            for c in self._allowed():
                if c <= self.coverage:
                    continue
                cand = self._settle(probe, c)
                if (cand.dgp <= self.p.dgp_close
                        and cand.solar_on_occupant_w_m2
                        <= self.p.solar_close_w_m2):
                    self._set(c)
                    return cand
            self._set(self._allowed()[-1])
            return self._settle(probe, self.coverage)
        return m


class IllustrativeStochastic(Controller):
    """
    Illustrative logistic closing probability in vertical eye illuminance.
    The coefficients (``stochastic_intercept``, ``stochastic_slope`` in
    :class:`ControllerParams`) are assumed, not fitted to field data.  This is
    not an implementation of any published blind-operation model.
    """
    key, label = "illustrative_stochastic", "Illustrative stochastic operation"

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        m = self._settle(probe, self.coverage)
        if not occupied:
            return m
        z = (self.p.stochastic_intercept
             + self.p.stochastic_slope * np.log10(max(m.lux_vertical, 1.0)))
        p_close = 1.0 / (1.0 + np.exp(-z))
        if self.rng.random() < p_close and self.coverage < self.p.max_coverage:
            self.counters["glare_triggers"] += 1
            higher = [c for c in self._allowed() if c > self.coverage]
            if higher:
                self._set(higher[0])
                return self._settle(probe, self.coverage)
        return m


class CircadianAware(Controller):
    """
    Melanopic-aware rule: among the coverages that satisfy the glare and
    radiant-comfort limits, take the one with the highest melanopic EDI; if
    none satisfies both, take the lowest glare proxy and then the highest
    melanopic EDI, and record that it did.

    Behavioural note: in this model melanopic EDI does not increase with
    coverage (audited in ``sensitivity.melanopic_equivalence``), so the rule
    always selects the smallest admissible coverage and is equivalent to
    :class:`MinimumAdmissibleCoverage`.  The melanopic criterion therefore
    never changes a decision here.
    """
    key, label = "circadian_aware", "Glare-constrained, circadian-maximising"
    uses_circadian = True

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        if not occupied:
            return self._settle(probe, self.coverage)
        cands = [(c, self._settle(probe, c)) for c in self._allowed()]
        ok = [(c, m) for c, m in cands
              if m.dgp <= self.p.dgp_close
              and m.solar_on_occupant_w_m2 <= self.p.solar_close_w_m2]
        if ok:
            best = max(ok, key=lambda cm: cm[1].medi)
            if best[1].medi < self.p.medi_target:
                self.counters["circadian_overrides"] += 1
            self._set(best[0])
            return best[1]
        self.counters["circadian_overrides"] += 1
        best = min(cands, key=lambda cm: (cm[1].dgp, -cm[1].medi))
        self._set(best[0])
        return best[1]


class MinimumAdmissibleCoverage(Controller):
    """
    Memoryless reference rule: at every occupied step choose the smallest
    coverage that satisfies the glare and radiant-comfort limits (fallback as
    in :class:`CircadianAware`).  Not part of the E1 controller set; it is the
    comparison rule used by ``sensitivity.melanopic_equivalence``.
    """
    key, label = "minimum_admissible_coverage", "Smallest admissible coverage"

    def act(self, probe, t, occupied):
        self.counters["steps_evaluated"] += 1
        self.arrival(occupied)
        if not occupied:
            return self._settle(probe, self.coverage)
        cands = [(c, self._settle(probe, c)) for c in self._allowed()]
        ok = [(c, m) for c, m in cands
              if m.dgp <= self.p.dgp_close
              and m.solar_on_occupant_w_m2 <= self.p.solar_close_w_m2]
        if ok:
            c, m = min(ok, key=lambda cm: cm[0])
        else:
            c, m = min(cands, key=lambda cm: (cm[1].dgp, -cm[1].medi))
        self._set(c)
        return m


CONTROLLERS = {c.key: c for c in (AlwaysOpen, AlwaysClosed, GlareOnly,
                                  ThermalOnly, ThermalAndGlare,
                                  IllustrativeStochastic, CircadianAware)}

#: Reference rules that are not part of the E1/E3 controller sets.
REFERENCE_CONTROLLERS = {MinimumAdmissibleCoverage.key:
                         MinimumAdmissibleCoverage}


def controller(key: str, params=None, seed: int = 0) -> Controller:
    registry = {**CONTROLLERS, **REFERENCE_CONTROLLERS}
    if key not in registry:
        raise KeyError(f"unknown controller {key!r}; have {sorted(registry)}")
    return registry[key](params, seed)
