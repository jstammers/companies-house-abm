"""Simulation model orchestrator for the ABM.

The :class:`Simulation` class owns all agents and markets and drives
the period-by-period execution loop described in the design document.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from itertools import chain
from typing import TYPE_CHECKING

import numpy as np
from mesa.agent import AgentSet
from mesa.datacollection import DataCollector
from mesa.model import Model

from companies_house_abm.abm.agents.bank import Bank
from companies_house_abm.abm.agents.central_bank import CentralBank
from companies_house_abm.abm.agents.firm import Firm
from companies_house_abm.abm.agents.government import Government
from companies_house_abm.abm.agents.household import Household
from companies_house_abm.abm.assets.property import Property
from companies_house_abm.abm.config import ModelConfig, load_config
from companies_house_abm.abm.markets.credit import CreditMarket
from companies_house_abm.abm.markets.goods import GoodsMarket
from companies_house_abm.abm.markets.housing import HousingMarket
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
    # Housing
    average_house_price: float = 0.0
    housing_transactions: int = 0
    housing_listings: int = 0
    homeownership_rate: float = 0.0
    house_price_inflation: float = 0.0
    total_mortgage_lending: float = 0.0
    foreclosures: int = 0


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

    @property
    def house_price_series(self) -> list[float]:
        """Average house price across all recorded periods."""
        return [r.average_house_price for r in self.records]

    @property
    def homeownership_series(self) -> list[float]:
        """Homeownership rate across all recorded periods."""
        return [r.homeownership_rate for r in self.records]


class SimulationDataCollector(DataCollector):
    """Mesa data collector configured for the simulation's macro metrics."""

    metric_names = tuple(field.name for field in fields(PeriodRecord))

    def __init__(self) -> None:
        super().__init__(
            model_reporters={
                name: self._model_metric_reporter(name) for name in self.metric_names
            }
        )

    @staticmethod
    def _model_metric_reporter(name: str):
        return lambda model: getattr(model.latest_record, name)


class Simulation(Model):
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
        seed = self.config.simulation.seed
        super().__init__(rng=seed)
        self.latest_record = PeriodRecord()
        self.datacollector = SimulationDataCollector()

        # Agents
        self.firms: list[Firm] = []
        self.households: list[Household] = []
        self.banks: list[Bank] = []
        self.central_bank = CentralBank(model=self, taylor_rule=self.config.taylor_rule)
        self.government = Government(
            model=self,
            fiscal_rule=self.config.fiscal_rule,
            transfers=self.config.transfers,
        )

        # Housing assets
        self.properties: list[Property] = []
        self.mortgages: list = []  # list[Mortgage]

        # Markets
        self.goods_market = GoodsMarket(config=self.config.goods_market)
        self.labor_market = LaborMarket(config=self.config.labor_market)
        self.credit_market = CreditMarket(config=self.config.credit_market)
        self.housing_market = HousingMarket(config=self.config.housing_market)

        self.current_period: int = 0

    def _attach_model(self, agent: Any) -> Any:
        """Attach and register an economic agent with the Mesa model."""
        agent.model = self
        self.register_agent(agent)
        return agent

    def _clear_registered_agents(self) -> None:
        """Remove existing registered agents before re-initialisation."""
        for agent in chain(self.firms, self.households, self.banks):
            if getattr(agent, "model", None) is self and hasattr(agent, "unique_id"):
                try:
                    self.deregister_agent(agent)
                except KeyError:
                    continue

    def _agent_set(self, agents: list[Any]) -> AgentSet:
        """Create a Mesa AgentSet from the current agent list."""
        return AgentSet(agents, random=self.random)

    @property
    def firm_agents(self) -> AgentSet:
        """Mesa AgentSet view over firm agents."""
        return self._agent_set(self.firms)

    @property
    def household_agents(self) -> AgentSet:
        """Mesa AgentSet view over household agents."""
        return self._agent_set(self.households)

    @property
    def bank_agents(self) -> AgentSet:
        """Mesa AgentSet view over bank agents."""
        return self._agent_set(self.banks)

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
        self._clear_registered_agents()
        self.firms = []
        self.households = []
        self.banks = []
        self.properties = []
        self.mortgages = []
        self.latest_record = PeriodRecord()
        self.datacollector = SimulationDataCollector()

        # --- Firms ---
        n_firms = min(cfg.firms.sample_size, 1000)  # cap for prototype
        if n_firms > 0:
            # Size firms to the available workforce.  With 1 000 firms and
            # 5 000 household agents, the mean firm size must be ≈ 5 so that
            # total employee slots (firms x mean_size) ≈ n_households.  The
            # original range of 1-49 (mean 25) produced 25 000 slots for
            # 5 000 households: firms paid wages for 20 000 phantom workers,
            # making every firm immediately insolvent.
            n_hh = min(cfg.households.count, 5000)
            mean_firm_size = max(1, n_hh // n_firms)
            sectors = [
                cfg.firms.sectors[i % len(cfg.firms.sectors)] for i in range(n_firms)
            ]
            employees = self.rng.integers(1, max(2, mean_firm_size * 2), size=n_firms)
            wage_rates = self.rng.lognormal(np.log(35_000 / 4), 0.3, size=n_firms)
            # Calibrate turnover so the wage share is 35-70 % (UK SME range).
            # Drawing turnover independently can produce wage_share > 200 %,
            # causing immediate equity collapse and mass bankruptcy in period 1.
            wage_bills = employees * wage_rates
            wage_shares = np.clip(self.rng.normal(0.50, 0.10, size=n_firms), 0.35, 0.70)
            turnover = wage_bills / wage_shares
            # Capital set to ~2x quarterly turnover so the capacity constraint
            # (capital x utilisation_target) does not bind in period 1 and
            # prevent firms from producing enough to cover their wage bill.
            capital = self.rng.lognormal(np.log(np.maximum(turnover * 2.0, 1.0)), 0.4)
            cash = self.rng.lognormal(np.log(np.maximum(turnover * 0.15, 1.0)), 0.4)

            self.firms = [
                self._attach_model(
                    Firm(
                        self,
                        sector=sectors[i],
                        employees=int(employees[i]),
                        wage_bill=float(wage_bills[i]),
                        turnover=float(turnover[i]),
                        capital=float(capital[i]),
                        cash=float(cash[i]),
                        debt=0.0,
                        equity=float(capital[i] + cash[i]),
                        behavior=cfg.firm_behavior,
                    )
                )
                for i in range(n_firms)
            ]

        # --- Households ---
        n_hh = min(cfg.households.count, 5000)
        if n_hh > 0:
            incomes = self.rng.lognormal(
                np.log(cfg.households.income_mean),
                cfg.households.income_std / cfg.households.income_mean,
                size=n_hh,
            )
            wealths = self.rng.pareto(cfg.households.wealth_shape, size=n_hh) * incomes
            mpcs = np.clip(
                self.rng.normal(
                    cfg.households.mpc_mean, cfg.households.mpc_std, size=n_hh
                ),
                0.1,
                0.99,
            )
            self.households = [
                self._attach_model(
                    Household(
                        model=self,
                        income=float(incomes[i] / 4),  # quarterly
                        wealth=float(wealths[i]),
                        mpc=float(mpcs[i]),
                        behavior=cfg.household_behavior,
                    )
                )
                for i in range(n_hh)
            ]

        # --- Banks ---
        if cfg.banks.count > 0:
            bank_capital = self.rng.lognormal(np.log(1e9), 0.5, size=cfg.banks.count)
            self.banks = [
                self._attach_model(
                    Bank(
                        model=self,
                        capital=float(bank_capital[i]),
                        reserves=float(bank_capital[i] * 0.1),
                        config=cfg.banks,
                        behavior=cfg.bank_behavior,
                        mortgage_config=cfg.mortgage,
                    )
                )
                for i in range(cfg.banks.count)
            ]

        # --- Initial employment: assign some households to firms ---
        self._initial_employment()

        # --- Initial housing: create properties and assign tenure ---
        self._initial_housing()

        # --- Wire markets ---
        self.goods_market.set_agents(self.firms, self.households, self.government)
        self.labor_market.set_agents(self.firms, self.households, self.rng)
        self.credit_market.set_agents(self.firms, self.banks, self.rng)
        self.housing_market.set_agents(
            self.properties, self.households, self.banks, self.mortgages, rng=self.rng
        )

    def _initial_employment(self) -> None:
        """Assign households to firms for initial employment."""
        hh_idx = 0
        for firm in self.firms:
            for _ in range(firm.employees):
                if hh_idx >= len(self.households):
                    break
                hh = self.households[hh_idx]
                hh.become_employed(firm.unique_id, firm.wage_rate)
                hh_idx += 1
            if hh_idx >= len(self.households):
                break

        # Reconcile firm.employees and wage_bill to the actual number of
        # household agents assigned.  Random firm sizes and sequential
        # assignment can leave firms with more "employees" than household
        # agents, causing phantom wage payments that drive firms insolvent.
        actual: dict[str, int] = {f.unique_id: 0 for f in self.firms}
        for hh in self.households:
            if hh.employer_id and hh.employer_id in actual:
                actual[hh.employer_id] += 1
        for firm in self.firms:
            n = actual[firm.unique_id]
            firm.employees = n
            firm.wage_bill = n * firm.wage_rate

    def _initial_housing(self) -> None:
        """Create the initial housing stock and assign tenure.

        Roughly 64% of households become owner-occupiers (matching the
        English Housing Survey).  The remaining households are renters.
        """
        cfg = self.config.properties
        # Size the housing stock to match the household count.  Using 2x
        # households creates ~50 % vacancy when agents are capped, which floods
        # the market on period 1 with thousands of cheap listings, crashing the
        # average price and inflating homeownership well above the 64% target.
        n_props = min(cfg.count, len(self.households))

        # Regional price multipliers (London ~1.8x, North East ~0.5x)
        region_price = {
            "london": 1.80,
            "south_east": 1.30,
            "east": 1.10,
            "south_west": 1.00,
            "west_midlands": 0.80,
            "east_midlands": 0.78,
            "north_west": 0.70,
            "north_east": 0.50,
            "yorkshire": 0.65,
            "scotland": 0.60,
            "wales": 0.60,
        }

        for i in range(n_props):
            region = cfg.regions[i % len(cfg.regions)]
            ptype_idx = self.rng.choice(len(cfg.types), p=cfg.type_shares)
            ptype = cfg.types[int(ptype_idx)]
            quality = float(np.clip(self.rng.normal(0.5, 0.15), 0.05, 0.95))
            multiplier = region_price.get(region, 1.0)
            base_price = cfg.average_price * multiplier
            price = float(self.rng.lognormal(np.log(base_price), 0.3))
            rental_yield = self.config.housing_market.rental_yield
            monthly_rent = price * rental_yield / 12.0

            self.properties.append(
                Property(
                    property_id=f"prop_{i:05d}",
                    region=region,
                    property_type=ptype,
                    quality=quality,
                    market_value=price,
                    last_transaction_price=price,
                    rental_value=monthly_rent,
                )
            )

        # Assign ~64% of households as owner-occupiers
        target_ownership = 0.64
        n_owners = int(len(self.households) * target_ownership)
        n_owners = min(n_owners, n_props)

        # Shuffle property indices for random assignment
        prop_indices = list(range(n_props))
        self.rng.shuffle(prop_indices)

        for i in range(n_owners):
            hh = self.households[i]
            prop = self.properties[prop_indices[i]]
            prop.owner_id = hh.unique_id
            hh.tenure = "owner_occupier"
            hh.property_id = prop.property_id
            hh.housing_wealth = prop.market_value
            hh.rent = 0.0

        # Remaining households are renters
        for i in range(n_owners, len(self.households)):
            hh = self.households[i]
            hh.tenure = "renter"
            # Assign to a random property as tenant
            if n_props > n_owners:
                rental_idx = prop_indices[
                    n_owners + (i - n_owners) % (n_props - n_owners)
                ]
                rental_prop = self.properties[rental_idx]
                rental_prop.is_rented = True
                rental_prop.tenant_id = hh.unique_id
                hh.rent = rental_prop.rental_value

        # List vacant (unowned, unrented) properties for sale
        markup = self.config.housing_market.initial_markup
        for prop in self.properties:
            if prop.owner_id is None and not prop.is_rented:
                prop.list_for_sale(initial_markup=markup)

    def _process_foreclosures(self) -> int:
        """Banks assess mortgages in arrears and foreclose if needed.

        Returns:
            Number of foreclosures this period.
        """
        count = 0
        banks_by_id = {bank.unique_id: bank for bank in self.banks}
        households_by_id = {
            household.unique_id: household for household in self.households
        }
        properties_by_id = {prop.property_id: prop for prop in self.properties}
        for mortgage in list(self.mortgages):
            if not mortgage.in_arrears:
                continue
            bank = banks_by_id.get(mortgage.lender_id)
            if bank is None:
                continue
            if not bank.assess_foreclosure(mortgage):
                continue

            # Foreclose: bank takes possession, household loses home
            borrower = households_by_id.get(mortgage.borrower_id)

            bank.record_mortgage_default(mortgage.outstanding)

            if borrower:
                borrower.tenure = "renter"
                borrower.property_id = None
                borrower.mortgage = None
                borrower.housing_wealth = 0.0

            # Mark property as available
            if property_ := properties_by_id.get(mortgage.property_id):
                property_.owner_id = None
                property_.on_market = False

            self.mortgages = [
                m for m in self.mortgages if m.mortgage_id != mortgage.mortgage_id
            ]
            count += 1
        return count

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
            self.step()
            result.records.append(self.latest_record)

            if collect_micro:
                result.firm_states.append([f.get_state() for f in self.firms])
                result.household_states.append([h.get_state() for h in self.households])

        return result

    def step(self) -> None:
        """Execute a single simulation period using the Mesa model API."""
        self.current_period = self.steps
        self.latest_record = self._period_step()
        self.datacollector.collect(self)

    def _period_step(self) -> PeriodRecord:
        """Execute a single period of the simulation.

        The within-period sequence follows the design document:

        1. Government begins period (reset flows).
        2. Central bank sets policy rate.
        3. Banks update lending rates and mortgage rates.
        4. Credit market clears.
        5. Firms step (plan, price, hire/fire, produce, financials).
        6. Labour market clears.
        7. Banks assess foreclosures.
        8. Households step (income, housing payment, consume, save).
        9. Households make buy/sell decisions.
        10. Housing market clears (bilateral matching).
        11. Government spending.
        12. Goods market clears.
        13. Tax collection.
        14. Government ends period (compute deficit/debt).
        15. Central bank observes inflation, output gap, house prices.
        16. Banks step (accounting).

        Returns:
            A :class:`PeriodRecord` for this period.
        """
        firms = self.firm_agents
        households = self.household_agents
        banks = self.bank_agents

        # 1. Government begins period
        self.government.begin_period()

        # 2. Central bank sets policy rate
        self.central_bank.step()

        # 3. Banks update lending rates and mortgage rates
        banks.do("set_policy_rate", self.central_bank.policy_rate)
        banks.do("set_mortgage_rate", self.central_bank.policy_rate)

        # 4. Credit market clears
        self.credit_market.clear()

        # 5. Firms step
        firms.do("step")

        # 6. Labour market clears
        labor_state = self.labor_market.clear()

        # 7. Banks assess foreclosures
        foreclosures = self._process_foreclosures()

        # 8. Households step
        # First set transfer income for unemployed
        avg_wage = labor_state["average_wage"]
        unemployed = households.select(lambda household: not household.employed)
        if len(unemployed) > 0 and avg_wage > 0:
            benefit = self.government.pay_unemployment_benefit(
                avg_wage, len(unemployed)
            )
            per_hh = benefit / len(unemployed)
            unemployed.do(
                lambda household, transfer_income: setattr(
                    household, "transfer_income", transfer_income
                ),
                per_hh,
            )

        households.do("step")

        # Reset transfer income after step
        households.do(lambda household: setattr(household, "transfer_income", 0.0))

        # 9. Households make buy/sell decisions
        mortgage_rate = self.banks[0].mortgage_rate if self.banks else 0.04
        rental_yield = self.config.housing_market.rental_yield
        markup = self.config.housing_market.initial_markup
        properties_by_id = {prop.property_id: prop for prop in self.properties}
        for hh in self.households:
            hh.decide_buy_or_rent(
                average_price=self.housing_market.average_price,
                mortgage_rate=mortgage_rate,
                rental_yield=rental_yield,
                price_history=self.housing_market.price_history,
            )
            # Owners may decide to sell each quarter.
            # UK housing turnover ≈ 6 % of owner-occupied stock per year
            # (≈ 1.1 M transactions / 15 M owner-occupied homes).  At
            # quarterly frequency: 6 % / 4 = 1.5 % per quarter.  The
            # previous value of 4 %/quarter (≈ 16 % annual) was 2.5x too
            # high and caused a rapid listing build-up that crashed prices.
            if hh.tenure == "owner_occupier" and hh.property_id:
                sell_prob = 0.015
                if not hh.employed:
                    sell_prob = 0.04  # financial stress: ~16 % annual
                if float(self.rng.random()) < sell_prob:
                    hh.wants_to_sell = True
                    property_ = properties_by_id.get(hh.property_id)
                    if property_ and not property_.on_market:
                        property_.list_for_sale(initial_markup=markup)

        # 10. Housing market clears
        self.housing_market.set_period(self.current_period)
        housing_state = self.housing_market.clear()

        # 11. Government spending
        gdp = sum(firms.select(lambda firm: not firm.bankrupt).get("turnover"))
        self.government.gdp_estimate = gdp
        self.government.calculate_spending()

        # 12. Goods market clears
        goods_state = self.goods_market.clear(rng=self.rng)

        # 13. Tax collection
        for firm in self.firms:
            if firm.profit > 0 and not firm.bankrupt:
                tax = self.government.collect_corporate_tax(firm.profit)
                firm.cash -= tax

        for hh in self.households:
            if hh.income > 0:
                tax = self.government.collect_income_tax(hh.income)
                hh.wealth -= tax

        # 14. Government ends period
        self.government.step()
        self.government.end_period()

        # 15. Central bank observes
        # Clip the goods-market inflation before passing it to the Taylor rule.
        # The goods-market price index tracks abstract firm unit-cost prices, not
        # a calibrated CPI.  Its period-on-period variance is far larger than real
        # CPI movements, and feeding raw spikes (often >100 %) into the Taylor
        # rule sends interest rates to implausible levels and shuts down the
        # housing market.  A ±5 % clip per period is consistent with the range
        # over which the Taylor rule is designed to operate.
        # Clip at the central bank's own inflation target (2 %).  When goods-market
        # inflation is at or above target the Taylor rule holds the rate steady;
        # it only cuts rates when observed inflation falls below target.  This
        # prevents the accumulated goods-market price volatility (driven by
        # firm repricing, not real CPI) from pushing the policy rate above the
        # break-even mortgage affordability threshold and shutting down housing
        # market transactions for extended periods.
        _INFLATION_CLIP = self.central_bank.inflation_target
        clipped_inflation = max(
            min(goods_state["inflation"], _INFLATION_CLIP), -_INFLATION_CLIP
        )
        self.central_bank.update_observations(
            inflation=clipped_inflation,
            output_gap=0.0,  # simplified: no potential GDP estimation yet
        )

        # 16. Bank step
        banks.do("step")

        # Record
        bankruptcies = len(firms.select(lambda firm: firm.bankrupt))

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
            average_house_price=housing_state["average_price"],
            housing_transactions=housing_state["transactions"],
            housing_listings=housing_state["listings"],
            homeownership_rate=housing_state["homeownership_rate"],
            house_price_inflation=housing_state["house_price_inflation"],
            total_mortgage_lending=housing_state["total_mortgage_lending"],
            foreclosures=foreclosures,
        )
