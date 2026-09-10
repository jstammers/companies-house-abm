"""Dealer / market-maker agent for the financial-crash module (M5).

Supplies liquidity up to a capital-limited inventory capacity; losses on
inventory reduce capital, and capital slowly replenishes (slow-moving
capital, Duffie 2010; Baranova, Douglas & Silvestri 2019).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from mesa import Agent

if TYPE_CHECKING:
    from mesa import Model


class Dealer(Agent):
    """A capital-constrained liquidity supplier."""

    def __init__(
        self,
        model: Model,
        *,
        n_assets: int,
        capital: float,
        target_capital: float,
        inventory_limit: np.ndarray,
        replenishment_rate: float = 0.05,
    ) -> None:
        super().__init__(model)
        self.capital = capital
        self.target_capital = target_capital
        self.inventory = np.zeros(n_assets)
        self.inventory_limit = inventory_limit
        self.replenishment_rate = replenishment_rate
        self._previous_prices: np.ndarray | None = None

    def capacity(self) -> np.ndarray:
        """Absorption capacity (shares) per asset, scaled by capital headroom
        relative to its target level — the capital constraint in M5."""
        if self.target_capital <= 0:
            return np.zeros_like(self.inventory_limit)
        capital_scale = np.clip(self.capital / self.target_capital, 0.0, 1.0)
        return capital_scale * self.inventory_limit

    def absorb(self, net_flow: np.ndarray) -> np.ndarray:
        """Absorb part of net order flow into inventory, capped by capacity."""
        cap = self.capacity()
        headroom_buy = np.maximum(cap - self.inventory, 0.0)
        headroom_sell = np.maximum(cap + self.inventory, 0.0)
        absorbed = np.where(
            net_flow >= 0,
            np.minimum(net_flow, headroom_buy),
            -np.minimum(-net_flow, headroom_sell),
        )
        self.inventory = self.inventory + absorbed
        return absorbed

    def mark_to_market(self, prices: np.ndarray) -> None:
        """Revalue inventory and update capital (M6)."""
        if self._previous_prices is not None:
            pnl = float(np.dot(self.inventory, prices - self._previous_prices))
            self.capital += pnl
        self._previous_prices = prices.copy()
        self.capital = max(self.capital, 0.0)

    def replenish(self) -> None:
        """Slow-moving capital: drift back toward the target level."""
        self.capital += self.replenishment_rate * (self.target_capital - self.capital)

    def get_state(self) -> dict[str, object]:
        """Return dealer state for logging/analysis."""
        return {
            "unique_id": self.unique_id,
            "capital": self.capital,
            "inventory_value": float(np.abs(self.inventory).sum()),
        }
