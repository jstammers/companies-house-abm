"""Integration tests for uk_data_client adapters and UKDataClient.

These tests make REAL network requests to verify that every adapter registered
in UKDataClient can successfully download its data from live sources.  They are
marked with ``pytest.mark.integration`` and are excluded from the default test
run; pass ``-m integration`` to execute them:

    uv run pytest tests/test_uk_data_client_integration.py -m integration -v

All assertions are structural invariants (non-empty, correct types, plausible
value ranges) rather than exact values so the tests remain valid as the
underlying datasets are updated over time.
"""

from __future__ import annotations

import urllib.request

import pytest

from uk_data_client import UKDataClient
from uk_data_client.adapters.boe import BoEAdapter
from uk_data_client.adapters.hmrc import HMRCAdapter
from uk_data_client.adapters.land_registry import LandRegistryAdapter
from uk_data_client.adapters.ons import ONSAdapter
from uk_data_client.models import TimeSeries

pytestmark = pytest.mark.integration  # applied to every test in this module

# ---------------------------------------------------------------------------
# Network availability helpers
# ---------------------------------------------------------------------------

_ONS_URL = "https://api.ons.gov.uk/v1"
_BOE_URL = "https://www.bankofengland.co.uk"
_LAND_REGISTRY_URL = "https://landregistry.data.gov.uk"


def _skip_if_cannot_reach(url: str) -> None:
    """Skip the calling test if *url* is not reachable within 5 s."""
    try:
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pytest.skip(f"Network unavailable or {url} unreachable")


# ---------------------------------------------------------------------------
# ONS adapter integration
# ---------------------------------------------------------------------------


class TestONSAdapterIntegration:
    """Verify every ONS series ID in available_series() can be fetched live."""

    def test_gdp_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("ABMI")
        assert isinstance(ts, TimeSeries)
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert ts.latest_value > 0, "GDP should be positive"

    def test_household_income_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("RPHQ")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_savings_ratio_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("NRJS")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_unemployment_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("MGSX")
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert 0 <= ts.latest_value <= 30, "UK unemployment rate should be 0-30%"

    def test_average_earnings_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("KAB9")
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert ts.latest_value > 0, "Average weekly earnings should be positive"

    def test_affordability_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("HP7A")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_rental_index_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("D7RA")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_all_advertised_series_fetchable_live(self) -> None:
        """Parametric: every series in available_series() must succeed live."""
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None, f"ONS series {series_id!r} returned None"
            assert ts.source == "ons"


# ---------------------------------------------------------------------------
# BoE adapter integration
# ---------------------------------------------------------------------------


class TestBoEAdapterIntegration:
    """Verify BoE series IDs return plausible values (with fallback tolerance)."""

    def test_bank_rate_live(self) -> None:
        _skip_if_cannot_reach(_BOE_URL)
        adapter = BoEAdapter()
        ts = adapter.fetch_series("IUMABEDR")
        assert ts.source == "boe"
        assert ts.latest_value is not None
        # Bank Rate has been between 0.1% and 20% in modern history
        assert 0 <= ts.latest_value <= 0.25, "Bank Rate should be 0-25%"

    def test_household_lending_rate_live(self) -> None:
        _skip_if_cannot_reach(_BOE_URL)
        adapter = BoEAdapter()
        ts = adapter.fetch_series("IUMTLMV")
        assert ts.source == "boe"
        assert ts.latest_value is not None
        assert 0 < ts.latest_value < 1, "Household lending rate should be 0-100%"

    def test_business_lending_rate_live(self) -> None:
        _skip_if_cannot_reach(_BOE_URL)
        adapter = BoEAdapter()
        ts = adapter.fetch_series("IUMZICQ")
        assert ts.source == "boe"
        assert ts.latest_value is not None
        assert 0 < ts.latest_value < 1, "Business lending rate should be 0-100%"

    def test_capital_ratio_live(self) -> None:
        _skip_if_cannot_reach(_BOE_URL)
        adapter = BoEAdapter()
        ts = adapter.fetch_series("LNMVNZL")
        assert ts.source == "boe"
        assert ts.latest_value is not None
        assert 0.05 < ts.latest_value < 1, "CET1 capital ratio should be 5-100%"

    def test_all_advertised_series_fetchable_live(self) -> None:
        _skip_if_cannot_reach(_BOE_URL)
        adapter = BoEAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None, f"BoE series {series_id!r} returned None"


# ---------------------------------------------------------------------------
# HMRC adapter integration (static data — no network needed, but included for
# completeness and to confirm the static values remain plausible)
# ---------------------------------------------------------------------------


class TestHMRCAdapterIntegration:
    """HMRC data is static; these tests always run (no network skip needed)."""

    def test_all_advertised_series_fetchable(self) -> None:
        adapter = HMRCAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None
            assert ts.source == "hmrc"

    def test_corporation_tax_plausible(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("corporation_tax_2024")
        # UK corporation tax main rate is 25% from April 2023
        assert ts.latest_value == pytest.approx(0.25, abs=0.01)

    def test_income_tax_basic_plausible(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("income_tax_basic_2024")
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)

    def test_vat_standard_plausible(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("vat_standard_2024")
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)


# ---------------------------------------------------------------------------
# Land Registry adapter integration
# ---------------------------------------------------------------------------


class TestLandRegistryAdapterIntegration:
    """uk_hpi_average hits the SPARQL endpoint; skip if unreachable."""

    def test_uk_hpi_average_live(self) -> None:
        _skip_if_cannot_reach(_LAND_REGISTRY_URL)
        adapter = LandRegistryAdapter()
        ts = adapter.fetch_series("uk_hpi_average")
        assert ts.source == "land_registry"
        assert ts.latest_value is not None
        assert ts.latest_value > 50_000, "UK average house price should be >£50k"
        assert ts.latest_value < 2_000_000, "UK average house price should be <£2M"


# ---------------------------------------------------------------------------
# UKDataClient.list_sources() + get_series() via concept registry
# ---------------------------------------------------------------------------


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
        from uk_data_client._http import clear_cache

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
        """Every concept in CONCEPT_REGISTRY must be resolvable without error
        (network skipped for concepts that require live data)."""
        from uk_data_client.registry import CONCEPT_REGISTRY

        _skip_if_cannot_reach(_ONS_URL)
        from uk_data_client._http import clear_cache

        clear_cache()
        client = UKDataClient()
        for concept in CONCEPT_REGISTRY:
            ts = client.get_series(concept)
            assert ts is not None, f"Concept {concept!r} returned None"
