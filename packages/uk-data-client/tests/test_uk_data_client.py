"""Unit tests for UKDataClient, SourceInfo, and adapter available_series().

These tests are fully offline — no network requests are made.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from uk_data_client import EntityTypeInfo, EventTypeInfo, SourceInfo, UKDataClient
from uk_data_client.adapters.boe import BoEAdapter
from uk_data_client.adapters.companies_house import CompaniesHouseAdapter
from uk_data_client.adapters.epc import EPCAdapter
from uk_data_client.adapters.hmrc import HMRCAdapter
from uk_data_client.adapters.land_registry import LandRegistryAdapter
from uk_data_client.adapters.ons import ONSAdapter

# ---------------------------------------------------------------------------
# BaseAdapter default
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Per-adapter available_series()
# ---------------------------------------------------------------------------


class TestONSAdapterAvailableSeries:
    def test_returns_seven_series(self) -> None:
        adapter = ONSAdapter()
        series = adapter.available_series()
        assert len(series) == 7

    def test_contains_gdp_series(self) -> None:
        adapter = ONSAdapter()
        assert "ABMI" in adapter.available_series()

    def test_contains_all_expected_ids(self) -> None:
        adapter = ONSAdapter()
        series = adapter.available_series()
        expected = {"ABMI", "RPHQ", "NRJS", "MGSX", "KAB9", "HP7A", "D7RA"}
        assert expected == set(series)

    def test_no_duplicates(self) -> None:
        adapter = ONSAdapter()
        series = adapter.available_series()
        assert len(series) == len(set(series))


class TestBoEAdapterAvailableSeries:
    def test_returns_four_series(self) -> None:
        adapter = BoEAdapter()
        series = adapter.available_series()
        assert len(series) == 4

    def test_contains_bank_rate(self) -> None:
        adapter = BoEAdapter()
        assert "IUMABEDR" in adapter.available_series()

    def test_contains_all_expected_ids(self) -> None:
        adapter = BoEAdapter()
        series = adapter.available_series()
        expected = {"IUMABEDR", "IUMTLMV", "IUMZICQ", "LNMVNZL"}
        assert expected == set(series)


class TestHMRCAdapterAvailableSeries:
    def test_returns_three_series(self) -> None:
        adapter = HMRCAdapter()
        series = adapter.available_series()
        assert len(series) == 3

    def test_contains_all_expected_ids(self) -> None:
        adapter = HMRCAdapter()
        series = adapter.available_series()
        expected = {
            "corporation_tax_2024",
            "income_tax_basic_2024",
            "vat_standard_2024",
        }
        assert expected == set(series)


class TestLandRegistryAdapterAvailableSeries:
    def test_returns_two_series(self) -> None:
        adapter = LandRegistryAdapter()
        series = adapter.available_series()
        assert len(series) == 2

    def test_contains_expected_ids(self) -> None:
        adapter = LandRegistryAdapter()
        series = adapter.available_series()
        assert set(series) == {"uk_hpi_average", "uk_hpi_full"}


# ---------------------------------------------------------------------------
# Client list_sources helper
# ---------------------------------------------------------------------------


class TestUKDataClientListSources:
    def test_returns_list_of_source_info(self) -> None:
        client = UKDataClient()
        sources = client.list_sources()
        assert isinstance(sources, list)
        assert all(isinstance(s, SourceInfo) for s in sources)

    def test_all_registered_adapters_present(self) -> None:
        client = UKDataClient()
        names = {s.name for s in client.list_sources()}
        expected = {"ons", "boe", "hmrc", "land_registry", "companies_house", "epc"}
        assert names == expected

    def test_source_info_has_correct_structure(self) -> None:
        client = UKDataClient()
        for src in client.list_sources():
            assert isinstance(src.name, str)
            assert isinstance(src.series, list)
            assert all(isinstance(sid, str) for sid in src.series)

    def test_ons_source_has_series(self) -> None:
        client = UKDataClient()
        ons = next(s for s in client.list_sources() if s.name == "ons")
        assert len(ons.series) > 0
        assert "ABMI" in ons.series

    def test_boe_source_has_series(self) -> None:
        client = UKDataClient()
        boe = next(s for s in client.list_sources() if s.name == "boe")
        assert "IUMABEDR" in boe.series

    def test_hmrc_source_has_series(self) -> None:
        client = UKDataClient()
        hmrc = next(s for s in client.list_sources() if s.name == "hmrc")
        assert "corporation_tax_2024" in hmrc.series

    def test_land_registry_source_has_series(self) -> None:
        client = UKDataClient()
        lr = next(s for s in client.list_sources() if s.name == "land_registry")
        assert "uk_hpi_average" in lr.series

    def test_event_only_adapters_have_no_series(self) -> None:
        """companies_house and epc are event-only; their series list is empty."""
        client = UKDataClient()
        sources_by_name = {s.name: s for s in client.list_sources()}
        assert sources_by_name["companies_house"].series == []
        assert sources_by_name["epc"].series == []

    def test_list_sources_consistent_with_adapters_dict(self) -> None:
        """list_sources() must exactly mirror the adapters registered in __init__."""
        client = UKDataClient()
        source_names = [s.name for s in client.list_sources()]
        assert source_names == list(client.adapters.keys())

    def test_source_info_repr_contains_name(self) -> None:
        src = SourceInfo(name="test_source", series=["A", "B"])
        assert "test_source" in repr(src)


# ---------------------------------------------------------------------------
# UKDataClient.list_sources() — invalid concept / source guard
# ---------------------------------------------------------------------------


class TestUKDataClientGetSeries:
    def test_unknown_concept_raises_value_error(self) -> None:
        client = UKDataClient()
        with pytest.raises(ValueError, match="Unknown concept"):
            client.get_series("nonexistent_concept_xyz")

    def test_known_concept_wrong_source_raises(self) -> None:
        client = UKDataClient()
        # gdp is available via ons, not hmrc
        with pytest.raises(ValueError):
            client.get_series("gdp", source="hmrc")


# ---------------------------------------------------------------------------
# HMRC fetch_series — offline (static data, no network)
# ---------------------------------------------------------------------------


class TestHMRCAdapterFetchSeries:
    def test_corporation_tax_value(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("corporation_tax_2024")
        assert ts.source == "hmrc"
        assert ts.latest_value is not None
        assert 0 < ts.latest_value <= 1  # fraction

    def test_income_tax_basic_value(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("income_tax_basic_2024")
        assert ts.source == "hmrc"
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)

    def test_vat_standard_value(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("vat_standard_2024")
        assert ts.source == "hmrc"
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)

    def test_unsupported_series_raises(self) -> None:
        adapter = HMRCAdapter()
        with pytest.raises(ValueError, match="Unsupported HMRC series"):
            adapter.fetch_series("unknown_hmrc_series")

    def test_all_advertised_series_fetchable(self) -> None:
        """Every series in available_series() must be fetchable without error."""
        adapter = HMRCAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None


# ---------------------------------------------------------------------------
# BoE fetch_series — uses fallback values; network may be unavailable
# ---------------------------------------------------------------------------


class TestBoEAdapterFetchSeries:
    def test_bank_rate_returns_timeseries(self) -> None:
        adapter = BoEAdapter()
        ts = adapter.fetch_series("IUMABEDR")
        assert ts.source == "boe"
        assert ts.source_series_id == "IUMABEDR"
        # BoE IADB may be unreachable (returns 403); latest_value may be None

    def test_household_lending_rate_returns_timeseries(self) -> None:
        adapter = BoEAdapter()
        ts = adapter.fetch_series("IUMTLMV")
        assert ts.source == "boe"
        assert ts.latest_value is not None

    def test_business_lending_rate_returns_timeseries(self) -> None:
        adapter = BoEAdapter()
        ts = adapter.fetch_series("IUMZICQ")
        assert ts.source == "boe"
        assert ts.latest_value is not None

    def test_capital_ratio_returns_timeseries(self) -> None:
        adapter = BoEAdapter()
        ts = adapter.fetch_series("LNMVNZL")
        assert ts.source == "boe"
        assert ts.latest_value is not None

    def test_unsupported_series_raises(self) -> None:
        adapter = BoEAdapter()
        with pytest.raises(ValueError, match="Unsupported Bank of England series"):
            adapter.fetch_series("NOTAREAL")

    def test_all_advertised_series_fetchable(self) -> None:
        """Every series in available_series() must be fetchable without error."""
        adapter = BoEAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None


# ---------------------------------------------------------------------------
# ONS fetch_series — mocked HTTP so tests stay offline
# ---------------------------------------------------------------------------


class TestONSAdapterFetchSeriesOffline:
    """Mock the HTTP layer so ONS tests never hit the network."""

    def _mock_observations(self) -> list[dict[str, object]]:
        return [{"date": "2024 Q1", "value": "100.0"}]

    def _patch_ons_http(self) -> patch:  # type: ignore[type-arg]
        """Return a patch target for the ONS internal HTTP fetch."""
        return patch(
            "uk_data_client.adapters.ons._fetch_timeseries",
            return_value=self._mock_observations(),
        )

    def test_gdp_series_returns_timeseries(self) -> None:
        with (
            patch(
                "uk_data_client.adapters.ons.fetch_gdp",
                return_value=self._mock_observations(),
            ),
        ):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("ABMI")
            assert ts.source == "ons"
            assert ts.source_series_id == "ABMI"

    def test_unemployment_series_returns_timeseries(self) -> None:
        with self._patch_ons_http():
            adapter = ONSAdapter()
            ts = adapter.fetch_series("MGSX")
            assert ts.source == "ons"

    def test_affordability_returns_point_series(self) -> None:
        with patch(
            "uk_data_client.adapters.ons.fetch_affordability_ratio",
            return_value=8.5,
        ):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("HP7A")
            assert ts.source == "ons"
            assert ts.latest_value == pytest.approx(8.5)

    def test_rental_index_returns_point_series(self) -> None:
        with patch(
            "uk_data_client.adapters.ons.fetch_rental_growth",
            return_value=0.03,
        ):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("D7RA")
            assert ts.source == "ons"
            assert ts.latest_value == pytest.approx(0.03)

    def test_unsupported_series_raises(self) -> None:
        adapter = ONSAdapter()
        with pytest.raises(ValueError, match="Unsupported ONS series"):
            adapter.fetch_series("NOTREAL_SERIES_ID")


# ---------------------------------------------------------------------------
# LandRegistry fetch_series — mocked to stay offline
# ---------------------------------------------------------------------------


class TestLandRegistryAdapterFetchSeriesOffline:
    def test_uk_hpi_average_returns_timeseries(self) -> None:
        with patch(
            "uk_data_client.adapters.land_registry.fetch_uk_average_price",
            return_value=285_000.0,
        ):
            adapter = LandRegistryAdapter()
            ts = adapter.fetch_series("uk_hpi_average")
            assert ts.source == "land_registry"
            assert ts.latest_value == pytest.approx(285_000.0)

    def test_uk_hpi_full_requires_filepath(self) -> None:
        adapter = LandRegistryAdapter()
        with pytest.raises(ValueError, match="filepath"):
            adapter.fetch_series("uk_hpi_full")

    def test_unsupported_series_raises(self) -> None:
        adapter = LandRegistryAdapter()
        with pytest.raises(ValueError, match="Unsupported Land Registry series"):
            adapter.fetch_series("invalid_lr_series")


# ---------------------------------------------------------------------------
# CompaniesHouse fetch_series — always raises
# ---------------------------------------------------------------------------


class TestCompaniesHouseAdapterFetchSeries:
    def test_fetch_series_always_raises(self) -> None:
        adapter = CompaniesHouseAdapter()
        with pytest.raises(ValueError, match="Unsupported Companies House series"):
            adapter.fetch_series("any_series")

    def test_available_series_is_empty(self) -> None:
        adapter = CompaniesHouseAdapter()
        assert adapter.available_series() == []


# ---------------------------------------------------------------------------
# EPCAdapter fetch_series — always raises NotImplementedError
# ---------------------------------------------------------------------------


class TestEPCAdapterFetchSeries:
    def test_fetch_series_raises_not_implemented(self) -> None:
        adapter = EPCAdapter()
        with pytest.raises(NotImplementedError):
            adapter.fetch_series("any_series")

    def test_available_series_is_empty(self) -> None:
        adapter = EPCAdapter()
        assert adapter.available_series() == []


# ---------------------------------------------------------------------------
# Per-adapter available_entity_types() and available_event_types()
# ---------------------------------------------------------------------------


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


class TestCompaniesHouseAdapterEntityEventTypes:
    def test_entity_types_contains_company(self) -> None:
        assert "company" in CompaniesHouseAdapter().available_entity_types()

    def test_event_types_contains_filing(self) -> None:
        assert "filing" in CompaniesHouseAdapter().available_event_types()

    def test_entity_types_is_list_of_strings(self) -> None:
        types = CompaniesHouseAdapter().available_entity_types()
        assert all(isinstance(t, str) for t in types)

    def test_event_types_is_list_of_strings(self) -> None:
        types = CompaniesHouseAdapter().available_event_types()
        assert all(isinstance(t, str) for t in types)


class TestLandRegistryAdapterEventTypes:
    def test_event_types_contains_property_transaction(self) -> None:
        assert "property_transaction" in LandRegistryAdapter().available_event_types()

    def test_no_entity_types(self) -> None:
        assert LandRegistryAdapter().available_entity_types() == []


class TestEPCAdapterEventTypes:
    def test_event_types_contains_epc_lodgement(self) -> None:
        assert "epc_lodgement" in EPCAdapter().available_event_types()

    def test_no_entity_types(self) -> None:
        assert EPCAdapter().available_entity_types() == []


# ---------------------------------------------------------------------------
# Client list_entities helper
# ---------------------------------------------------------------------------


class TestUKDataClientListEntities:
    def test_returns_list_of_entity_type_info(self) -> None:
        client = UKDataClient()
        entities = client.list_entities()
        assert isinstance(entities, list)
        assert all(isinstance(e, EntityTypeInfo) for e in entities)

    def test_only_companies_house_has_entities(self) -> None:
        """Of the six registered adapters only companies_house exposes entities."""
        client = UKDataClient()
        sources = {e.source for e in client.list_entities()}
        assert sources == {"companies_house"}

    def test_companies_house_entity_types(self) -> None:
        client = UKDataClient()
        ch = next(e for e in client.list_entities() if e.source == "companies_house")
        assert "company" in ch.entity_types

    def test_entity_type_info_structure(self) -> None:
        client = UKDataClient()
        for info in client.list_entities():
            assert isinstance(info.source, str) and info.source
            assert isinstance(info.entity_types, list)
            assert all(isinstance(t, str) for t in info.entity_types)
            assert len(info.entity_types) > 0

    def test_entity_type_info_repr_contains_source(self) -> None:
        info = EntityTypeInfo(source="companies_house", entity_types=["company"])
        assert "companies_house" in repr(info)

    def test_no_entity_type_info_for_series_only_adapters(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_entities()}
        for series_only in ("ons", "boe", "hmrc"):
            assert series_only not in sources


# ---------------------------------------------------------------------------
# Client list_events helper
# ---------------------------------------------------------------------------


class TestUKDataClientListEvents:
    def test_returns_list_of_event_type_info(self) -> None:
        client = UKDataClient()
        events = client.list_events()
        assert isinstance(events, list)
        assert all(isinstance(e, EventTypeInfo) for e in events)

    def test_expected_sources_present(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_events()}
        assert {"companies_house", "land_registry", "epc"} == sources

    def test_companies_house_event_types(self) -> None:
        client = UKDataClient()
        ch = next(e for e in client.list_events() if e.source == "companies_house")
        assert "filing" in ch.event_types

    def test_land_registry_event_types(self) -> None:
        client = UKDataClient()
        lr = next(e for e in client.list_events() if e.source == "land_registry")
        assert "property_transaction" in lr.event_types

    def test_epc_event_types(self) -> None:
        client = UKDataClient()
        epc = next(e for e in client.list_events() if e.source == "epc")
        assert "epc_lodgement" in epc.event_types

    def test_event_type_info_structure(self) -> None:
        client = UKDataClient()
        for info in client.list_events():
            assert isinstance(info.source, str) and info.source
            assert isinstance(info.event_types, list)
            assert all(isinstance(t, str) for t in info.event_types)
            assert len(info.event_types) > 0

    def test_event_type_info_repr_contains_source(self) -> None:
        info = EventTypeInfo(
            source="land_registry", event_types=["property_transaction"]
        )
        assert "land_registry" in repr(info)

    def test_no_event_type_info_for_series_only_adapters(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_events()}
        for series_only in ("ons", "boe", "hmrc"):
            assert series_only not in sources
