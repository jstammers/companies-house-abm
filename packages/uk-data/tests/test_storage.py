"""Tests for uk_data.storage.canonical — upsert and typed query."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import polars as pl
import pytest

from uk_data.storage.canonical import CanonicalStore


def _make_store(tmp_path: Path) -> CanonicalStore:
    return CanonicalStore(tmp_path)


def _sample_frame(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows)


# ---------------------------------------------------------------------------
# Upsert tests
# ---------------------------------------------------------------------------


class TestUpsert:
    def test_creates_parquet_from_scratch(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        df = _sample_frame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "value": 5.25,
                },
            ]
        )
        path = store.upsert(df, "boe/rates.parquet")
        assert path.exists()
        result = pl.read_parquet(path)
        assert len(result) == 1

    def test_replaces_duplicate_key(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        original = _sample_frame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "value": 5.0,
                },
            ]
        )
        store.upsert(original, "boe/rates.parquet")

        updated = _sample_frame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "value": 5.25,
                },
            ]
        )
        store.upsert(updated, "boe/rates.parquet")

        result = pl.read_parquet(store._canonical_path("boe/rates.parquet"))
        assert len(result) == 1
        assert result["value"][0] == pytest.approx(5.25)

    def test_appends_new_rows(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        first = _sample_frame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "value": 5.0,
                },
            ]
        )
        store.upsert(first, "boe/rates.parquet")

        second = _sample_frame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-02-01",
                    "value": 5.25,
                },
            ]
        )
        store.upsert(second, "boe/rates.parquet")

        result = pl.read_parquet(store._canonical_path("boe/rates.parquet"))
        assert len(result) == 2

    def test_raises_on_missing_key_column(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        df = pl.DataFrame({"value": [1.0]})
        with pytest.raises(ValueError, match="missing"):
            store.upsert(df, "bad.parquet")

    def test_idempotent_double_upsert(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        df = _sample_frame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "value": 5.25,
                },
            ]
        )
        store.upsert(df, "boe/rates.parquet")
        store.upsert(df, "boe/rates.parquet")

        result = pl.read_parquet(store._canonical_path("boe/rates.parquet"))
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Typed query tests
# ---------------------------------------------------------------------------


class TestQueryTyped:
    def _write_sample(self, store: CanonicalStore, relative_path: str) -> None:
        df = pl.DataFrame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "concept": "bank_rate",
                    "value": 5.0,
                },
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-02-01",
                    "concept": "bank_rate",
                    "value": 5.25,
                },
                {
                    "source": "ons",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "concept": "gdp_growth",
                    "value": 0.3,
                },
            ]
        )
        store.write_parquet(df, relative_path)

    def test_no_filters_returns_all(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        self._write_sample(store, "data.parquet")
        result = store.query_typed("data.parquet")
        assert len(result) == 3

    def test_filter_by_concept(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        self._write_sample(store, "data.parquet")
        result = store.query_typed("data.parquet", concept="bank_rate")
        assert len(result) == 2
        assert set(result["concept"].to_list()) == {"bank_rate"}

    def test_filter_by_entity(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        df = pl.DataFrame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "concept": "bank_rate",
                    "value": 5.0,
                },
                {
                    "source": "boe",
                    "entity_id": "US",
                    "timestamp": "2024-01-01",
                    "concept": "fed_rate",
                    "value": 5.5,
                },
            ]
        )
        store.write_parquet(df, "data.parquet")
        result = store.query_typed("data.parquet", entity="UK")
        assert len(result) == 1
        assert result["entity_id"][0] == "UK"

    def test_filter_by_date_range(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        self._write_sample(store, "data.parquet")
        result = store.query_typed("data.parquet", start="2024-02-01", end="2024-12-31")
        assert len(result) == 1
        assert result["value"][0] == pytest.approx(5.25)

    def test_raw_sql_escape_hatch(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        self._write_sample(store, "data.parquet")
        result = store.query_typed(
            "data.parquet", sql="SELECT * FROM data WHERE source = 'ons'"
        )
        assert len(result) == 1
        assert result["source"][0] == "ons"

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        with pytest.raises(FileNotFoundError):
            store.query_typed("nonexistent.parquet")

    def test_raises_on_invalid_start_date(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        self._write_sample(store, "data.parquet")
        with pytest.raises(ValueError, match="start"):
            store.query_typed("data.parquet", start="not-a-date")

    def test_concept_filter_skipped_when_column_absent(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        df = pl.DataFrame(
            [
                {
                    "source": "boe",
                    "entity_id": "UK",
                    "timestamp": "2024-01-01",
                    "value": 5.0,
                },
            ]
        )
        store.write_parquet(df, "data.parquet")
        # Should not raise even though concept column is absent
        result = store.query_typed("data.parquet", concept="bank_rate")
        assert len(result) == 1
