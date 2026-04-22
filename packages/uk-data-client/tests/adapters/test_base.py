"""Unit tests for BaseAdapter default method implementations."""

from __future__ import annotations

from uk_data_client.adapters.boe import BoEAdapter
from uk_data_client.adapters.companies_house import CompaniesHouseAdapter
from uk_data_client.adapters.epc import EPCAdapter
from uk_data_client.adapters.hmrc import HMRCAdapter
from uk_data_client.adapters.land_registry import LandRegistryAdapter
from uk_data_client.adapters.ons import ONSAdapter


class TestBaseAdapterDefault:
    """available_series() returns [] by default for concrete subclasses."""

    def test_default_available_series_is_empty(self) -> None:
        # Use CompaniesHouseAdapter as a representative subclass that
        # does not override available_series().
        adapter = CompaniesHouseAdapter()
        assert adapter.available_series() == []

    def test_epc_available_series_is_empty(self) -> None:
        adapter = EPCAdapter()
        assert adapter.available_series() == []


class TestBaseAdapterEntityEventDefaults:
    """Adapters that do not override the methods return empty lists."""

    def test_ons_no_entity_types(self) -> None:
        assert ONSAdapter().available_entity_types() == []

    def test_boe_no_entity_types(self) -> None:
        assert BoEAdapter().available_entity_types() == []

    def test_hmrc_no_entity_types(self) -> None:
        assert HMRCAdapter().available_entity_types() == []

    def test_land_registry_no_entity_types(self) -> None:
        assert LandRegistryAdapter().available_entity_types() == []

    def test_ons_no_event_types(self) -> None:
        assert ONSAdapter().available_event_types() == []

    def test_boe_no_event_types(self) -> None:
        assert BoEAdapter().available_event_types() == []

    def test_hmrc_no_event_types(self) -> None:
        assert HMRCAdapter().available_event_types() == []
