"""Tests for the bytes-and-mortar-derived property and EPC source helpers."""

from __future__ import annotations

from uk_data_client.client import UKDataClient


def test_price_paid_load_clean_and_event_conversion(tmp_path):
    from uk_data_client.adapters.land_registry import (
        clean_price_paid_data,
        fetch_property_transaction_events,
        load_price_paid_data,
    )

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
    from uk_data_client.adapters.land_registry import fetch_uk_hpi_history

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
    assert series.latest_value == 285000.0
    assert len(series.values) == 2


def test_land_registry_adapter_events_and_series(tmp_path):
    from uk_data_client.adapters.land_registry import LandRegistryAdapter

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
    assert series.latest_value == 285000.0


def test_epc_clean_and_event_conversion(tmp_path):
    from uk_data_client.adapters.epc import (
        EPCAdapter,
        clean_epc_data,
        fetch_epc_lodgement_events,
        load_epc_data,
    )

    csv_path = tmp_path / "epc.csv"
    csv_path.write_text(
        "lmk-key,postcode,current-energy-rating,inspection-date,lodgement-date,total-floor-area,number-habitable-rooms,transaction-type,uprn\n"
        "abc-123,sw1a1aa,C,2024-01-01,2024-01-10,85.0,5,sale,10001\n"
        "bad-row,,Z,2024-01-01,2024-01-10,70.0,4,rental,\n"
    )

    cleaned = clean_epc_data(load_epc_data(csv_path)).collect()
    assert len(cleaned) == 1
    assert cleaned["postcode"][0] == "SW1A1AA"

    events = fetch_epc_lodgement_events(csv_path)
    assert len(events) == 1
    assert events[0].event_type == "epc_lodgement"
    assert events[0].entity_id == "epc:uprn:10001"

    adapter = EPCAdapter()
    adapter_events = adapter.fetch_events(filepath=csv_path)
    assert len(adapter_events) == 1


def test_uk_data_client_registers_epc_adapter():
    client = UKDataClient()
    assert "epc" in client.adapters
