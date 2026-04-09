"""Goods market for the ABM.

Firms post prices and quantities; households and government purchase
goods.  The market uses a simple matching procedure where buyers are
allocated across sellers proportionally to their relative price
competitiveness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.markets.base import BaseMarket

if TYPE_CHECKING:
    from typing import Any

    from numpy.random import Generator

    from companies_house_abm.abm.agents.firm import Firm
    from companies_house_abm.abm.agents.government import Government
    from companies_house_abm.abm.agents.household import Household
    from companies_house_abm.abm.config import GoodsMarketConfig


class GoodsMarket(BaseMarket):
    """The goods market.

    Attributes:
        total_sales: Aggregate sales volume (monetary) in the last round.
        average_price: Average price across firms after clearing.
        excess_demand: Aggregate excess demand (positive) or supply.
        inflation: Period-on-period price change.
    """

    def __init__(self, config: GoodsMarketConfig | None = None) -> None:
        self._config = config
        self.total_sales: float = 0.0
        self.average_price: float = 1.0
        self.excess_demand: float = 0.0
        self.inflation: float = 0.0
        # None until the first clear() so that the period-1 transition from the
        # initialised price index (1.0) to cost-based firm prices does not
        # register as hyperinflation and destabilise the Taylor rule.
        self._previous_price: float | None = None

        self._firms: list[Firm] = []
        self._households: list[Household] = []
        self._government: Government | None = None

    def set_agents(
        self,
        firms: list[Firm],
        households: list[Household],
        government: Government | None = None,
    ) -> None:
        """Register participating agents.

        Args:
            firms: Firm agents supplying goods.
            households: Household agents demanding goods.
            government: Government agent demanding goods.
        """
        self._firms = firms
        self._households = households
        self._government = government

    def clear(self, rng: Generator | None = None) -> dict[str, Any]:
        """Clear the goods market.

        1. Compute total demand from households and government.
        2. Compute total supply from firms' inventory.
        3. Allocate demand across firms based on price competitiveness.
        4. Update firm turnover / inventory and household consumption.

        Args:
            rng: Seeded numpy RNG forwarded to :meth:`~Firm.adapt_markup` for
                 reproducible stochastic markup adjustment.

        Returns:
            Aggregate market outcomes.
        """
        active_firms = [f for f in self._firms if not f.bankrupt]

        # ---- demand side ----
        total_demand = sum(h.consumption for h in self._households)
        if self._government:
            total_demand += self._government.expenditure

        # ---- supply side ----
        total_supply = sum(f.inventory * f.price for f in active_firms)

        self.excess_demand = total_demand - total_supply

        if not active_firms:
            self.total_sales = 0.0
            return self.get_state()

        # ---- matching: allocate demand in proportion to competitiveness ----
        max_price = max(f.price for f in active_firms)
        weights = [max(max_price - f.price + 1e-9, 1e-9) for f in active_firms]
        weight_sum = sum(weights)

        self.total_sales = 0.0
        for firm, w in zip(active_firms, weights, strict=True):
            share = w / weight_sum
            demand_for_firm = total_demand * share
            available = firm.inventory * firm.price
            actual_sales = min(demand_for_firm, available)

            quantity_sold = actual_sales / max(firm.price, 1e-9)
            firm.inventory = max(firm.inventory - quantity_sold, 0.0)
            firm.turnover = actual_sales
            self.total_sales += actual_sales

            # Firms adapt markup based on their excess demand signal
            firm_excess = (demand_for_firm - available) / max(available, 1e-9)
            firm.adapt_markup(firm_excess, rng=rng)

        # ---- average price and inflation ----
        # Use a sales-weighted (Paasche) price index so that firms with zero
        # sales get zero weight.  An arithmetic mean of all posted prices is
        # dominated by outliers (firms with near-zero output and therefore
        # extremely high unit costs) and is economically misleading.
        if active_firms:
            total_value = sum(f.turnover for f in active_firms if f.turnover > 0)
            total_qty = sum(
                f.turnover / f.price
                for f in active_firms
                if f.turnover > 0 and f.price > 0
            )
            new_price = (
                total_value / total_qty
                if total_qty > 0
                else self.average_price  # no sales this period — keep prior
            )

            if self._previous_price is not None and self._previous_price > 0:
                self.inflation = (
                    new_price - self._previous_price
                ) / self._previous_price
            # else: first call — no prior baseline, leave inflation = 0.0
            self._previous_price = new_price
            self.average_price = new_price

        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        """Return goods market statistics."""
        return {
            "total_sales": self.total_sales,
            "average_price": self.average_price,
            "excess_demand": self.excess_demand,
            "inflation": self.inflation,
        }
