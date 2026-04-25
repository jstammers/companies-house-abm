"""Unit tests for HMRCAdapter — static data, no network required."""

from __future__ import annotations

import pytest

from uk_data.adapters.hmrc import HMRCAdapter


class TestHMRCAdapterAvailableSeries:
    def test_includes_three_kinds_per_tax_year(self) -> None:
        adapter = HMRCAdapter()
        series = adapter.available_series()
        # Three kinds (corporation_tax, income_tax_basic, vat_standard)
        # times N supported tax years.
        assert len(series) % 3 == 0
        expected_2024 = {
            "corporation_tax_2024",
            "income_tax_basic_2024",
            "vat_standard_2024",
        }
        assert expected_2024 <= set(series)

    def test_advertises_multiple_tax_years(self) -> None:
        from uk_data.adapters.hmrc import supported_tax_years

        adapter = HMRCAdapter()
        series = adapter.available_series()
        years = supported_tax_years()
        for year in years:
            start = year.split("/", 1)[0]
            assert f"corporation_tax_{start}" in series


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
