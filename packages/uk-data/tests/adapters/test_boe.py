"""Unit tests for BoEAdapter — uses fallback values; network may be unavailable."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from uk_data.adapters.boe import BoEAdapter


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

    def test_bank_rate_falls_back_to_constant_when_feed_empty(self) -> None:
        """When the IADB returns no rows, the adapter must still surface a value."""
        with patch(
            "uk_data.adapters.boe.fetch_bank_rate",
            return_value=[],
        ):
            adapter = BoEAdapter()
            ts = adapter.fetch_series("IUMABEDR")
        assert ts.latest_value is not None
        assert 0.0 <= ts.latest_value <= 0.25, (
            "Bank Rate fallback should be in fraction convention"
        )
        assert ts.metadata.get("source_quality") == "fallback"

    def test_bank_rate_returns_fraction_convention_when_live(self) -> None:
        """Live IADB rows are percentages; adapter should convert to fractions."""
        with patch(
            "uk_data.adapters.boe.fetch_bank_rate",
            return_value=[
                {"date": "01 Oct 2024", "value": "5.00"},
                {"date": "01 Nov 2024", "value": "4.75"},
            ],
        ):
            adapter = BoEAdapter()
            ts = adapter.fetch_series("IUMABEDR")
        assert ts.latest_value == pytest.approx(0.0475)

    def test_bank_rate_applies_inclusive_date_window(self) -> None:
        with patch(
            "uk_data.adapters.boe.fetch_bank_rate",
            return_value=[
                {"date": "31 Dec 2023", "value": "5.50"},
                {"date": "01 Jan 2024", "value": "5.25"},
                {"date": "31 Mar 2024", "value": "5.00"},
                {"date": "01 Apr 2024", "value": "4.75"},
            ],
        ):
            adapter = BoEAdapter()
            ts = adapter.fetch_series(
                "IUMABEDR",
                start_date="2024-01-01",
                end_date="2024-03-31",
            )

        assert ts.values.tolist() == pytest.approx([0.0525, 0.05])

    def test_bank_rate_filters_before_limit(self) -> None:
        with patch(
            "uk_data.adapters.boe.fetch_bank_rate",
            return_value=[
                {"date": "01 Jan 2024", "value": "5.50"},
                {"date": "01 Feb 2024", "value": "5.25"},
                {"date": "01 Mar 2024", "value": "5.00"},
                {"date": "01 Apr 2024", "value": "4.75"},
            ],
        ):
            adapter = BoEAdapter()
            ts = adapter.fetch_series(
                "IUMABEDR",
                start_date="2024-01-01",
                end_date="2024-03-31",
                limit=2,
            )

        assert ts.values.tolist() == pytest.approx([0.0525, 0.05])
