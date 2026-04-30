"""Integration tests for ONSAdapter — makes real network requests.

Run with::

    uv run pytest -m integration \
        packages/uk-data-client/tests/adapters/test_ons_integration.py
"""

from __future__ import annotations

import urllib.request

import pytest

from uk_data.adapters.ons import ONSAdapter
from uk_data.adapters.ons_models import (
    ONSDatasetInfo,
    ONSDatasetVersionInfo,
    ONSObservation,
)
from uk_data.models import TimeSeries
from uk_data.utils.http import clear_cache

pytestmark = pytest.mark.integration

_ONS_URL = "https://api.ons.gov.uk/v1"


def _skip_if_cannot_reach(url: str) -> None:
    try:
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pytest.skip(f"Network unavailable or {url} unreachable")


class TestONSAdapterIntegration:
    """Verify every ONS series ID in available_series() can be fetched live."""

    def test_gdp_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("ABMI")
        assert isinstance(ts, TimeSeries)
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert ts.latest_value > 0, "GDP should be positive"

    def test_household_income_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("RPHQ")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_savings_ratio_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("NRJS")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_unemployment_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("MGSX")
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert 0 <= ts.latest_value <= 30, "UK unemployment rate should be 0-30%"

    def test_average_earnings_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("KAB9")
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert ts.latest_value > 0, "Average weekly earnings should be positive"

    def test_affordability_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("HP7A")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_rental_index_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("D7RA")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_all_advertised_series_fetchable_live(self) -> None:
        """Parametric: every series in available_series() must succeed live."""
        _skip_if_cannot_reach(_ONS_URL)

        clear_cache()
        adapter = ONSAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None, f"ONS series {series_id!r} returned None"
            assert ts.source == "ons"
            assert ts.latest_value is not None, (
                f"ONS series {series_id!r} returned null latest_value"
            )

    def test_list_datasets_live(self) -> None:
        adapter = ONSAdapter()
        result = adapter.list_datasets()
        assert isinstance(result, list), "Expected list of datasets"
        assert isinstance(result[0], ONSDatasetInfo), "Expected dataset details"

    def test_get_dataset_live(self) -> None:
        adapter = ONSAdapter()
        dataset = adapter.get_dataset("cpih01")
        assert isinstance(dataset, ONSDatasetInfo), "Expected dataset details"

    def test_get_version_live(self) -> None:
        adapter = ONSAdapter()
        version = adapter.get_version("cpih01", "time-series", 6)
        assert isinstance(version, ONSDatasetVersionInfo), "Expected version details"

    def test_get_observations_live(self) -> None:

        adapter = ONSAdapter()
        result = adapter.get_observation(
            "cpih01",
            "time-series",
            6,
            time="Aug-16",
            geography="K02000001",
            aggregate="cpih1dim1A0",
        )
        assert isinstance(result, ONSObservation), "Expected ONSObservation container"
        assert len(result.observations) > 0, "Expected at least one observation"
