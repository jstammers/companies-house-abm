"""Housing market with bilateral matching and aspiration-level pricing.

Implements the market mechanism described by Farmer (2025) and adapted
for the UK by Baptista et al. (2016) and Carro et al. (2022).  Unlike
the goods or labour markets, the housing market does **not** clear to
equilibrium.  Buyers and sellers are matched bilaterally, prices
adjust sluggishly through aspiration-level adaptation, and persistent
imbalances between supply and demand are the norm.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from companies_house_abm.abm.markets.base import BaseMarket

if TYPE_CHECKING:
    from typing import Any

    from numpy.random import Generator

    from companies_house_abm.abm.agents.bank import Bank
    from companies_house_abm.abm.agents.household import Household
    from companies_house_abm.abm.assets.mortgage import Mortgage
    from companies_house_abm.abm.assets.property import Property
    from companies_house_abm.abm.config import HousingMarketConfig


class HousingMarket(BaseMarket):
    """UK housing market with bilateral matching.

    Each period the market:
    1. Updates asking prices for listed properties (aspiration-level
       adaptation).
    2. Collects potential buyers (households that want to buy).
    3. Matches buyers to listed properties via a search process.
    4. Processes transactions (mortgage origination, ownership transfer).
    5. Records aggregate statistics.
    """

    def __init__(
        self,
        config: HousingMarketConfig | None = None,
    ) -> None:
        self._config = config

        # Aggregate state
        self.average_price: float = 285_000.0
        self.transactions: int = 0
        self.listings: int = 0
        self.months_supply: float = 0.0
        self.price_to_income: float = 0.0
        self.house_price_inflation: float = 0.0
        self.total_mortgage_lending: float = 0.0
        self.foreclosures: int = 0
        self.homeownership_rate: float = 0.0

        self._previous_average_price: float = 285_000.0
        self._price_history: list[float] = []

        # References (set via set_agents)
        self._properties: list[Property] = []
        self._households: list[Household] = []
        self._banks: list[Bank] = []
        self._mortgages: list[Mortgage] = []
        self._rng: np.random.Generator = np.random.default_rng(42)
        self._period: int = 0

    def set_agents(
        self,
        properties: list[Property],
        households: list[Household],
        banks: list[Bank],
        mortgages: list[Mortgage],
        rng: np.random.Generator | None = None,
    ) -> None:
        """Register agent populations with the market."""
        self._properties = properties
        self._households = households
        self._banks = banks
        self._mortgages = mortgages
        if rng is not None:
            self._rng = rng

    def set_period(self, period: int) -> None:
        """Update the current period counter."""
        self._period = period

    # ------------------------------------------------------------------
    # Market clearing
    # ------------------------------------------------------------------

    def clear(self, rng: Generator | None = None) -> dict[str, Any]:  # noqa: ARG002
        """Execute one period of the housing market.

        Returns:
            Dictionary of aggregate market outcomes.
        """
        self._previous_average_price = self.average_price

        # Phase 1: Sellers update asking prices
        self._update_asking_prices()

        # Phase 2: Collect buyers
        buyers = [hh for hh in self._households if hh.wants_to_buy and hh.wealth > 0]

        # Phase 3: Collect listings
        listed = [p for p in self._properties if p.on_market]

        # Phase 4: Bilateral matching
        period_transactions = 0
        period_lending = 0.0

        if buyers and listed:
            period_transactions, period_lending = self._match_buyers_sellers(
                buyers, listed
            )

        # Phase 5: Update statistics
        self._update_statistics(period_transactions, period_lending)

        return self.get_state()

    def _update_asking_prices(self) -> None:
        """Aspiration-level adaptation: reduce prices of unsold listings."""
        reduction = self._config.price_reduction_rate if self._config else 0.10
        max_months = self._config.max_months_listed if self._config else 6

        for prop in self._properties:
            if not prop.on_market:
                continue
            if prop.months_listed >= max_months:
                prop.delist()
                # Owner may try again later
                owner = self._find_household(prop.owner_id)
                if owner:
                    owner.wants_to_sell = False
            else:
                prop.reduce_price(reduction)

    def _match_buyers_sellers(
        self,
        buyers: list[Household],
        listed: list[Property],
    ) -> tuple[int, float]:
        """Bilateral matching: buyers search, bid, transactions clear.

        Returns:
            (number of transactions, total mortgage lending)
        """
        search_intensity = self._config.search_intensity if self._config else 10
        transactions = 0
        lending = 0.0

        # Shuffle buyers for fairness
        buyer_indices = list(range(len(buyers)))
        self._rng.shuffle(buyer_indices)

        # Track which properties are sold this period
        sold_ids: set[str] = set()

        for idx in buyer_indices:
            buyer = buyers[idx]
            if not buyer.wants_to_buy:
                continue

            # Budget: wealth (deposit) + max mortgage
            annual_income = buyer.wage * 12.0 if buyer.employed else 0.0
            max_dti = 4.5
            max_mortgage = annual_income * max_dti
            max_budget = buyer.wealth + max_mortgage

            # Search: sample properties within budget
            affordable = [
                p
                for p in listed
                if p.property_id not in sold_ids
                and p.asking_price <= max_budget
                and p.on_market
            ]
            if not affordable:
                buyer.months_searching += 1
                continue

            n_visit = min(search_intensity, len(affordable))
            visited_indices = self._rng.choice(
                len(affordable), size=n_visit, replace=False
            )
            visited = [affordable[i] for i in visited_indices]

            # Pick best value (lowest asking price relative to quality)
            best = min(visited, key=lambda p: p.asking_price / max(p.quality, 0.01))

            # Attempt to transact
            result = self._attempt_transaction(buyer, best, annual_income)
            if result is not None:
                transactions += 1
                lending += result
                sold_ids.add(best.property_id)
                buyer.wants_to_buy = False
                buyer.months_searching = 0

        return transactions, lending

    def _attempt_transaction(
        self,
        buyer: Household,
        prop: Property,
        annual_income: float,
    ) -> float | None:
        """Try to complete a purchase.  Returns mortgage amount or None."""
        sale_price = prop.asking_price
        deposit = min(buyer.wealth, sale_price)
        loan_needed = sale_price - deposit

        if loan_needed > 0:
            # Find a bank willing to lend
            bank = self._find_lender(annual_income, deposit, sale_price)
            if bank is None:
                return None

            mortgage = bank.originate_mortgage(
                borrower_id=buyer.agent_id,
                property_id=prop.property_id,
                loan_amount=loan_needed,
                property_value=sale_price,
                annual_income=annual_income,
                period=self._period,
            )
            self._mortgages.append(mortgage)
            buyer.mortgage = mortgage
        else:
            loan_needed = 0.0

        # Transfer ownership
        old_owner_id = prop.owner_id
        prop.sell(
            new_owner_id=buyer.agent_id,
            sale_price=sale_price,
            period=self._period,
        )

        # Update buyer state
        buyer.wealth -= deposit
        buyer.tenure = "owner_occupier"
        buyer.property_id = prop.property_id
        buyer.rent = 0.0
        buyer.housing_wealth = sale_price - loan_needed

        # If there was a previous owner, update their state
        if old_owner_id:
            seller = self._find_household(old_owner_id)
            if seller:
                seller.wealth += sale_price
                if seller.property_id == prop.property_id:
                    seller.property_id = None
                    seller.tenure = "renter"
                    seller.housing_wealth = 0.0
                    # Clear seller's mortgage on this property
                    if (
                        seller.mortgage
                        and seller.mortgage.property_id == prop.property_id
                    ):
                        remaining = seller.mortgage.outstanding
                        seller.wealth -= remaining  # pay off mortgage
                        bank_id = seller.mortgage.lender_id
                        for b in self._banks:
                            if b.agent_id == bank_id:
                                b.record_mortgage_repayment(remaining)
                                break
                        self._mortgages = [
                            m
                            for m in self._mortgages
                            if m.mortgage_id != seller.mortgage.mortgage_id
                        ]
                        seller.mortgage = None

        return loan_needed

    def _find_lender(
        self,
        annual_income: float,
        deposit: float,
        property_value: float,
    ) -> Bank | None:
        """Find a bank willing to approve a mortgage."""
        # Try banks in random order
        bank_indices = list(range(len(self._banks)))
        self._rng.shuffle(bank_indices)
        for idx in bank_indices:
            bank = self._banks[idx]
            if bank.evaluate_mortgage(annual_income, deposit, property_value):
                return bank
        return None

    def _find_household(self, agent_id: str | None) -> Household | None:
        """Look up a household by agent_id."""
        if agent_id is None:
            return None
        for hh in self._households:
            if hh.agent_id == agent_id:
                return hh
        return None

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _update_statistics(self, transactions: int, lending: float) -> None:
        """Update aggregate market statistics after clearing."""
        self.transactions = transactions
        self.total_mortgage_lending = lending

        # Listings
        listed = [p for p in self._properties if p.on_market]
        self.listings = len(listed)

        # Average price from recent transactions
        if transactions > 0:
            recent_prices = [
                p.last_transaction_price
                for p in self._properties
                if p.last_transaction_period == self._period
            ]
            if recent_prices:
                self.average_price = sum(recent_prices) / len(recent_prices)

        # Price history for expectations
        self._price_history.append(self.average_price)

        # House price inflation (monthly)
        if self._previous_average_price > 0:
            self.house_price_inflation = (
                self.average_price / self._previous_average_price - 1.0
            )
        else:
            self.house_price_inflation = 0.0

        # Months of supply
        if transactions > 0:
            self.months_supply = self.listings / transactions
        else:
            self.months_supply = float(self.listings) if self.listings > 0 else 0.0

        # Homeownership rate
        if self._households:
            owners = sum(1 for hh in self._households if hh.tenure == "owner_occupier")
            self.homeownership_rate = owners / len(self._households)

        # Price to income
        incomes = [
            hh.wage * 12.0 for hh in self._households if hh.employed and hh.wage > 0
        ]
        if incomes:
            avg_income = sum(incomes) / len(incomes)
            if avg_income > 0:
                self.price_to_income = self.average_price / avg_income

    @property
    def price_history(self) -> list[float]:
        """Return the recorded price history."""
        return list(self._price_history)

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return the current state of the housing market."""
        return {
            "average_price": self.average_price,
            "transactions": self.transactions,
            "listings": self.listings,
            "months_supply": self.months_supply,
            "price_to_income": self.price_to_income,
            "house_price_inflation": self.house_price_inflation,
            "total_mortgage_lending": self.total_mortgage_lending,
            "foreclosures": self.foreclosures,
            "homeownership_rate": self.homeownership_rate,
        }
