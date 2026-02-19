"""Base market class for the ABM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class BaseMarket(ABC):
    """Abstract base class for all markets.

    Markets match buyers and sellers, determine prices and quantities,
    and update agent states accordingly.
    """

    @abstractmethod
    def clear(self) -> dict[str, Any]:
        """Execute the market clearing mechanism.

        Returns:
            Dictionary of aggregate market outcomes (e.g. total volume,
            average price, excess demand).
        """

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return the current state of the market.

        Returns:
            Dictionary of market statistics for logging/analysis.
        """
