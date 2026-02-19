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
        self._previous_price: float = 1.0

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

    def clear(self) -> dict[str, Any]:
        """Clear the goods market.

        1. Compute total demand from households and government.
        2. Compute total supply from firms' inventory.
        3. Allocate demand across firms based on price competitiveness.
        4. Update firm turnover / inventory and household consumption.

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
            firm.adapt_markup(firm_excess)

        # ---- average price and inflation ----
        if active_firms:
            self._previous_price = self.average_price
            self.average_price = sum(f.price for f in active_firms) / len(active_firms)
            if self._previous_price > 0:
                self.inflation = (
                    self.average_price - self._previous_price
                ) / self._previous_price

        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        """Return goods market statistics."""
        return {
            "total_sales": self.total_sales,
            "average_price": self.average_price,
            "excess_demand": self.excess_demand,
            "inflation": self.inflation,
        }
