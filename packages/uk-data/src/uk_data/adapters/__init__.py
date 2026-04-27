"""Canonical source adapters.

The adapter surface for external consumers is intentionally narrow: the
:class:`AdapterProtocol` structural Protocol and the six concrete adapter
classes.  Source-specific helper functions (e.g. ``fetch_bank_rate``,
``compute_income_tax``) remain importable from their submodules
(``uk_data.adapters.boe``, ``uk_data.adapters.hmrc``, ...) but are no
longer re-exported here — they are implementation details of the ABM
calibration layer, not part of the canonical client API.
"""

# HistoricalAdapter relocated to uk_data.workflows.historical (not a low-level adapter)

from uk_data.adapters.base import AdapterProtocol, BaseAdapter
from uk_data.adapters.boe import BoEAdapter
from uk_data.adapters.companies_house import CompaniesHouseAdapter
from uk_data.adapters.epc import EPCAdapter
from uk_data.adapters.hmrc import HMRCAdapter
from uk_data.adapters.land_registry import LandRegistryAdapter
from uk_data.adapters.ons import ONSAdapter

__all__ = [
    "AdapterProtocol",
    "BaseAdapter",
    "BoEAdapter",
    "CompaniesHouseAdapter",
    "EPCAdapter",
    "HMRCAdapter",
    "LandRegistryAdapter",
    "ONSAdapter",
]
