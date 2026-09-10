"""LeveragedInvestor agent for the financial-crash module.

See ``docs/financial-market-crash.md`` §5.1, §5.3, §5.4 (M1, M3, M6).
Funding is represented as a single net-debt wedge: positive values are a
margin loan, negative values are surplus cash. This is algebraically
equivalent to tracking cash and margin debt separately for the purpose of
computing equity and leverage, and matches the aggregate-fund abstraction in
Thurner, Farmer & Geanakoplos (2012) — the reference implementation the
design doc cites for this core.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from mesa import Agent

if TYPE_CHECKING:
    from mesa import Model

    from companies_house_abm.abm.config import InvestorConfig


class LeveragedInvestor(Agent):
    """A leveraged investor holding a basket of risky assets on margin."""

    def __init__(
        self,
        model: Model,
        *,
        n_assets: int,
        basket: np.ndarray,
        target_leverage: float = 3.0,
        rebalancing_speed: float = 0.25,
        config: InvestorConfig | None = None,
    ) -> None:
        super().__init__(model)
        self.basket = basket
        self.target_leverage = target_leverage
        self.rebalancing_speed = rebalancing_speed
        self.holdings = np.zeros(n_assets)
        self.net_debt = 0.0
        self.defaulted = False
        self._config = config

    # ------------------------------------------------------------------
    # Balance-sheet identities (§5.3)
    # ------------------------------------------------------------------

    def gross_assets(self, prices: np.ndarray) -> float:
        """Market value of the current portfolio."""
        return float(np.dot(self.holdings, prices))

    def equity(self, prices: np.ndarray) -> float:
        """assets - liabilities."""
        return self.gross_assets(prices) - self.net_debt

    def leverage(self, prices: np.ndarray) -> float:
        """assets / equity."""
        eq = self.equity(prices)
        if eq <= 0:
            return math.inf
        return self.gross_assets(prices) / eq

    def collateral_value(self, prices: np.ndarray, haircuts: np.ndarray) -> float:
        """Sum of (1 - haircut) x holdings x price across assets."""
        return float(np.dot(self.holdings * prices, 1.0 - haircuts))

    def in_margin_call(
        self,
        prices: np.ndarray,
        haircuts: np.ndarray,
        margin_call_multiple: float,
    ) -> bool:
        """Whether the leverage or funding constraint is breached (M3)."""
        if self.defaulted:
            return False
        eq = self.equity(prices)
        if eq <= 0:
            return False
        over_leverage = (
            self.leverage(prices) > self.target_leverage * margin_call_multiple
        )
        under_collateralised = self.net_debt > self.collateral_value(prices, haircuts)
        return bool(over_leverage or under_collateralised)

    # ------------------------------------------------------------------
    # Order generation
    # ------------------------------------------------------------------

    def desired_orders(
        self,
        prices: np.ndarray,
        mispricing: np.ndarray,
        max_liquidation_rate: float,
        mispricing_sensitivity: float = 5.0,
    ) -> np.ndarray:
        """Voluntary rebalancing orders (in shares), paced by
        ``rebalancing_speed`` (M1).

        Demand has two components: the *level* of desired exposure scales
        with the average mispricing across the investor's basket (so a
        common-factor shock that moves every held asset's fundamental value
        together still generates real order flow), and the *allocation*
        within that exposure tilts toward the relatively cheaper assets in
        the basket via a softmax over each asset's mispricing.
        """
        if self.defaulted:
            return np.zeros_like(prices)
        eq = self.equity(prices)
        if eq <= 0:
            return np.zeros_like(prices)

        basket_mispricing = mispricing[self.basket]
        mean_mispricing = (
            float(basket_mispricing.mean()) if basket_mispricing.size else 0.0
        )
        effective_leverage = np.clip(
            self.target_leverage * (1.0 + mispricing_sensitivity * mean_mispricing),
            0.1,
            self.target_leverage * 3.0,
        )

        signal = np.where(self.basket, mispricing, 0.0)
        weights = _softmax(signal, self.basket)
        desired_value = weights * effective_leverage * eq
        desired_shares = np.divide(
            desired_value, prices, out=np.zeros_like(prices), where=prices > 0
        )
        trade = self.rebalancing_speed * (desired_shares - self.holdings)
        max_step = max_liquidation_rate * np.maximum(np.abs(self.holdings), 1.0)
        return np.clip(trade, -max_step, max_step)

    def forced_orders(
        self,
        prices: np.ndarray,
        haircuts: np.ndarray,
        max_liquidation_rate: float,
        margin_call_multiple: float,
    ) -> np.ndarray:
        """Sale required to restore the leverage/funding constraint (M3).

        Sells pro-rata across held positions back to ``target_leverage``,
        capped at ``max_liquidation_rate`` of each position per day.
        """
        if not self.in_margin_call(prices, haircuts, margin_call_multiple):
            return np.zeros_like(prices)

        eq = self.equity(prices)
        target_assets = self.target_leverage * eq
        current_assets = self.gross_assets(prices)
        sale_value = max(current_assets - target_assets, 0.0)
        if sale_value <= 0:
            return np.zeros_like(prices)

        held_value = self.holdings * prices
        total_held_value = held_value.sum()
        if total_held_value <= 0:
            return np.zeros_like(prices)
        sale_fraction = np.clip(sale_value / total_held_value, 0.0, 1.0)
        desired_sale_shares = sale_fraction * self.holdings
        max_step = max_liquidation_rate * np.abs(self.holdings)
        sale_shares = np.minimum(desired_sale_shares, max_step)
        return -sale_shares

    # ------------------------------------------------------------------
    # Settlement — mark-to-market
    # ------------------------------------------------------------------

    def apply_fill(self, filled: np.ndarray, fill_prices: np.ndarray) -> None:
        """Settle executed trades against the balance sheet."""
        self.holdings = self.holdings + filled
        self.net_debt += float(np.dot(filled, fill_prices))

    def get_state(self, prices: np.ndarray) -> dict[str, object]:
        """Return investor state for logging/analysis."""
        return {
            "unique_id": self.unique_id,
            "equity": self.equity(prices),
            "leverage": self.leverage(prices),
            "net_debt": self.net_debt,
            "defaulted": self.defaulted,
        }


def _softmax(signal: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Softmax over ``signal`` restricted to ``mask``; zero outside it."""
    if not mask.any():
        return np.zeros_like(signal)
    scaled = np.where(mask, signal, -np.inf) * 5.0
    scaled = scaled - np.max(scaled[mask])
    exp = np.where(mask, np.exp(scaled), 0.0)
    total = exp.sum()
    if total <= 0:
        return mask.astype(float) / mask.sum()
    return exp / total
