"""Unit tests for HMRCAdapter — static data, no network required."""

from __future__ import annotations

import pytest

from uk_data_client.adapters.hmrc import HMRCAdapter


class TestHMRCAdapterAvailableSeries:
    def test_returns_three_series(self) -> None:
        adapter = HMRCAdapter()
        series = adapter.available_series()
        assert len(series) == 3

    def test_contains_all_expected_ids(self) -> None:
        adapter = HMRCAdapter()
        series = adapter.available_series()
        expected = {
            "corporation_tax_2024",
            "income_tax_basic_2024",
            "vat_standard_2024",
        }
        assert expected == set(series)


class TestHMRCAdapterFetchSeries:
    def test_corporation_tax_value(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("corporation_tax_2024")
        assert ts.source == "hmrc"
        assert ts.latest_value is not None
        assert 0 < ts.latest_value <= 1  # fraction

    def test_income_tax_basic_value(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("income_tax_basic_2024")
        assert ts.source == "hmrc"
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)

    def test_vat_standard_value(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("vat_standard_2024")
        assert ts.source == "hmrc"
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)

    def test_unsupported_series_raises(self) -> None:
        adapter = HMRCAdapter()
        with pytest.raises(ValueError, match="Unsupported HMRC series"):
            adapter.fetch_series("unknown_hmrc_series")

    def test_all_advertised_series_fetchable(self) -> None:
        """Every series in available_series() must be fetchable without error."""
        adapter = HMRCAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None
