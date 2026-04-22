"""Integration tests for LandRegistryAdapter — makes real network requests.

Run with::

    uv run pytest -m integration \
        packages/uk-data-client/tests/adapters/test_land_registry_integration.py
"""

from __future__ import annotations

import urllib.request

import pytest

from uk_data_client.adapters.land_registry import LandRegistryAdapter

pytestmark = pytest.mark.integration

_LAND_REGISTRY_URL = "https://landregistry.data.gov.uk"


def _skip_if_cannot_reach(url: str) -> None:
    try:
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pytest.skip(f"Network unavailable or {url} unreachable")


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
