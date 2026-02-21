"""Parameter sweep and calibration utilities for the ABM.

Provides tools for systematically searching the parameter space to find
model configurations that best replicate observed UK macroeconomic statistics.

The calibration workflow is:

1. Define a parameter grid (``{param_name: [value1, value2, ...]}``).
2. Provide a factory function that accepts those keyword arguments and returns
   a configured, initialised :class:`~companies_house_abm.abm.model.Simulation`.
3. Call :func:`parameter_sweep` — it runs every parameter combination and
   returns a :class:`SweepSummary` with per-combination evaluation scores.
4. Inspect :attr:`SweepSummary.best` for the parameter set that minimises
   the weighted RMSD against the UK calibration targets.

Example::

    from companies_house_abm.abm.calibration import parameter_sweep
    from companies_house_abm.abm.sector_model import (
        create_sector_representative_simulation,
    )

    def factory(price_markup, mpc_mean):
        return create_sector_representative_simulation(
            n_households=500, n_banks=3, periods=80,
        )

    summary = parameter_sweep(
        param_grid={
            "price_markup": [0.10, 0.15, 0.20],
            "mpc_mean": [0.70, 0.80, 0.90],
        },
        base_factory=factory,
        periods=80,
        warm_up=20,
    )
    print(summary.best)
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from companies_house_abm.abm.evaluation import EvaluationReport, evaluate_simulation

if TYPE_CHECKING:
    from collections.abc import Callable

    from companies_house_abm.abm.evaluation import TargetStat
    from companies_house_abm.abm.model import Simulation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SweepResult:
    """Result of one parameter combination in a sweep.

    Attributes:
        params: The parameter values used for this run.
        report: The evaluation report for this run.
    """

    params: dict[str, Any]
    report: EvaluationReport

    @property
    def score(self) -> float:
        """Weighted RMSD evaluation score (lower is better)."""
        return self.report.overall_score

    def __repr__(self) -> str:
        return f"SweepResult(score={self.score:.4f}, params={self.params})"


@dataclass
class SweepSummary:
    """Summary of a full parameter sweep.

    Attributes:
        results: One :class:`SweepResult` per parameter combination tested.
    """

    results: list[SweepResult] = field(default_factory=list)

    @property
    def best(self) -> SweepResult | None:
        """Parameter combination with the lowest evaluation score."""
        return min(self.results, key=lambda r: r.score) if self.results else None

    @property
    def worst(self) -> SweepResult | None:
        """Parameter combination with the highest evaluation score."""
        return max(self.results, key=lambda r: r.score) if self.results else None

    def ranked(self) -> list[SweepResult]:
        """Return results sorted by score (ascending — best first)."""
        return sorted(self.results, key=lambda r: r.score)

    def summary_table(self) -> str:
        """Human-readable table of all results sorted by score."""
        if not self.results:
            return "No results."
        ranked = self.ranked()
        param_keys = list(ranked[0].params.keys())
        header = f"{'Rank':>4}  {'Score':>8}  " + "  ".join(
            f"{k:<12}" for k in param_keys
        )
        lines = [header, "-" * len(header)]
        for i, r in enumerate(ranked, 1):
            param_str = "  ".join(f"{r.params[k]:<12}" for k in param_keys)
            lines.append(f"{i:>4}  {r.score:>8.4f}  {param_str}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parameter sweep
# ---------------------------------------------------------------------------


def parameter_sweep(
    param_grid: dict[str, list[Any]],
    *,
    base_factory: Callable[..., Simulation],
    periods: int = 80,
    warm_up: int = 20,
    targets: list[TargetStat] | None = None,
    verbose: bool = False,
) -> SweepSummary:
    """Run a grid search over parameter combinations.

    For every combination of values in ``param_grid``, this function:

    1. Calls ``base_factory(**params)`` to obtain a configured
       :class:`~companies_house_abm.abm.model.Simulation`.
    2. Runs the simulation for ``periods`` periods.
    3. Evaluates the result with
       :func:`~companies_house_abm.abm.evaluation.evaluate_simulation`,
       skipping the first ``warm_up`` periods.

    Args:
        param_grid: Mapping from parameter name to the list of values to
            explore.  All combinations are tested (full grid search).
        base_factory: Callable that accepts the keyword arguments from
            ``param_grid`` and returns a configured, *initialised*
            :class:`~companies_house_abm.abm.model.Simulation`.
        periods: Number of periods to run each simulation.
        warm_up: Number of leading periods to skip when computing evaluation
            statistics.
        targets: Calibration targets passed to
            :func:`~companies_house_abm.abm.evaluation.evaluate_simulation`.
            Defaults to the UK targets in
            :data:`~companies_house_abm.abm.evaluation.DEFAULT_TARGETS`.
        verbose: If ``True``, log progress at ``INFO`` level.

    Returns:
        A :class:`SweepSummary` with one :class:`SweepResult` per combination.
        Combinations that raise an exception are silently skipped (the
        exception is logged at ``WARNING`` level).

    Example::

        from companies_house_abm.abm.calibration import parameter_sweep
        from companies_house_abm.abm.sector_model import (
            create_sector_representative_simulation,
        )

        def factory(**kw):
            return create_sector_representative_simulation(
                n_households=500, n_banks=3, **kw
            )

        summary = parameter_sweep(
            {"seed": [0, 1, 2]},
            base_factory=factory,
            periods=40,
            warm_up=10,
        )
        print(summary.best)
    """
    keys = list(param_grid.keys())
    value_lists = [param_grid[k] for k in keys]
    n_total = 1
    for lst in value_lists:
        n_total *= len(lst)

    summary = SweepSummary()

    for i, combo in enumerate(itertools.product(*value_lists), 1):
        params: dict[str, Any] = dict(zip(keys, combo, strict=True))
        if verbose:
            logger.info("[%d/%d] Evaluating %s", i, n_total, params)

        try:
            sim = base_factory(**params)
            result = sim.run(periods=periods)
            report = evaluate_simulation(result, targets=targets, warm_up=warm_up)
            summary.results.append(SweepResult(params=params, report=report))
            if verbose:
                logger.info(
                    "  -> score=%.4f  (%d/%d targets)",
                    report.overall_score,
                    report.n_passed,
                    report.n_total,
                )
        except Exception as exc:
            logger.warning("Sweep combination %s failed: %s", params, exc)

    return summary


# ---------------------------------------------------------------------------
# One-dimensional sensitivity analysis
# ---------------------------------------------------------------------------


def sensitivity_analysis(
    param_name: str,
    param_values: list[Any],
    *,
    base_factory: Callable[..., Simulation],
    periods: int = 80,
    warm_up: int = 20,
    targets: list[TargetStat] | None = None,
) -> SweepSummary:
    """Vary a single parameter while holding all others at factory defaults.

    A convenience wrapper around :func:`parameter_sweep` for single-parameter
    sensitivity analysis.

    Args:
        param_name: The parameter to vary.
        param_values: Values to test.
        base_factory: Factory function; must accept ``param_name`` as a
            keyword argument.
        periods: Periods per simulation run.
        warm_up: Warm-up periods to skip in evaluation.
        targets: Calibration targets (defaults to UK targets).

    Returns:
        :class:`SweepSummary` sorted by ``param_name`` value.

    Example::

        from companies_house_abm.abm.calibration import sensitivity_analysis
        from companies_house_abm.abm.sector_model import (
            create_sector_representative_simulation,
        )

        def factory(seed=42):
            return create_sector_representative_simulation(
                n_households=500, n_banks=3, seed=seed, periods=80
            )

        summary = sensitivity_analysis(
            "seed",
            [0, 1, 2, 3, 4],
            base_factory=factory,
            periods=40,
            warm_up=10,
        )
        print(summary.summary_table())
    """
    return parameter_sweep(
        {param_name: param_values},
        base_factory=base_factory,
        periods=periods,
        warm_up=warm_up,
        targets=targets,
    )
