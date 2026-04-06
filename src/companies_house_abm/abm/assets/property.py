"""Property asset class for the housing market."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Property:
    """A housing unit that can be owned, rented, or traded.

    Properties are passive assets — they do not make decisions and have no
    ``step()`` method.  Their state is updated by the :class:`HousingMarket`
    during the market clearing phase.

    Seller pricing follows *aspiration-level adaptation* (Farmer 2025): the
    asking price starts above recent comparable sales and is gradually reduced
    each period the property remains unsold.
    """

    # Identity
    property_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    region: str = "south_east"
    property_type: str = "terraced"  # detached, semi_detached, terraced, flat
    quality: float = 0.5  # abstract index [0, 1]

    # Valuation
    market_value: float = 285_000.0  # current estimated value (GBP)
    last_transaction_price: float = 285_000.0
    last_transaction_period: int = 0

    # Ownership
    owner_id: str | None = None  # household agent_id, None if vacant
    on_market: bool = False
    asking_price: float = 0.0
    months_listed: int = 0

    # Rental
    rental_value: float = 1_000.0  # monthly rent (GBP)
    is_rented: bool = False
    tenant_id: str | None = None

    def list_for_sale(self, initial_markup: float = 0.05) -> None:
        """Put the property on the market at a markup above market value."""
        self.on_market = True
        self.asking_price = self.market_value * (1.0 + initial_markup)
        self.months_listed = 0

    def reduce_price(self, reduction_rate: float = 0.10) -> None:
        """Reduce the asking price after an unsold period."""
        self.asking_price *= 1.0 - reduction_rate
        self.months_listed += 1

    def delist(self) -> None:
        """Remove the property from the market."""
        self.on_market = False
        self.asking_price = 0.0
        self.months_listed = 0

    def sell(self, new_owner_id: str, sale_price: float, period: int) -> None:
        """Record a sale transaction."""
        self.owner_id = new_owner_id
        self.last_transaction_price = sale_price
        self.last_transaction_period = period
        self.market_value = sale_price
        self.on_market = False
        self.asking_price = 0.0
        self.months_listed = 0
        self.is_rented = False
        self.tenant_id = None

    def get_state(self) -> dict[str, object]:
        """Return property state for logging/analysis."""
        return {
            "property_id": self.property_id,
            "region": self.region,
            "property_type": self.property_type,
            "quality": self.quality,
            "market_value": self.market_value,
            "on_market": self.on_market,
            "asking_price": self.asking_price,
            "months_listed": self.months_listed,
            "is_rented": self.is_rented,
            "owner_id": self.owner_id,
            "tenant_id": self.tenant_id,
        }
