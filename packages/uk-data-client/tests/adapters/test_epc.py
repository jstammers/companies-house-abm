"""Unit tests for EPCAdapter — including file-based helpers."""

from __future__ import annotations

import pytest

from uk_data_client.adapters.epc import EPCAdapter
from uk_data_client.client import UKDataClient


class TestEPCAdapterFetchSeries:
    def test_fetch_series_raises_not_implemented(self) -> None:
        adapter = EPCAdapter()
        with pytest.raises(NotImplementedError):
            adapter.fetch_series("any_series")

    def test_available_series_is_empty(self) -> None:
        adapter = EPCAdapter()
        assert adapter.available_series() == []


class TestEPCAdapterEventTypes:
    def test_event_types_contains_epc_lodgement(self) -> None:
        assert "epc_lodgement" in EPCAdapter().available_event_types()

    def test_no_entity_types(self) -> None:
        assert EPCAdapter().available_entity_types() == []


def test_epc_clean_and_event_conversion(tmp_path):
    from uk_data_client.adapters.epc import (
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
