"""Unit tests for CompaniesHouseAdapter."""

from __future__ import annotations

import pytest

from uk_data.adapters.companies_house import CompaniesHouseAdapter


class TestCompaniesHouseAdapterFetchSeries:
    def test_fetch_series_always_raises(self) -> None:
        adapter = CompaniesHouseAdapter()
        with pytest.raises(ValueError, match="Unsupported Companies House series"):
            adapter.fetch_series("any_series")

    def test_available_series_is_empty(self) -> None:
        adapter = CompaniesHouseAdapter()
        assert adapter.available_series() == []


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
