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

        # Housing assets
        self.properties: list[Property] = []
        self.mortgages: list = []  # list[Mortgage]

        # Markets
        self.goods_market = GoodsMarket(config=self.config.goods_market)
        self.labor_market = LaborMarket(config=self.config.labor_market)
        self.credit_market = CreditMarket(config=self.config.credit_market)
        self.housing_market = HousingMarket(config=self.config.housing_market)

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
                    mortgage_config=cfg.mortgage,
                )
            )

        # --- Initial employment: assign some households to firms ---
        self._initial_employment()

        # --- Initial housing: create properties and assign tenure ---
        self._initial_housing()

        # --- Wire markets ---
        self.goods_market.set_agents(self.firms, self.households, self.government)
        self.labor_market.set_agents(self.firms, self.households, self._rng)
        self.credit_market.set_agents(self.firms, self.banks, self._rng)
        self.housing_market.set_agents(
            self.properties, self.households, self.banks, self.mortgages, rng=self._rng
        )

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

    def _initial_housing(self) -> None:
        """Create the initial housing stock and assign tenure.

        Roughly 64% of households become owner-occupiers (matching the
        English Housing Survey).  The remaining households are renters.
        """
        cfg = self.config.properties
        n_props = min(cfg.count, len(self.households) * 2)

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
            ptype_idx = self._rng.choice(len(cfg.types), p=cfg.type_shares)
            ptype = cfg.types[int(ptype_idx)]
            quality = float(np.clip(self._rng.normal(0.5, 0.15), 0.05, 0.95))
            multiplier = region_price.get(region, 1.0)
            base_price = cfg.average_price * multiplier
            price = float(self._rng.lognormal(np.log(base_price), 0.3))
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
        self._rng.shuffle(prop_indices)

        for i in range(n_owners):
            hh = self.households[i]
            prop = self.properties[prop_indices[i]]
            prop.owner_id = hh.agent_id
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
                rental_prop.tenant_id = hh.agent_id
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
        for mortgage in list(self.mortgages):
            if not mortgage.in_arrears:
                continue
            # Find the lending bank
            bank = None
            for b in self.banks:
                if b.agent_id == mortgage.lender_id:
                    bank = b
                    break
            if bank is None:
                continue
            if not bank.assess_foreclosure(mortgage):
                continue

            # Foreclose: bank takes possession, household loses home
            borrower = None
            for hh in self.households:
                if hh.agent_id == mortgage.borrower_id:
                    borrower = hh
                    break

            bank.record_mortgage_default(mortgage.outstanding)

            if borrower:
                borrower.tenure = "renter"
                borrower.property_id = None
                borrower.mortgage = None
                borrower.housing_wealth = 0.0

            # Mark property as available
            for prop in self.properties:
                if prop.property_id == mortgage.property_id:
                    prop.owner_id = None
                    prop.on_market = False
                    break

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
        self.current_period += 1

        # 1. Government begins period
        self.government.begin_period()

        # 2. Central bank sets policy rate
        self.central_bank.step()

        # 3. Banks update lending rates and mortgage rates
        for bank in self.banks:
            bank.set_policy_rate(self.central_bank.policy_rate)
            bank.set_mortgage_rate(self.central_bank.policy_rate)

        # 4. Credit market clears
        self.credit_market.clear()

        # 5. Firms step
        for firm in self.firms:
            firm.step()

        # 6. Labour market clears
        labor_state = self.labor_market.clear()

        # 7. Banks assess foreclosures
        foreclosures = self._process_foreclosures()

        # 8. Households step
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

        # 9. Households make buy/sell decisions
        mortgage_rate = self.banks[0].mortgage_rate if self.banks else 0.04
        rental_yield = self.config.housing_market.rental_yield
        markup = self.config.housing_market.initial_markup
        for hh in self.households:
            hh.decide_buy_or_rent(
                average_price=self.housing_market.average_price,
                mortgage_rate=mortgage_rate,
                rental_yield=rental_yield,
                price_history=self.housing_market.price_history,
            )
            # Owners may decide to sell (~2% per period, or if unemployed)
            if hh.tenure == "owner_occupier" and hh.property_id:
                sell_prob = 0.02
                if not hh.employed:
                    sell_prob = 0.10  # financial stress
                if float(self._rng.random()) < sell_prob:
                    hh.wants_to_sell = True
                    for prop in self.properties:
                        if prop.property_id == hh.property_id and not prop.on_market:
                            prop.list_for_sale(initial_markup=markup)
                            break

        # 10. Housing market clears
        self.housing_market.set_period(self.current_period)
        housing_state = self.housing_market.clear()

        # 11. Government spending
        gdp = sum(f.turnover for f in self.firms if not f.bankrupt)
        self.government.gdp_estimate = gdp
        self.government.calculate_spending()

        # 12. Goods market clears
        goods_state = self.goods_market.clear(rng=self._rng)

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
        self.central_bank.update_observations(
            inflation=goods_state["inflation"],
            output_gap=0.0,  # simplified: no potential GDP estimation yet
        )

        # 16. Bank step
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
            average_house_price=housing_state["average_price"],
            housing_transactions=housing_state["transactions"],
            housing_listings=housing_state["listings"],
            homeownership_rate=housing_state["homeownership_rate"],
            house_price_inflation=housing_state["house_price_inflation"],
            total_mortgage_lending=housing_state["total_mortgage_lending"],
            foreclosures=foreclosures,
        )
