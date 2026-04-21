"""Evaluation framework for comparing ABM simulation output to calibration targets.

The evaluation workflow computes summary statistics from a
:class:`~companies_house_abm.abm.model.SimulationResult` and compares them
against empirical calibration targets for the UK economy.  The targets are
taken from the ``validation`` section of ``config/model_parameters.yml`` and
from the macroeconomics literature.

For historical simulations, :func:`evaluate_historical` compares the
simulated time series against actual UK data and produces a
:class:`HistoricalEvaluationReport` with fit metrics.

Usage::

    from companies_house_abm.abm.evaluation import evaluate_simulation
    from companies_house_abm.abm.model import Simulation

    sim = Simulation.from_config()
    result = sim.run(periods=80)
    report = evaluate_simulation(result, warm_up=20)
    print(report.summary())
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies_house_abm.abm.historical import HistoricalResult
    from companies_house_abm.abm.model import SimulationResult


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TargetStat:
    """A single calibration target statistic.

    Attributes:
        name: Identifier matching a key in the statistics dict returned by
            :func:`compute_simulation_stats`.
        description: Human-readable description.
        target_value: Empirical target value.
        tolerance: Maximum acceptable absolute deviation from ``target_value``
            for the target to be considered *passed*.
        weight: Relative importance when computing the aggregate score.
    """

    name: str
    description: str
    target_value: float
    tolerance: float
    weight: float = 1.0


@dataclass
class StatResult:
    """Evaluation result for a single calibration target.

    Attributes:
        name: Statistic name.
        description: Human-readable description.
        simulated: Value computed from the simulation output.
        target: Empirical calibration target.
        deviation: Relative deviation ``(simulated - target) / |target|``.
        tolerance: Tolerance threshold used to determine *passed*.
        passed: ``True`` if ``|simulated - target| <= tolerance``.
        weight: Weight used in the aggregate score.
    """

    name: str
    description: str
    simulated: float
    target: float
    deviation: float
    tolerance: float
    passed: bool
    weight: float


@dataclass
class EvaluationReport:
    """Full evaluation report comparing simulation output to calibration targets.

    Attributes:
        results: Per-target evaluation results.
    """

    results: list[StatResult] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Weighted root-mean-square relative deviation (lower is better).

        Returns ``inf`` when no results are available.
        """
        if not self.results:
            return float("inf")
        total_weight = sum(r.weight for r in self.results)
        if total_weight == 0:
            return float("inf")
        wss = sum(
            r.weight * r.deviation**2
            for r in self.results
            if not math.isnan(r.deviation)
        )
        return math.sqrt(wss / total_weight)

    @property
    def n_passed(self) -> int:
        """Number of targets within tolerance."""
        return sum(1 for r in self.results if r.passed)

    @property
    def n_total(self) -> int:
        """Total number of evaluated targets."""
        return len(self.results)

    def summary(self) -> str:
        """Return a human-readable summary of the evaluation report."""
        lines = [
            f"Evaluation Report: "
            f"{self.n_passed}/{self.n_total} targets within tolerance",
            f"Overall score (WRMS deviation): {self.overall_score:.4f}",
            "",
        ]
        max_name = max((len(r.name) for r in self.results), default=10)
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            dev_str = f"{r.deviation:+.1%}" if not math.isnan(r.deviation) else "  N/A "
            lines.append(
                f"  [{status}]  {r.name:<{max_name}}  "
                f"sim={r.simulated:8.4f}  "
                f"tgt={r.target:8.4f}  "
                f"dev={dev_str}"
            )
        return "\n".join(lines)

    def as_dict(self) -> dict[str, object]:
        """Serialise the report to a plain dictionary."""
        return {
            "overall_score": self.overall_score,
            "n_passed": self.n_passed,
            "n_total": self.n_total,
            "targets": [
                {
                    "name": r.name,
                    "description": r.description,
                    "simulated": r.simulated,
                    "target": r.target,
                    "deviation": r.deviation,
                    "passed": r.passed,
                }
                for r in self.results
            ],
        }


# ---------------------------------------------------------------------------
# Statistics computation
# ---------------------------------------------------------------------------


def compute_simulation_stats(
    result: SimulationResult,
    warm_up: int = 0,
    gdp_coverage: float = 1.0,
) -> dict[str, float]:
    """Compute aggregate statistics from a simulation result.

    Args:
        result: The simulation output.
        warm_up: Number of leading periods to discard (initial transients).
        gdp_coverage: Fraction of the full economy represented by the
            simulation's firm sector (default 1.0 — all sectors modelled).
            When using the sector-representative model (13 sectors covering
            ~85.7% of UK GDP), pass ``SECTOR_GDP_COVERAGE`` here so that
            debt-to-GDP and wage-share statistics are normalised to a
            whole-economy denominator rather than the simulated partial GDP.

    Returns:
        Dictionary mapping statistic name to its value.  Keys:

        - ``gdp_growth_mean`` — mean quarterly GDP growth rate.
        - ``gdp_growth_std``  — sample std dev of quarterly GDP growth rate.
        - ``unemployment_mean`` — mean unemployment rate.
        - ``inflation_mean``  — mean quarterly inflation rate.
        - ``inflation_std``   — sample std dev of quarterly inflation rate.
        - ``government_debt_gdp`` — mean government debt / GDP ratio
          (normalised by ``gdp_coverage``).
        - ``wage_share``      — mean labour-income share of GDP
          (normalised by ``gdp_coverage``).
    """
    records = result.records[warm_up:]
    n = len(records)
    if n == 0:
        return {}

    # ── GDP growth ────────────────────────────────────────────────────────
    gdps = [r.gdp for r in records]
    gdp_growths = [
        (gdps[i] - gdps[i - 1]) / gdps[i - 1]
        for i in range(1, len(gdps))
        if gdps[i - 1] > 0
    ]
    mean_gdp_growth = (
        sum(gdp_growths) / len(gdp_growths) if gdp_growths else float("nan")
    )
    if len(gdp_growths) > 1:
        # Sample std (÷ N-1) — consistent with calibration targets.
        std_gdp_growth = math.sqrt(
            sum((g - mean_gdp_growth) ** 2 for g in gdp_growths)
            / (len(gdp_growths) - 1)
        )
    else:
        std_gdp_growth = 0.0

    # ── Inflation ─────────────────────────────────────────────────────────
    inflations = [r.inflation for r in records]
    mean_inflation = sum(inflations) / n
    std_inflation = (
        math.sqrt(sum((x - mean_inflation) ** 2 for x in inflations) / (n - 1))
        if n > 1
        else 0.0
    )

    # ── Unemployment ──────────────────────────────────────────────────────
    mean_unemployment = sum(r.unemployment_rate for r in records) / n

    # ── Government debt / GDP ─────────────────────────────────────────────
    # Divide simulated debt/GDP by gdp_coverage so the ratio is normalised to
    # the full economy (e.g. if only 85.7% of sectors are modelled, simulated
    # GDP is ~85.7% of real GDP, inflating debt/GDP by ~1/0.857).
    _cov = gdp_coverage if gdp_coverage > 0 else 1.0
    debt_gdp_pairs = [(r.government_debt / r.gdp) / _cov for r in records if r.gdp > 0]
    mean_debt_gdp = (
        sum(debt_gdp_pairs) / len(debt_gdp_pairs) if debt_gdp_pairs else float("nan")
    )

    # ── Wage share ────────────────────────────────────────────────────────
    wage_shares = [
        ((r.average_wage * r.total_employment) / r.gdp) / _cov
        for r in records
        if r.gdp > 0 and r.total_employment > 0
    ]
    mean_wage_share = (
        sum(wage_shares) / len(wage_shares) if wage_shares else float("nan")
    )

    return {
        "gdp_growth_mean": mean_gdp_growth,
        "gdp_growth_std": std_gdp_growth,
        "unemployment_mean": mean_unemployment,
        "inflation_mean": mean_inflation,
        "inflation_std": std_inflation,
        "government_debt_gdp": mean_debt_gdp,
        "wage_share": mean_wage_share,
    }


# ---------------------------------------------------------------------------
# Default calibration targets (UK economy)
# ---------------------------------------------------------------------------

#: UK calibration targets drawn from ``config/model_parameters.yml`` and the
#: OBR/ONS statistical release for 2015-2024.
DEFAULT_TARGETS: list[TargetStat] = [
    TargetStat(
        name="gdp_growth_mean",
        description="Mean quarterly GDP growth rate (~2 % p.a.)",
        target_value=0.005,
        tolerance=0.003,
        weight=2.0,
    ),
    TargetStat(
        name="gdp_growth_std",
        description="Std dev of quarterly GDP growth (volatility)",
        target_value=0.010,
        tolerance=0.005,
        weight=1.0,
    ),
    TargetStat(
        name="unemployment_mean",
        description="Mean unemployment rate (~4.5 %)",
        target_value=0.045,
        tolerance=0.010,
        weight=2.0,
    ),
    TargetStat(
        name="inflation_mean",
        description="Mean quarterly inflation rate (2 % p.a. target)",
        target_value=0.005,
        tolerance=0.003,
        weight=2.0,
    ),
    TargetStat(
        name="inflation_std",
        description="Std dev of quarterly inflation",
        target_value=0.003,
        tolerance=0.002,
        weight=1.0,
    ),
    TargetStat(
        name="government_debt_gdp",
        description="Government debt as fraction of annual GDP (~85 %)",
        target_value=0.85,
        tolerance=0.20,
        weight=1.0,
    ),
    TargetStat(
        name="wage_share",
        description="Labour income share of GDP (~55 %)",
        target_value=0.55,
        tolerance=0.10,
        weight=1.0,
    ),
]


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------


def evaluate_simulation(
    result: SimulationResult,
    targets: list[TargetStat] | None = None,
    warm_up: int = 0,
    gdp_coverage: float = 1.0,
) -> EvaluationReport:
    """Evaluate a simulation result against calibration targets.

    Args:
        result: Simulation output to evaluate.
        targets: Target statistics.  Defaults to :data:`DEFAULT_TARGETS`
            (UK calibration).
        warm_up: Number of leading periods to skip when computing statistics.
            Use the same value as
            :attr:`~companies_house_abm.abm.config.SimulationConfig.warm_up_periods`.
        gdp_coverage: Fraction of the full economy represented by the
            simulation's firm sector.  Pass ``SECTOR_GDP_COVERAGE`` from
            :mod:`~companies_house_abm.abm.sector_model` when evaluating a
            sector-representative simulation so that debt/GDP and wage-share
            targets are compared against economy-normalised values.

    Returns:
        An :class:`EvaluationReport` with per-target pass/fail results and
        an overall goodness-of-fit score.

    Example::

        from companies_house_abm.abm.evaluation import evaluate_simulation
        from companies_house_abm.abm.model import Simulation

        sim = Simulation.from_config()
        result = sim.run(periods=80)
        report = evaluate_simulation(result, warm_up=20)
        print(report.summary())
    """
    if targets is None:
        targets = DEFAULT_TARGETS

    stats = compute_simulation_stats(result, warm_up=warm_up, gdp_coverage=gdp_coverage)
    stat_results: list[StatResult] = []

    for t in targets:
        simulated = stats.get(t.name, float("nan"))
        if math.isnan(simulated) or t.target_value == 0:
            deviation = float("nan")
            passed = False
        else:
            deviation = (simulated - t.target_value) / abs(t.target_value)
            passed = abs(simulated - t.target_value) <= t.tolerance

        stat_results.append(
            StatResult(
                name=t.name,
                description=t.description,
                simulated=simulated,
                target=t.target_value,
                deviation=deviation,
                tolerance=t.tolerance,
                passed=passed,
                weight=t.weight,
            )
        )

    return EvaluationReport(results=stat_results)


# ---------------------------------------------------------------------------
# Historical simulation evaluation
# ---------------------------------------------------------------------------


@dataclass
class HistoricalEvaluationReport:
    """Evaluation report for a historical simulation run.

    Compares the simulated time series against actual UK data and
    computes goodness-of-fit metrics.

    Attributes:
        scenario_name: Name of the scenario evaluated.
        n_periods: Number of periods in the comparison.
        price_correlation: Pearson correlation of simulated vs actual prices.
        price_rmse: Root mean squared error (GBP).
        price_rmse_pct: RMSE as percentage of mean actual price.
        directional_accuracy: Fraction of quarters with matching direction.
        mean_homeownership: Mean simulated homeownership rate.
        cross_sectional: Standard evaluation report for steady-state targets.
    """

    scenario_name: str = ""
    n_periods: int = 0
    price_correlation: float = float("nan")
    price_rmse: float = float("nan")
    price_rmse_pct: float = float("nan")
    directional_accuracy: float = float("nan")
    mean_homeownership: float = float("nan")
    cross_sectional: EvaluationReport | None = None

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"Historical Evaluation: {self.scenario_name}",
            f"  Periods evaluated:       {self.n_periods}",
            f"  Price correlation:       {self.price_correlation:+.3f}",
            f"  Price RMSE:              £{self.price_rmse:,.0f}",
            f"  Price RMSE (%):          {self.price_rmse_pct:.1%}",
            f"  Directional accuracy:    {self.directional_accuracy:.1%}",
            f"  Mean homeownership:      {self.mean_homeownership:.1%}",
        ]
        if self.cross_sectional:
            lines.append("")
            lines.append(self.cross_sectional.summary())
        return "\n".join(lines)

    def as_dict(self) -> dict[str, object]:
        """Serialise to a plain dictionary."""
        d: dict[str, object] = {
            "scenario_name": self.scenario_name,
            "n_periods": self.n_periods,
            "price_correlation": self.price_correlation,
            "price_rmse": self.price_rmse,
            "price_rmse_pct": self.price_rmse_pct,
            "directional_accuracy": self.directional_accuracy,
            "mean_homeownership": self.mean_homeownership,
        }
        if self.cross_sectional:
            d["cross_sectional"] = self.cross_sectional.as_dict()
        return d


def evaluate_historical(
    result: HistoricalResult,
    warm_up: int = 0,
) -> HistoricalEvaluationReport:
    """Evaluate a historical simulation result against actual UK data.

    Computes time-series fit metrics (correlation, RMSE, directional
    accuracy) and optionally a cross-sectional evaluation against
    standard calibration targets.

    Args:
        result: Output from
            :meth:`~companies_house_abm.abm.historical.HistoricalSimulation.run`.
        warm_up: Number of leading periods to discard for the
            cross-sectional evaluation.

    Returns:
        A :class:`HistoricalEvaluationReport`.
    """
    from companies_house_abm.abm.model import SimulationResult

    records = result.records
    n = len(records)

    # Homeownership
    ownership_rates = [r.homeownership_rate for r in records]
    mean_ownership = sum(ownership_rates) / n if n > 0 else float("nan")

    # Cross-sectional evaluation using the standard targets
    sim_result = SimulationResult(records=records)
    cross = evaluate_simulation(sim_result, warm_up=warm_up)

    return HistoricalEvaluationReport(
        scenario_name=result.scenario_name,
        n_periods=n,
        price_correlation=result.price_correlation(),
        price_rmse=result.price_rmse(),
        price_rmse_pct=result.price_rmse_pct(),
        directional_accuracy=result.directional_accuracy(),
        mean_homeownership=mean_ownership,
        cross_sectional=cross,
    )
