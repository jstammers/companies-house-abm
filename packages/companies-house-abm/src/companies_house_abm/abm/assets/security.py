"""Risky asset (security) for the financial-crash module.

See ``docs/financial-market-crash.md`` §5.2.  The traded price only moves in
response to order flow via the market's price-impact function (M4); the
fundamental value follows an independent exogenous news process.  The gap
between the two is what gives leveraged investors a reason to trade.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskyAsset:
    """A tradable security with a fundamental value distinct from its price."""

    asset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_class: str = "equity"
    price: float = 100.0
    fundamental_value: float = 100.0
    shares_outstanding: float = 10_000_000.0
    daily_volume: float = 500_000.0  # average daily volume (ADV)
    realised_volatility: float = 0.01  # EWMA daily volatility
    haircut: float = 0.15
    previous_price: float = 100.0
    transient_impact: float = 0.0  # decaying price-level offset (M4)

    @property
    def daily_return(self) -> float:
        """Return over the most recent :meth:`roll`."""
        if self.previous_price <= 0:
            return 0.0
        return self.price / self.previous_price - 1.0

    @property
    def mispricing(self) -> float:
        """Fractional gap between fundamental value and price; > 0 = cheap."""
        if self.price <= 0:
            return 0.0
        return (self.fundamental_value - self.price) / self.price

    def roll(self) -> None:
        """Advance the return-calculation anchor to the current price."""
        self.previous_price = self.price

    def update_volatility(self, ewma_lambda: float = 0.94, floor: float = 0.0) -> None:
        """EWMA update of realised volatility from the latest return (M2).

        ``floor`` prevents a self-reinforcing quiet spiral: since price
        impact scales with realised volatility (M4), a realised volatility
        that is allowed to decay to exactly zero would permanently mute all
        further order flow's effect on price, freezing the market.
        """
        r = self.daily_return
        variance = ewma_lambda * self.realised_volatility**2 + (1 - ewma_lambda) * r**2
        self.realised_volatility = max(math.sqrt(max(variance, 0.0)), floor)

    def get_state(self) -> dict[str, Any]:
        """Return asset state for logging/analysis."""
        return {
            "asset_id": self.asset_id,
            "asset_class": self.asset_class,
            "price": self.price,
            "fundamental_value": self.fundamental_value,
            "realised_volatility": self.realised_volatility,
            "haircut": self.haircut,
            "daily_return": self.daily_return,
            "mispricing": self.mispricing,
        }
