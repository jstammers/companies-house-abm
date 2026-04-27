"""Unit tests for ONSAdapter — fully offline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from uk_data.adapters.ons import ONSAdapter
from uk_data.adapters.ons_manifest import ONS_SERIES_IDS


class TestONSAdapterAvailableSeries:
    def test_returns_seven_series(self) -> None:
        adapter = ONSAdapter()
        series = adapter.available_series()
        assert len(series) == 7

    def test_contains_gdp_series(self) -> None:
        adapter = ONSAdapter()
        assert "ABMI" in adapter.available_series()

    def test_contains_all_expected_ids(self) -> None:
        adapter = ONSAdapter()
        series = adapter.available_series()
        assert set(ONS_SERIES_IDS) == set(series)

    def test_no_duplicates(self) -> None:
        adapter = ONSAdapter()
        series = adapter.available_series()
        assert len(series) == len(set(series))


class TestONSAdapterFetchSeriesOffline:
    """Mock the SDMX and fallback layers so ONS tests never hit the network."""

    def _mock_quarterly_observations(self) -> list[dict[str, str]]:
        return [
            {"date": "2024Q1", "value": "100.0"},
            {"date": "2024Q2", "value": "101.5"},
        ]

    def _mock_monthly_observations(self) -> list[dict[str, str]]:
        return [
            {"date": "2024-01-01", "value": "4.2"},
            {"date": "2024-02-01", "value": "4.1"},
        ]

    def _patch_ons_sdmx(
        self,
        observations: list[dict[str, str]],
    ) -> patch:  # type: ignore[type-arg]
        return patch(
            "uk_data.adapters.ons.fetch_sdmx_series",
            return_value=observations,
        )

    def test_manifest_backed_series_returns_timeseries_for_abmi(self) -> None:
        with self._patch_ons_sdmx(self._mock_quarterly_observations()):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("ABMI")
            assert ts.source == "ons"
            assert ts.source_series_id == "ABMI"
            assert ts.latest_value == pytest.approx(101.5)

    def test_manifest_backed_series_returns_timeseries_for_mgsx(self) -> None:
        with self._patch_ons_sdmx(self._mock_monthly_observations()):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("MGSX")
            assert ts.source == "ons"
            assert ts.latest_value == pytest.approx(4.1)

    def test_manifest_backed_series_sets_source_and_source_series_id(self) -> None:
        with self._patch_ons_sdmx(self._mock_quarterly_observations()):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("RPHQ")
            assert ts.source == "ons"
            assert ts.source_series_id == "RPHQ"

    def test_manifest_backed_series_converts_dates_and_numeric_values(self) -> None:
        with self._patch_ons_sdmx(self._mock_quarterly_observations()):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("NRJS")
            assert ts.values.tolist() == pytest.approx([100.0, 101.5])
            assert str(ts.timestamps[0]) == "2024-01-01T00:00:00.000000000"

    def test_affordability_series_still_uses_fallback_point_series(self) -> None:
        with patch(
            "uk_data.adapters.ons.fetch_affordability_ratio",
            return_value=8.5,
        ):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("HP7A")
            assert ts.source == "ons"
            assert ts.latest_value == pytest.approx(8.5)

    def test_rental_growth_series_still_uses_fallback_point_series(self) -> None:
        with patch(
            "uk_data.adapters.ons.fetch_rental_growth",
            return_value=0.03,
        ):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("D7RA")
            assert ts.source == "ons"
            assert ts.latest_value == pytest.approx(0.03)

    def test_unsupported_series_raises(self) -> None:
        adapter = ONSAdapter()
        with pytest.raises(ValueError, match="Unsupported ONS series"):
            adapter.fetch_series("NOTREAL_SERIES_ID")

    def test_sdmx_series_applies_inclusive_date_window(self) -> None:
        observations = [
            {"date": "2023-12-31", "value": "1.0"},
            {"date": "2024-01-01", "value": "2.0"},
            {"date": "2024-03-31", "value": "3.0"},
            {"date": "2024-04-01", "value": "4.0"},
        ]
        with self._patch_ons_sdmx(observations):
            adapter = ONSAdapter()
            ts = adapter.fetch_series(
                "ABMI",
                start_date="2024-01-01",
                end_date="2024-03-31",
            )

        assert ts.values.tolist() == pytest.approx([2.0, 3.0])

    def test_sdmx_series_filters_before_limit(self) -> None:
        observations = [
            {"date": "2024-01-01", "value": "1.0"},
            {"date": "2024-02-01", "value": "2.0"},
            {"date": "2024-03-01", "value": "3.0"},
            {"date": "2024-04-01", "value": "4.0"},
        ]
        with self._patch_ons_sdmx(observations):
            adapter = ONSAdapter()
            ts = adapter.fetch_series(
                "ABMI",
                start_date="2024-01-01",
                end_date="2024-03-01",
                limit=2,
            )

        assert ts.values.tolist() == pytest.approx([2.0, 3.0])
