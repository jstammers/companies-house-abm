"""Historical simulation runner for the UK housing market ABM.

The :class:`HistoricalSimulation` wraps the core :class:`Simulation` and
injects time-varying exogenous inputs (Bank Rate, mortgage rates, income
growth, regulatory events) period-by-period from a
:class:`~companies_house_abm.abm.scenarios.HistoricalScenario`.

The core ``Simulation.step()`` is **not modified** — all injection happens
between steps by manipulating agent and market state directly.

Usage::

    from companies_house_abm.abm.historical import HistoricalSimulation
    from companies_house_abm.abm.scenarios import build_uk_2013_2024

    scenario = build_uk_2013_2024()
    hsim = HistoricalSimulation(scenario)
    result = hsim.run()
    print(f"Price correlation: {result.price_correlation():.3f}")
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from companies_house_abm.abm.config import (
    ModelConfig,
    load_config,
)
from companies_house_abm.abm.model import PeriodRecord, Simulation

if TYPE_CHECKING:
    from companies_house_abm.abm.scenarios import HistoricalScenario

logger = logging.getLogger(__name__)


@dataclass
class HistoricalResult:
    """Simulation output paired with actual historical data for comparison.

    Attributes:
        scenario_name: Name of the scenario that was run.
        quarter_labels: Calendar quarter labels for each period.
        records: Per-period aggregate statistics from the simulation.
        actual_hpi: Actual UK house prices per quarter (from scenario).
        actual_transactions: Actual quarterly transactions (from scenario).
        bank_rate_input: Bank Rate path that was fed in.
        mortgage_rate_input: Mortgage rate path that was fed in.
    """

    scenario_name: str = ""
    quarter_labels: list[str] = field(default_factory=list)
    records: list[PeriodRecord] = field(default_factory=list)
    actual_hpi: list[float] = field(default_factory=list)
    actual_transactions: list[int] = field(default_factory=list)
    bank_rate_input: list[float] = field(default_factory=list)
    mortgage_rate_input: list[float] = field(default_factory=list)

    @property
    def simulated_prices(self) -> list[float]:
        """Simulated average house prices per period."""
        return [r.average_house_price for r in self.records]

    @property
    def simulated_transactions(self) -> list[int]:
        """Simulated housing transactions per period."""
        return [r.housing_transactions for r in self.records]

    def price_correlation(self) -> float:
        """Pearson correlation between simulated and actual house prices.

        Returns ``NaN`` if either series has zero variance or if the
        series lengths do not match.
        """
        sim = self.simulated_prices
        act = self.actual_hpi
        n = min(len(sim), len(act))
        if n < 2:
            return float("nan")
        sim, act = sim[:n], act[:n]
        return _pearson(sim, act)

    def price_rmse(self) -> float:
        """Root mean squared error between simulated and actual prices.

        Returns ``NaN`` if the series lengths do not match.
        """
        sim = self.simulated_prices
        act = self.actual_hpi
        n = min(len(sim), len(act))
        if n == 0:
            return float("nan")
        pairs = zip(sim[:n], act[:n], strict=True)
        mse = sum((s - a) ** 2 for s, a in pairs) / n
        return math.sqrt(mse)

    def price_rmse_pct(self) -> float:
        """RMSE as a percentage of the mean actual price.

        Returns ``NaN`` if the actual series is empty.
        """
        act = self.actual_hpi
        if not act:
            return float("nan")
        mean_act = sum(act) / len(act)
        if mean_act == 0:
            return float("nan")
        return self.price_rmse() / mean_act

    def directional_accuracy(self) -> float:
        """Fraction of quarters where simulated price direction matches actual.

        Direction is defined as the sign of the quarter-on-quarter change.
        Returns ``NaN`` if fewer than 2 periods are available.
        """
        sim = self.simulated_prices
        act = self.actual_hpi
        n = min(len(sim), len(act))
        if n < 2:
            return float("nan")
        correct = 0
        for i in range(1, n):
            sim_dir = sim[i] - sim[i - 1]
            act_dir = act[i] - act[i - 1]
            if (sim_dir >= 0) == (act_dir >= 0):
                correct += 1
        return correct / (n - 1)

    def summary(self) -> str:
        """Return a human-readable summary of the historical fit."""
        lines = [
            f"Historical Simulation: {self.scenario_name}",
            f"Periods: {len(self.records)}",
            f"Price correlation: {self.price_correlation():.3f}",
            f"Price RMSE: {self.price_rmse():,.0f}",
            f"Price RMSE (%): {self.price_rmse_pct():.1%}",
            f"Directional accuracy: {self.directional_accuracy():.1%}",
        ]
        if self.records:
            last = self.records[-1]
            lines.extend(
                [
                    f"Final simulated price: {last.average_house_price:,.0f}",
                    f"Homeownership rate: {last.homeownership_rate:.1%}",
                    f"Final policy rate: {last.policy_rate:.2%}",
                ]
            )
        return "\n".join(lines)


class HistoricalSimulation:
    """Run a simulation driven by historical exogenous data.

    This wrapper:

    1. Configures the :class:`Simulation` with initial conditions matching
       the scenario's start quarter.
    2. Disables the Taylor rule so the Bank Rate is set exogenously.
    3. Before each ``step()``, injects the historical Bank Rate, mortgage
       rate, income growth, and any regulatory events scheduled for that
       period.

    Args:
        scenario: The historical scenario to run.
        base_config: Starting model configuration.  If ``None``, loads
            from the default YAML.
    """

    def __init__(
        self,
        scenario: HistoricalScenario,
        base_config: ModelConfig | None = None,
    ) -> None:
        self.scenario = scenario
        self._base_config = base_config or load_config()

        # Prepare config with initial conditions
        self._config = self._calibrate_initial_conditions()
        self._sim = Simulation(self._config)
        self._sim.initialize_agents()

        # Pre-index regulatory events by period for fast lookup
        self._events_by_period: dict[int, list] = {}
        for event in scenario.regulatory_events:
            self._events_by_period.setdefault(event.period, []).append(event)

    def _calibrate_initial_conditions(self) -> ModelConfig:
        """Set initial config to match the scenario's start quarter."""
        scenario = self.scenario
        cfg = self._base_config

        # Set average house price to historical start value
        props = replace(cfg.properties, average_price=scenario.initial_average_price)

        # Disable Taylor rule — Bank Rate will be set exogenously
        taylor = replace(cfg.taylor_rule, active=False)

        # Set initial mortgage spread to match the first-period mortgage rate.
        # At t=0, risk_premium ~ 0, so spread ~ mortgage_rate - bank_rate.
        initial_bank_rate = (
            scenario.bank_rate_path[0] if scenario.bank_rate_path else 0.005
        )
        initial_mortgage_rate = (
            scenario.mortgage_rate_path[0] if scenario.mortgage_rate_path else 0.034
        )
        implied_spread = max(initial_mortgage_rate - initial_bank_rate, 0.005)
        mortgage = replace(cfg.mortgage, mortgage_spread=implied_spread)

        return replace(
            cfg,
            properties=props,
            taylor_rule=taylor,
            mortgage=mortgage,
        )

    def run(self) -> HistoricalResult:
        """Execute the full historical simulation.

        Returns:
            A :class:`HistoricalResult` with simulated and actual data.
        """
        scenario = self.scenario
        sim = self._sim
        records: list[PeriodRecord] = []

        for t in range(scenario.n_periods):
            # 1. Inject exogenous Bank Rate
            if t < len(scenario.bank_rate_path):
                sim.central_bank.policy_rate = scenario.bank_rate_path[t]
                sim.central_bank._previous_rate = scenario.bank_rate_path[t]

            # 2. Apply regulatory events for this period
            self._apply_regulatory_events(t)

            # 3. Apply income growth to household incomes
            if t < len(scenario.income_growth_path):
                growth = scenario.income_growth_path[t]
                if growth != 0:
                    for hh in sim.households:
                        hh.income *= 1.0 + growth

            # 4. Override mortgage rate on banks if we have historical data
            # (do this after step so that set_mortgage_rate in step() doesn't
            #  overwrite, but actually we need to do it after the bank rate
            #  propagation in step()... so we'll let step() handle bank rate
            #  propagation and then correct the mortgage rate afterward)

            # 5. Run the simulation step
            record = sim.step()

            # 6. Post-step mortgage rate correction: if the scenario provides
            # a historical mortgage rate, override what the banks computed
            # so that next period's affordability checks use the right rate.
            if t < len(scenario.mortgage_rate_path):
                target_rate = scenario.mortgage_rate_path[t]
                for bank in sim.banks:
                    bank.mortgage_rate = target_rate

            records.append(record)

            if t % 4 == 0:
                quarter = (
                    scenario.quarter_labels[t]
                    if t < len(scenario.quarter_labels)
                    else f"P{t}"
                )
                logger.info(
                    "Period %d (%s): price=%.0f, txns=%d, rate=%.2f%%",
                    t,
                    quarter,
                    record.average_house_price,
                    record.housing_transactions,
                    record.policy_rate * 100,
                )

        return HistoricalResult(
            scenario_name=scenario.name,
            quarter_labels=scenario.quarter_labels,
            records=records,
            actual_hpi=scenario.actual_hpi,
            actual_transactions=scenario.actual_transactions,
            bank_rate_input=scenario.bank_rate_path,
            mortgage_rate_input=scenario.mortgage_rate_path,
        )

    def _apply_regulatory_events(self, period: int) -> None:
        """Apply any regulatory events scheduled for *period*."""
        events = self._events_by_period.get(period, [])
        if not events:
            return

        sim = self._sim
        for event in events:
            logger.info(
                "Period %d (%s): %s",
                period,
                event.quarter,
                event.description,
            )

            # Apply mortgage config overrides
            if event.mortgage_overrides:
                new_mortgage = replace(sim.config.mortgage, **event.mortgage_overrides)
                sim.config = replace(sim.config, mortgage=new_mortgage)
                # Update bank references
                for bank in sim.banks:
                    bank._mortgage_config = new_mortgage

            # Apply housing market config overrides
            if event.housing_overrides:
                new_housing = replace(
                    sim.config.housing_market, **event.housing_overrides
                )
                sim.config = replace(sim.config, housing_market=new_housing)
                sim.housing_market.config = new_housing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pearson(x: list[float], y: list[float]) -> float:
    """Compute the Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return float("nan")
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=True))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if sx == 0 or sy == 0:
        return float("nan")
    return cov / (sx * sy)
