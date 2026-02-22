"""Simulation model orchestrator for the ABM.

The :class:`Simulation` class owns all agents and markets and drives
the period-by-period execution loop described in the design document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from companies_house_abm.abm.agents.bank import Bank
from companies_house_abm.abm.agents.central_bank import CentralBank
from companies_house_abm.abm.agents.firm import Firm
from companies_house_abm.abm.agents.government import Government
from companies_house_abm.abm.agents.household import Household
from companies_house_abm.abm.config import ModelConfig, load_config
from companies_house_abm.abm.markets.credit import CreditMarket
from companies_house_abm.abm.markets.goods import GoodsMarket
from companies_house_abm.abm.markets.labor import LaborMarket

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@dataclass
class PeriodRecord:
    """Aggregate statistics recorded for a single period."""

    period: int = 0
    gdp: float = 0.0
    inflation: float = 0.0
    unemployment_rate: float = 0.0
    average_wage: float = 0.0
    policy_rate: float = 0.0
    government_deficit: float = 0.0
    government_debt: float = 0.0
    total_lending: float = 0.0
    firm_bankruptcies: int = 0
    total_employment: int = 0


@dataclass
class SimulationResult:
    """Container for the full simulation output."""

    records: list[PeriodRecord] = field(default_factory=list)
    firm_states: list[list[dict[str, Any]]] = field(default_factory=list)
    household_states: list[list[dict[str, Any]]] = field(default_factory=list)

    @property
    def gdp_series(self) -> list[float]:
        """GDP values across all recorded periods."""
        return [r.gdp for r in self.records]

    @property
    def inflation_series(self) -> list[float]:
        """Inflation values across all recorded periods."""
        return [r.inflation for r in self.records]

    @property
    def unemployment_series(self) -> list[float]:
        """Unemployment rate values across all recorded periods."""
        return [r.unemployment_rate for r in self.records]


class Simulation:
    """The top-level simulation orchestrator.

    Usage::

        sim = Simulation.from_config()
        result = sim.run()

    Attributes:
        config: The model configuration.
        firms: List of firm agents.
        households: List of household agents.
        banks: List of bank agents.
        central_bank: The central bank agent.
        government: The government agent.
        goods_market: The goods market.
        labor_market: The labor market.
        credit_market: The credit market.
        current_period: The current simulation period.
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        self.config = config or ModelConfig()
        self._rng = np.random.default_rng(self.config.simulation.seed)

        # Agents
        self.firms: list[Firm] = []
        self.households: list[Household] = []
        self.banks: list[Bank] = []
        self.central_bank = CentralBank(taylor_rule=self.config.taylor_rule)
        self.government = Government(
            fiscal_rule=self.config.fiscal_rule,
            transfers=self.config.transfers,
        )

        # Markets
        self.goods_market = GoodsMarket(config=self.config.goods_market)
        self.labor_market = LaborMarket(config=self.config.labor_market)
        self.credit_market = CreditMarket(config=self.config.credit_market)

        self.current_period: int = 0

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, path: Path | None = None) -> Simulation:
        """Create a simulation from a YAML configuration file.

        Args:
            path: Path to configuration YAML.  Uses defaults when *None*.

        Returns:
            A configured :class:`Simulation` instance with initialised
            agents.
        """
        config = load_config(path)
        sim = cls(config)
        sim.initialize_agents()
        return sim

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize_agents(self) -> None:
        """Create the initial population of agents from configuration."""
        cfg = self.config

        # --- Firms ---
        n_firms = min(cfg.firms.sample_size, 1000)  # cap for prototype
        for i in range(n_firms):
            sector = cfg.firms.sectors[i % len(cfg.firms.sectors)]
            employees = int(self._rng.integers(1, 50))
            wage_rate = float(self._rng.lognormal(np.log(35_000 / 4), 0.3))
            turnover = float(self._rng.lognormal(np.log(100_000), 1.0))
            capital = float(self._rng.lognormal(np.log(50_000), 1.0))
            cash = float(self._rng.lognormal(np.log(10_000), 0.8))

            self.firms.append(
                Firm(
                    agent_id=f"firm_{i:05d}",
                    sector=sector,
                    employees=employees,
                    wage_bill=employees * wage_rate,
                    turnover=turnover,
                    capital=capital,
                    cash=cash,
                    debt=0.0,
                    equity=capital + cash,
                    behavior=cfg.firm_behavior,
                )
            )

        # --- Households ---
        n_hh = min(cfg.households.count, 5000)
        for i in range(n_hh):
            income = float(
                self._rng.lognormal(
                    np.log(cfg.households.income_mean),
                    cfg.households.income_std / cfg.households.income_mean,
                )
            )
            wealth = float(self._rng.pareto(cfg.households.wealth_shape) * income)
            mpc = float(
                np.clip(
                    self._rng.normal(cfg.households.mpc_mean, cfg.households.mpc_std),
                    0.1,
                    0.99,
                )
            )
            self.households.append(
                Household(
                    agent_id=f"hh_{i:05d}",
                    income=income / 4,  # quarterly
                    wealth=wealth,
                    mpc=mpc,
                    behavior=cfg.household_behavior,
                )
            )

        # --- Banks ---
        for i in range(cfg.banks.count):
            capital = float(self._rng.lognormal(np.log(1e9), 0.5))
            self.banks.append(
                Bank(
                    agent_id=f"bank_{i:02d}",
                    capital=capital,
                    reserves=capital * 0.1,
                    config=cfg.banks,
                    behavior=cfg.bank_behavior,
                )
            )

        # --- Initial employment: assign some households to firms ---
        self._initial_employment()

        # --- Wire markets ---
        self.goods_market.set_agents(self.firms, self.households, self.government)
        self.labor_market.set_agents(self.firms, self.households, self._rng)
        self.credit_market.set_agents(self.firms, self.banks, self._rng)

    def _initial_employment(self) -> None:
        """Assign households to firms for initial employment."""
        hh_idx = 0
        for firm in self.firms:
            for _ in range(firm.employees):
                if hh_idx >= len(self.households):
                    break
                hh = self.households[hh_idx]
                hh.become_employed(firm.agent_id, firm.wage_rate)
                hh_idx += 1
            if hh_idx >= len(self.households):
                break

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(
        self,
        periods: int | None = None,
        collect_micro: bool = False,
    ) -> SimulationResult:
        """Run the simulation for the specified number of periods.

        Args:
            periods: Number of periods to run.  Defaults to the value in
                configuration.
            collect_micro: Whether to collect agent-level states each period.

        Returns:
            A :class:`SimulationResult` with aggregate and (optionally)
            micro data.
        """
        n = periods or self.config.simulation.periods
        result = SimulationResult()

        for _ in range(n):
            record = self.step()
            result.records.append(record)

            if collect_micro:
                result.firm_states.append([f.get_state() for f in self.firms])
                result.household_states.append([h.get_state() for h in self.households])

        return result

    def step(self) -> PeriodRecord:
        """Execute a single period of the simulation.

        The within-period sequence follows the design document:

        1. Government begins period (reset flows).
        2. Central bank sets policy rate.
        3. Banks update lending rates.
        4. Credit market clears.
        5. Firms step (plan, price, hire/fire, produce, financials).
        6. Labour market clears.
        7. Households step (income, consume, save).
        8. Goods market clears.
        9. Government collects taxes and pays transfers.
        10. Government ends period (compute deficit/debt).
        11. Central bank observes inflation and output gap.
        12. Record aggregate statistics.

        Returns:
            A :class:`PeriodRecord` for this period.
        """
        self.current_period += 1

        # 1. Government begins period
        self.government.begin_period()

        # 2. Central bank sets policy rate
        self.central_bank.step()

        # 3. Banks update lending rates
        for bank in self.banks:
            bank.set_policy_rate(self.central_bank.policy_rate)

        # 4. Credit market clears
        self.credit_market.clear()

        # 5. Firms step
        for firm in self.firms:
            firm.step()

        # 6. Labour market clears
        labor_state = self.labor_market.clear()

        # 7. Households step
        # First set transfer income for unemployed
        avg_wage = labor_state["average_wage"]
        unemployed = [h for h in self.households if not h.employed]
        if unemployed and avg_wage > 0:
            benefit = self.government.pay_unemployment_benefit(
                avg_wage, len(unemployed)
            )
            per_hh = benefit / len(unemployed)
            for hh in unemployed:
                hh.transfer_income = per_hh

        for hh in self.households:
            hh.step()

        # Reset transfer income after step
        for hh in self.households:
            hh.transfer_income = 0.0

        # 8. Government spending
        gdp = sum(f.turnover for f in self.firms if not f.bankrupt)
        self.government.gdp_estimate = gdp
        self.government.calculate_spending()

        # 9. Goods market clears
        goods_state = self.goods_market.clear()

        # 10. Tax collection
        for firm in self.firms:
            if firm.profit > 0 and not firm.bankrupt:
                tax = self.government.collect_corporate_tax(firm.profit)
                firm.cash -= tax

        for hh in self.households:
            if hh.income > 0:
                tax = self.government.collect_income_tax(hh.income)
                hh.wealth -= tax

        # 11. Government ends period
        self.government.step()
        self.government.end_period()

        # 12. Central bank observes
        self.central_bank.update_observations(
            inflation=goods_state["inflation"],
            output_gap=0.0,  # simplified: no potential GDP estimation yet
        )

        # 13. Bank step
        for bank in self.banks:
            bank.step()

        # Record
        bankruptcies = sum(1 for f in self.firms if f.bankrupt)

        return PeriodRecord(
            period=self.current_period,
            gdp=gdp,
            inflation=goods_state["inflation"],
            unemployment_rate=labor_state["unemployment_rate"],
            average_wage=labor_state["average_wage"],
            policy_rate=self.central_bank.policy_rate,
            government_deficit=self.government.deficit,
            government_debt=self.government.debt,
            total_lending=self.credit_market.total_lending,
            firm_bankruptcies=bankruptcies,
            total_employment=labor_state["total_employed"],
        )
