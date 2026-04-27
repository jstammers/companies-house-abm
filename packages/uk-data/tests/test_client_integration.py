"""Integration tests for UKDataClient — concept resolution, list_entities, list_events.

These tests make REAL network requests.  They are marked ``pytest.mark.integration``
and excluded from the default test run; pass ``-m integration`` to execute them::

    uv run pytest -m integration \
        packages/uk-data-client/tests/test_client_integration.py -v
"""

from __future__ import annotations

import urllib.request

import pytest

from uk_data import UKDataClient

pytestmark = pytest.mark.integration

_ONS_URL = "https://api.ons.gov.uk/v1"
_BOE_URL = "https://www.bankofengland.co.uk"
_LAND_REGISTRY_URL = "https://landregistry.data.gov.uk"
_CH_API_URL = "https://api.companieshouse.gov.uk"


def _skip_if_cannot_reach(url: str) -> None:
    """Skip the calling test if *url* is not reachable within 5 s."""
    try:
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pytest.skip(f"Network unavailable or {url} unreachable")


class TestUKDataClientConceptResolutionIntegration:
    """Verify that canonical concept strings resolve and fetch live data."""

    def test_list_sources_returns_non_empty(self) -> None:
        client = UKDataClient()
        sources = client.list_sources()
        assert len(sources) > 0

    def test_list_sources_all_series_ids_are_strings(self) -> None:
        client = UKDataClient()
        for src in client.list_sources():
            for sid in src.series:
                assert isinstance(sid, str) and len(sid) > 0

    def test_get_series_gdp_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        client = UKDataClient()
        ts = client.get_series("gdp")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_get_series_bank_rate_live(self) -> None:
        _skip_if_cannot_reach(_BOE_URL)
        client = UKDataClient()
        ts = client.get_series("bank_rate")
        assert ts.source == "boe"
        assert ts.latest_value is not None

    def test_get_series_corp_tax_live(self) -> None:
        """HMRC data is static; always succeeds."""
        client = UKDataClient()
        ts = client.get_series("corp_tax_rate")
        assert ts.source == "hmrc"
        assert ts.latest_value == pytest.approx(0.25, abs=0.01)

    def test_get_series_house_price_live(self) -> None:
        _skip_if_cannot_reach(_LAND_REGISTRY_URL)
        client = UKDataClient()
        ts = client.get_series("house_price_uk")
        assert ts.source == "land_registry"
        assert ts.latest_value is not None

    def test_all_concepts_resolvable(self) -> None:
        """Every concept in CONCEPT_REGISTRY must be resolvable without error."""
        from uk_data.registry import CONCEPT_REGISTRY

        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        client = UKDataClient()
        for concept in CONCEPT_REGISTRY:
            ts = client.get_series(concept)
            assert ts is not None, f"Concept {concept!r} returned None"

    def test_get_series_accepts_window_and_limit_together(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        client = UKDataClient()
        ts = client.get_series(
            "gdp",
            start_date="2019-01-01",
            end_date="2025-12-31",
            limit=2,
        )
        assert ts.source == "ons"
        assert len(ts.values) <= 2


class TestUKDataClientListEntitiesIntegration:
    """Verify that list_entities() reports the correct structure at runtime."""

    def test_list_entities_non_empty(self) -> None:
        client = UKDataClient()
        entities = client.list_entities()
        assert len(entities) > 0

    def test_companies_house_in_list_entities(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_entities()}
        assert "companies_house" in sources

    def test_companies_house_advertises_company_type(self) -> None:
        client = UKDataClient()
        ch = next(e for e in client.list_entities() if e.source == "companies_house")
        assert "company" in ch.entity_types

    def test_series_only_adapters_absent_from_list_entities(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_entities()}
        for series_only in ("ons", "boe", "hmrc"):
            assert series_only not in sources


class TestUKDataClientListEventsIntegration:
    """Verify that list_events() reports the correct structure at runtime."""

    def test_list_events_non_empty(self) -> None:
        client = UKDataClient()
        events = client.list_events()
        assert len(events) > 0

    def test_expected_event_sources_present(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_events()}
        assert {"companies_house", "land_registry", "epc"} == sources

    def test_companies_house_advertises_filing(self) -> None:
        client = UKDataClient()
        ch = next(e for e in client.list_events() if e.source == "companies_house")
        assert "filing" in ch.event_types

    def test_land_registry_advertises_property_transaction(self) -> None:
        client = UKDataClient()
        lr = next(e for e in client.list_events() if e.source == "land_registry")
        assert "property_transaction" in lr.event_types

    def test_epc_advertises_epc_lodgement(self) -> None:
        client = UKDataClient()
        epc = next(e for e in client.list_events() if e.source == "epc")
        assert "epc_lodgement" in epc.event_types

    def test_series_only_adapters_absent_from_list_events(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_events()}
        for series_only in ("ons", "boe", "hmrc"):
            assert series_only not in sources
