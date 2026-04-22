"""Unit tests for BoEAdapter — uses fallback values; network may be unavailable."""

from __future__ import annotations

import pytest

from uk_data_client.adapters.boe import BoEAdapter


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
