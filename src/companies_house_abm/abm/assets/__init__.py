"""Non-agent asset classes for the ABM (properties, mortgages)."""

from __future__ import annotations

from companies_house_abm.abm.assets.mortgage import Mortgage
from companies_house_abm.abm.assets.property import Property

__all__ = [
    "Mortgage",
    "Property",
]
