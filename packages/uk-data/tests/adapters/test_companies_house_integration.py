"""Integration tests for CompaniesHouseAdapter — makes real network requests.

Run with::

    uv run pytest -m integration \
        packages/uk-data-client/tests/adapters/test_companies_house_integration.py
"""

from __future__ import annotations

import urllib.request

import pytest

from uk_data import UKDataClient

pytestmark = pytest.mark.integration

_CH_API_URL = "https://api.companieshouse.gov.uk"


def _skip_if_cannot_reach(url: str) -> None:
    try:
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pytest.skip(f"Network unavailable or {url} unreachable")


class TestCompaniesHouseAdapterEntityIntegration:
    """Verify fetch_entity() returns a well-formed Entity for a known company."""

    def test_fetch_entity_returns_company(self) -> None:
        _skip_if_cannot_reach(_CH_API_URL)
        from uk_data.adapters.companies_house import CompaniesHouseAdapter
        from uk_data.models import Entity

        adapter = CompaniesHouseAdapter()
        entity = adapter.fetch_entity("BBC")
        assert isinstance(entity, Entity)
        assert entity.entity_type == "company"
        assert entity.source == "companies_house"
        assert entity.source_id is not None
        assert entity.name

    def test_get_entity_via_client(self) -> None:
        _skip_if_cannot_reach(_CH_API_URL)
        from uk_data.models import Entity

        client = UKDataClient()
        entity = client.get_entity("BBC")
        assert isinstance(entity, Entity)
        assert entity.entity_type == "company"

    def test_fetch_entity_attributes_present(self) -> None:
        _skip_if_cannot_reach(_CH_API_URL)
        from uk_data.adapters.companies_house import CompaniesHouseAdapter

        adapter = CompaniesHouseAdapter()
        entity = adapter.fetch_entity("BBC")
        assert "company_status" in entity.attributes

    def test_fetch_entity_not_found_raises(self) -> None:
        _skip_if_cannot_reach(_CH_API_URL)
        from uk_data.adapters.companies_house import CompaniesHouseAdapter

        adapter = CompaniesHouseAdapter()
        with pytest.raises(ValueError, match="No Companies House entity found"):
            adapter.fetch_entity("XYZNOTAREALCOMPANYNAME99999ZZZ")


class TestCompaniesHouseAdapterEventsIntegration:
    """Verify fetch_events() returns filing events for a known company number."""

    def test_fetch_events_returns_filings(self) -> None:
        _skip_if_cannot_reach(_CH_API_URL)
        from uk_data.adapters.companies_house import CompaniesHouseAdapter
        from uk_data.models import Event

        adapter = CompaniesHouseAdapter()
        # BBC's company number: 00101498
        events = adapter.fetch_events(entity_id="companies_house:00101498")
        assert isinstance(events, list)
        assert len(events) > 0
        for event in events:
            assert isinstance(event, Event)
            assert event.event_type == "filing"
            assert event.source == "companies_house"
            assert event.entity_id == "companies_house:00101498"

    def test_fetch_events_requires_entity_id(self) -> None:
        from uk_data.adapters.companies_house import CompaniesHouseAdapter

        adapter = CompaniesHouseAdapter()
        with pytest.raises(ValueError, match="entity_id"):
            adapter.fetch_events(entity_id=None)

    def test_get_events_via_client(self) -> None:
        _skip_if_cannot_reach(_CH_API_URL)
        from uk_data.models import Event

        client = UKDataClient()
        events = client.get_events(
            entity_id="companies_house:00101498", source="companies_house"
        )
        assert isinstance(events, list)
        assert len(events) > 0
        assert all(isinstance(e, Event) for e in events)
