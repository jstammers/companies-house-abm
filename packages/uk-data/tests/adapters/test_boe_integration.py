"""Integration tests for BoEAdapter — makes real network requests.

Run with::

    uv run pytest -m integration \
        packages/uk-data-client/tests/adapters/test_boe_integration.py
"""

from __future__ import annotations

import urllib.request

import pytest

from uk_data.adapters.boe import BoEAdapter

pytestmark = pytest.mark.integration

_BOE_URL = "https://www.bankofengland.co.uk"


def _skip_if_cannot_reach(url: str) -> None:
    try:
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pytest.skip(f"Network unavailable or {url} unreachable")


class TestBoEAdapterIntegration:
    """Verify BoE series IDs return plausible values (with fallback tolerance)."""

    def test_bank_rate_live(self) -> None:
        _skip_if_cannot_reach(_BOE_URL)
        adapter = BoEAdapter()
        ts = adapter.fetch_series("IUMABEDR")
        assert ts.source == "boe"
        assert ts.latest_value is not None
        # Bank Rate is returned as a fraction (0.0-0.25 covers all modern history).
        assert 0 <= ts.latest_value <= 0.25, (
            "Bank Rate should be 0-25% (fraction convention)"
        )

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
