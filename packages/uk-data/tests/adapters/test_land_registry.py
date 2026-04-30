"""Unit tests for LandRegistryAdapter — including file-based helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from uk_data.adapters.land_registry import (
    LandRegistryAdapter,
    clean_price_paid_data,
    fetch_property_transaction_events,
    fetch_uk_hpi_history,
    load_price_paid_data,
)


class TestLandRegistryAdapterAvailableSeries:
    def test_returns_two_series(self) -> None:
        adapter = LandRegistryAdapter()
        series = adapter.available_series()
        assert len(series) == 2

    def test_contains_expected_ids(self) -> None:
        adapter = LandRegistryAdapter()
        series = adapter.available_series()
        assert set(series) == {"uk_hpi_average", "uk_hpi_full"}


class TestLandRegistryAdapterFetchSeriesOffline:
    def test_uk_hpi_average_returns_timeseries(self) -> None:
        with patch(
            "uk_data.adapters.land_registry.fetch_uk_average_price",
            return_value=285_000.0,
        ):
            adapter = LandRegistryAdapter()
            ts = adapter.fetch_series("uk_hpi_average")
            assert ts.source == "land_registry"
            assert ts.latest_value == pytest.approx(285_000.0)

    def test_uk_hpi_full_requires_filepath(self) -> None:
        adapter = LandRegistryAdapter()
        with pytest.raises(ValueError, match="filepath"):
            adapter.fetch_series("uk_hpi_full")

    def test_unsupported_series_raises(self) -> None:
        adapter = LandRegistryAdapter()
        with pytest.raises(ValueError, match="Unsupported Land Registry series"):
            adapter.fetch_series("invalid_lr_series")


class TestLandRegistryAdapterEventTypes:
    def test_event_types_contains_property_transaction(self) -> None:
        assert "property_transaction" in LandRegistryAdapter().available_event_types()

    def test_no_entity_types(self) -> None:
        assert LandRegistryAdapter().available_entity_types() == []


def test_price_paid_load_clean_and_event_conversion(tmp_path):

    csv_path = tmp_path / "pp-sample.csv"
    csv_path.write_text(
        "{tx-1},{250000},{2024-01-15 00:00},{SW1A 1AA},{D},{N},{F},{10},,"
        "{Main Street},,{London},{Westminster},{Greater London},{A},{A}\n"
        "{tx-2},{9000},{2024-01-20 00:00},{SW1A 2AA},{F},{N},{L},{11},,"
        "{Bad Street},,{London},{Westminster},{Greater London},{A},{A}\n"
        "{tx-3},{300000},{2024-02-01 00:00},,{S},{N},{F},{12},,"
        "{No Postcode},,{London},{Westminster},{Greater London},{A},{A}\n"
    )

    cleaned = clean_price_paid_data(load_price_paid_data(csv_path)).collect()

    assert len(cleaned) == 1
    assert cleaned["postcode"][0] == "SW1A 1AA"
    assert cleaned["property_type_label"][0] == "Detached"
    assert cleaned["postcode_outward"][0] == "SW1A"

    events = fetch_property_transaction_events(csv_path)
    assert len(events) == 1
    assert events[0].event_type == "property_transaction"
    assert events[0].payload["transaction_id"] == "tx-1"


def test_uk_hpi_history_from_local_file(tmp_path):

    csv_path = tmp_path / "uk-hpi.csv"
    csv_path.write_text(
        "Date,RegionName,Average Price,Sales Volume\n"
        "01/03/2025,United Kingdom,280000,1000\n"
        "01/04/2025,United Kingdom,285000,1100\n"
        "01/04/2025,London,525000,400\n"
    )

    series = fetch_uk_hpi_history(csv_path, area_name="United Kingdom")

    assert series.series_id == "uk_hpi_monthly"
    assert series.source == "land_registry"
    assert series.latest_value == pytest.approx(285_000.0)
    assert len(series.values) == 2


def test_uk_hpi_history_applies_inclusive_date_window(tmp_path):

    csv_path = tmp_path / "uk-hpi.csv"
    csv_path.write_text(
        "Date,RegionName,Average Price,Sales Volume\n"
        "01/12/2023,United Kingdom,275000,900\n"
        "01/01/2024,United Kingdom,280000,1000\n"
        "01/03/2024,United Kingdom,290000,1200\n"
        "01/04/2024,United Kingdom,295000,1250\n"
    )

    series = fetch_uk_hpi_history(
        csv_path,
        area_name="United Kingdom",
        start_date="2024-01-01",
        end_date="2024-03-01",
    )

    assert series.values.tolist() == pytest.approx([280_000.0, 290_000.0])


def test_uk_hpi_history_filters_before_limit(tmp_path):

    csv_path = tmp_path / "uk-hpi.csv"
    csv_path.write_text(
        "Date,RegionName,Average Price,Sales Volume\n"
        "01/01/2024,United Kingdom,280000,1000\n"
        "01/02/2024,United Kingdom,285000,1100\n"
        "01/03/2024,United Kingdom,290000,1200\n"
        "01/04/2024,United Kingdom,295000,1250\n"
    )

    series = fetch_uk_hpi_history(
        csv_path,
        area_name="United Kingdom",
        start_date="2024-01-01",
        end_date="2024-03-01",
        limit=1,
    )

    assert series.values.tolist() == pytest.approx([290_000.0])


def test_uk_hpi_history_pushes_date_filter_into_lazy_query(tmp_path):

    csv_path = tmp_path / "uk-hpi.csv"
    csv_path.write_text(
        "Date,RegionName,Average Price,Sales Volume\n"
        "01/12/2023,United Kingdom,275000,900\n"
        "01/01/2024,United Kingdom,280000,1000\n"
        "01/03/2024,United Kingdom,290000,1200\n"
        "01/04/2024,United Kingdom,295000,1250\n"
    )

    with patch(
        "uk_data.adapters.land_registry.filter_observations_by_date_window",
        side_effect=AssertionError("post-hoc filter should not be called"),
        create=True,
    ):
        series = fetch_uk_hpi_history(
            csv_path,
            area_name="United Kingdom",
            start_date="2024-01-01",
            end_date="2024-03-01",
            limit=20,
        )

    assert series.values.tolist() == pytest.approx([280_000.0, 290_000.0])


def test_land_registry_adapter_events_and_series(tmp_path):
    price_paid_path = tmp_path / "pp-sample.csv"
    price_paid_path.write_text(
        "{tx-1},{250000},{2024-01-15 00:00},{SW1A 1AA},{D},{N},{F},{10},,"
        "{Main Street},,{London},{Westminster},{Greater London},{A},{A}\n"
    )
    uk_hpi_path = tmp_path / "uk-hpi.csv"
    uk_hpi_path.write_text(
        "Date,RegionName,Average Price\n01/04/2025,United Kingdom,285000\n"
    )

    adapter = LandRegistryAdapter()
    events = adapter.fetch_events(filepath=price_paid_path)
    series = adapter.fetch_series("uk_hpi_full", filepath=uk_hpi_path)

    assert len(events) == 1
    assert events[0].event_type == "property_transaction"
    assert series.latest_value == pytest.approx(285_000.0)
