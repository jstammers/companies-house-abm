"""Integration tests for ONSAdapter — makes real network requests.

Run with::

    uv run pytest -m integration \
        packages/uk-data-client/tests/adapters/test_ons_integration.py
"""

from __future__ import annotations

import urllib.request

import pytest

from uk_data.adapters.ons import ONSAdapter
from uk_data.models import TimeSeries

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
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("ABMI")
        assert isinstance(ts, TimeSeries)
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert ts.latest_value > 0, "GDP should be positive"

    def test_household_income_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("RPHQ")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_savings_ratio_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("NRJS")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_unemployment_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("MGSX")
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert 0 <= ts.latest_value <= 30, "UK unemployment rate should be 0-30%"

    def test_average_earnings_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("KAB9")
        assert ts.source == "ons"
        assert ts.latest_value is not None
        assert ts.latest_value > 0, "Average weekly earnings should be positive"

    def test_affordability_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("HP7A")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_rental_index_series_live(self) -> None:
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        ts = adapter.fetch_series("D7RA")
        assert ts.source == "ons"
        assert ts.latest_value is not None

    def test_all_advertised_series_fetchable_live(self) -> None:
        """Parametric: every series in available_series() must succeed live."""
        _skip_if_cannot_reach(_ONS_URL)
        from uk_data._http import clear_cache

        clear_cache()
        adapter = ONSAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None, f"ONS series {series_id!r} returned None"
            assert ts.source == "ons"
            assert ts.latest_value is not None, (
                f"ONS series {series_id!r} returned null latest_value"
            )
