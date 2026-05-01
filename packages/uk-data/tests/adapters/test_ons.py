"""Unit tests for ONSAdapter — fully offline."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from uk_data.adapters.ons import _SERIES_DATASET, ONSAdapter
from uk_data.storage.canonical import CanonicalStore
from uk_data.storage.raw import RawStore

ONS_SERIES_IDS = ["ABMI", "RPHQ", "NRJS", "MGSX", "KAB9", "HP7A", "D7RA"]


def _raw_payload(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Build a raw dataset-API observation payload (plain dicts, not pydantic)."""
    return {
        "dimensions": {},
        "observations": [
            {
                "dimensions": {"time": {"id": row["date"]}},
                "observation": row["value"],
            }
            for row in rows
        ],
        "limit": len(rows),
    }


def _make_adapter(tmp_path) -> ONSAdapter:
    return ONSAdapter(
        store=RawStore(tmp_path),
        canonical_store=CanonicalStore(tmp_path),
    )


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


class TestONSAdapterExtract:
    """Stage 1: extract fetches raw JSON and writes it to the RawStore."""

    def test_extract_writes_raw_payload_and_returns_key(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        rows = [{"date": "2024Q1", "value": "100.0"}]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ) as mocked:
            key = adapter.extract(
                "ukea", "time-series", "latest", timeseries="ABMI", time="*"
            )

        assert mocked.call_count == 1
        # The raw payload was persisted under a deterministic key.
        files = list((tmp_path / "raw" / "ons" / key).glob("*.json"))
        assert len(files) == 1
        assert "timeseries=ABMI" in key
        assert "time=*" in key

    def test_extract_does_not_validate_with_pydantic(self, tmp_path) -> None:
        """Extract must accept raw payloads that would fail pydantic validation."""
        adapter = _make_adapter(tmp_path)
        # Missing 'observations' key entirely; pydantic would still parse, but
        # we verify get_json is called and payload reaches the store untouched.
        weird_payload = {"foo": "bar", "garbage": [1, 2, 3]}
        with patch("uk_data.adapters.ons.get_json", return_value=weird_payload):
            key = adapter.extract("dataset_x", "time-series", "1")

        files = list((tmp_path / "raw" / "ons" / key).glob("*.json"))
        assert len(files) == 1

    def test_extract_series_uses_registry(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        rows = [{"date": "2024Q1", "value": "100.0"}]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ) as mocked:
            key = adapter.extract_series("ABMI")

        assert mocked.call_count == 1
        cfg = _SERIES_DATASET["ABMI"]
        assert cfg["dataset_id"] in mocked.call_args.args[0]
        assert "timeseries=ABMI" in key

    def test_extract_series_rejects_unknown_series(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        with pytest.raises(ValueError, match="Unsupported ONS series"):
            adapter.extract_series("NOT_A_SERIES")


class TestONSAdapterTransform:
    """Stage 2: transform validates raw and persists to canonical."""

    def test_transform_round_trips_raw_to_canonical(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        rows = [
            {"date": "2024Q1", "value": "100.0"},
            {"date": "2024Q2", "value": "101.5"},
        ]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ):
            key = adapter.extract_series("ABMI")

        ts = adapter.transform(key)
        assert ts.source == "ons"
        assert ts.source_series_id == "ABMI"
        assert ts.values.tolist() == pytest.approx([100.0, 101.5])

        canonical_path = tmp_path / "canonical" / "timeseries" / "ons.parquet"
        assert canonical_path.exists()

    def test_transform_missing_key_raises(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        with pytest.raises(FileNotFoundError):
            adapter.transform("nonexistent/key")

    def test_transform_invalid_payload_raises(self, tmp_path) -> None:
        """Pydantic validation surfaces from transform, not extract."""
        adapter = _make_adapter(tmp_path)
        # Save a payload whose 'observation' values cannot be coerced to float.
        bad_payload = {
            "observations": [
                {
                    "dimensions": {"time": {"id": "2024Q1"}},
                    "observation": "not-a-number",
                }
            ]
        }
        with patch("uk_data.adapters.ons.get_json", return_value=bad_payload):
            key = adapter.extract_series("ABMI")

        with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError
            adapter.transform(key)


class TestONSAdapterFetchSeriesFromCanonical:
    """Stage 3: fetch_series reads canonical store only — never the network."""

    def test_round_trip_returns_canonical_series(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        rows = [
            {"date": "2024Q1", "value": "100.0"},
            {"date": "2024Q2", "value": "101.5"},
        ]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ):
            key = adapter.extract_series("ABMI")
            adapter.transform(key)

        # fetch_series must not hit the network at all.
        with patch(
            "uk_data.adapters.ons.get_json",
            side_effect=AssertionError("fetch_series should not call the API"),
        ):
            ts = adapter.fetch_series("ABMI")

        assert ts.source == "ons"
        assert ts.source_series_id == "ABMI"
        assert ts.values.tolist() == pytest.approx([100.0, 101.5])
        assert ts.latest_value == pytest.approx(101.5)

    def test_fetch_series_raises_when_canonical_missing(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        with pytest.raises(FileNotFoundError):
            adapter.fetch_series("ABMI")

    def test_fetch_series_raises_without_canonical_store(self) -> None:
        adapter = ONSAdapter()
        with pytest.raises(FileNotFoundError):
            adapter.fetch_series("ABMI")

    def test_fetch_series_unsupported_id_raises(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        with pytest.raises(ValueError, match="Unsupported ONS series"):
            adapter.fetch_series("NOT_REAL")

    def test_fetch_series_applies_inclusive_date_window(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        rows = [
            {"date": "2023-12-31", "value": "1.0"},
            {"date": "2024-01-01", "value": "2.0"},
            {"date": "2024-03-31", "value": "3.0"},
            {"date": "2024-04-01", "value": "4.0"},
        ]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ):
            key = adapter.extract_series("ABMI")
            adapter.transform(key)

        ts = adapter.fetch_series(
            "ABMI",
            start_date="2024-01-01",
            end_date="2024-03-31",
        )
        assert ts.values.tolist() == pytest.approx([2.0, 3.0])

    def test_fetch_series_filters_before_limit(self, tmp_path) -> None:
        adapter = _make_adapter(tmp_path)
        rows = [
            {"date": "2024-01-01", "value": "1.0"},
            {"date": "2024-02-01", "value": "2.0"},
            {"date": "2024-03-01", "value": "3.0"},
            {"date": "2024-04-01", "value": "4.0"},
        ]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ):
            key = adapter.extract_series("ABMI")
            adapter.transform(key)

        ts = adapter.fetch_series(
            "ABMI",
            start_date="2024-01-01",
            end_date="2024-03-01",
            limit=2,
        )
        assert ts.values.tolist() == pytest.approx([2.0, 3.0])

    def test_fetch_series_for_affordability_via_dataset_api(self, tmp_path) -> None:
        """HP7A flows through the dataset API like every other series."""
        adapter = _make_adapter(tmp_path)
        rows = [{"date": "2023", "value": "8.5"}]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ):
            key = adapter.extract_series("HP7A")
            adapter.transform(key)

        ts = adapter.fetch_series("HP7A")
        assert ts.source == "ons"
        assert ts.source_series_id == "HP7A"
        assert ts.latest_value == pytest.approx(8.5)

    def test_fetch_series_for_rental_growth_via_dataset_api(self, tmp_path) -> None:
        """D7RA flows through the dataset API like every other series."""
        adapter = _make_adapter(tmp_path)
        rows = [{"date": "2024-01-01", "value": "0.05"}]
        with patch(
            "uk_data.adapters.ons.get_json",
            return_value=_raw_payload(rows),
        ):
            key = adapter.extract_series("D7RA")
            adapter.transform(key)

        ts = adapter.fetch_series("D7RA")
        assert ts.latest_value == pytest.approx(0.05)
