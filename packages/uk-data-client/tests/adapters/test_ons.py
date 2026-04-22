"""Unit tests for ONSAdapter — fully offline (HTTP mocked)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from uk_data_client.adapters.ons import ONSAdapter


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
        expected = {"ABMI", "RPHQ", "NRJS", "MGSX", "KAB9", "HP7A", "D7RA"}
        assert expected == set(series)

    def test_no_duplicates(self) -> None:
        adapter = ONSAdapter()
        series = adapter.available_series()
        assert len(series) == len(set(series))


class TestONSAdapterFetchSeriesOffline:
    """Mock the HTTP layer so ONS tests never hit the network."""

    def _mock_observations(self) -> list[dict[str, object]]:
        return [{"date": "2024 Q1", "value": "100.0"}]

    def _patch_ons_http(self) -> patch:  # type: ignore[type-arg]
        """Return a patch target for the ONS internal HTTP fetch."""
        return patch(
            "uk_data_client.adapters.ons._fetch_timeseries",
            return_value=self._mock_observations(),
        )

    def test_gdp_series_returns_timeseries(self) -> None:
        with (
            patch(
                "uk_data_client.adapters.ons.fetch_gdp",
                return_value=self._mock_observations(),
            ),
        ):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("ABMI")
            assert ts.source == "ons"
            assert ts.source_series_id == "ABMI"

    def test_unemployment_series_returns_timeseries(self) -> None:
        with self._patch_ons_http():
            adapter = ONSAdapter()
            ts = adapter.fetch_series("MGSX")
            assert ts.source == "ons"

    def test_affordability_returns_point_series(self) -> None:
        with patch(
            "uk_data_client.adapters.ons.fetch_affordability_ratio",
            return_value=8.5,
        ):
            adapter = ONSAdapter()
            ts = adapter.fetch_series("HP7A")
            assert ts.source == "ons"
            assert ts.latest_value == pytest.approx(8.5)

    def test_rental_index_returns_point_series(self) -> None:
        with patch(
            "uk_data_client.adapters.ons.fetch_rental_growth",
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
