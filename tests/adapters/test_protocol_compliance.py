"""Protocol compliance tests for all registered low-level source adapters.

Verifies that each source adapter satisfies ``AdapterProtocol`` via
structural (duck-typed) conformance — no inheritance required.

``HistoricalAdapter`` is intentionally excluded: it is a high-level
orchestration class (``companies_house_abm.data_sources.historical``), not a
low-level source adapter.
"""

from __future__ import annotations

import pytest

from uk_data.adapters.base import AdapterProtocol
from uk_data.adapters.boe import BoEAdapter
from uk_data.adapters.companies_house import CompaniesHouseAdapter
from uk_data.adapters.epc import EPCAdapter
from uk_data.adapters.hmrc import HMRCAdapter
from uk_data.adapters.land_registry import LandRegistryAdapter
from uk_data.adapters.ons import ONSAdapter


class TestAdapterProtocolCompliance:
    """Assert all 6 source adapters are runtime-conformant with AdapterProtocol."""

    def test_ons_adapter_satisfies_protocol(self) -> None:
        assert isinstance(ONSAdapter(), AdapterProtocol)

    def test_boe_adapter_satisfies_protocol(self) -> None:
        assert isinstance(BoEAdapter(), AdapterProtocol)

    def test_hmrc_adapter_satisfies_protocol(self) -> None:
        assert isinstance(HMRCAdapter(), AdapterProtocol)

    def test_epc_adapter_satisfies_protocol(self) -> None:
        assert isinstance(EPCAdapter(), AdapterProtocol)

    def test_companies_house_adapter_satisfies_protocol(self) -> None:
        assert isinstance(CompaniesHouseAdapter(), AdapterProtocol)

    def test_land_registry_adapter_satisfies_protocol(self) -> None:
        assert isinstance(LandRegistryAdapter(), AdapterProtocol)


class TestAdapterProtocolPublicExport:
    """AdapterProtocol must be importable from the public adapter surface."""

    def test_adapter_protocol_exported_from_adapters_init(self) -> None:
        from uk_data.adapters import AdapterProtocol as AP

        assert AP is AdapterProtocol

    def test_adapter_protocol_is_runtime_checkable(self) -> None:
        # If not @runtime_checkable, isinstance raises TypeError
        try:
            result = isinstance(object(), AdapterProtocol)
            # result is False — that's fine, just shouldn't raise
            assert result is False or result is True
        except TypeError as exc:
            pytest.fail(f"AdapterProtocol is not @runtime_checkable: {exc}")
