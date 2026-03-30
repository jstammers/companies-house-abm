"""Tests for the companies_house.storage module."""

from __future__ import annotations

import datetime
from decimal import Decimal

import polars as pl
import pytest

from companies_house.schema import COMPANIES_HOUSE_SCHEMA
from companies_house.storage.db import CompaniesHouseDB


def _make_filing_row(**overrides):
    """Build a single filing row dict with sensible defaults."""
    row = dict.fromkeys(COMPANIES_HOUSE_SCHEMA)
    row.update(
        {
            "company_id": "01873499",
            "balance_sheet_date": datetime.date(2023, 1, 31),
            "period_start": datetime.date(2022, 2, 1),
            "period_end": datetime.date(2023, 1, 31),
            "entity_current_legal_name": "Exel Computer Systems PLC",
            "date": datetime.date(2023, 4, 1),
            "file_type": "html",
        }
    )
    row.update(overrides)
    return row


def _make_df(rows=None):
    """Build a DataFrame from row dicts."""
    if rows is None:
        rows = [_make_filing_row()]
    return pl.DataFrame(rows, schema=COMPANIES_HOUSE_SCHEMA)


class TestCompaniesHouseDB:
    def test_create_in_memory(self):
        with CompaniesHouseDB(":memory:") as db:
            assert db.row_count() == 0

    def test_upsert_and_query(self):
        with CompaniesHouseDB(":memory:") as db:
            df = _make_df()
            count = db.upsert(df)
            assert count == 1
            assert db.row_count() == 1

            result = db.query_company("01873499")
            assert len(result) == 1
            assert result["company_id"][0] == "01873499"

    def test_upsert_idempotent(self):
        """Upserting the same row twice should not create duplicates."""
        with CompaniesHouseDB(":memory:") as db:
            df = _make_df()
            db.upsert(df)
            db.upsert(df)
            assert db.row_count() == 1

    def test_upsert_updates_existing(self):
        """Upserting with same PK but different values updates the row."""
        with CompaniesHouseDB(":memory:") as db:
            df1 = _make_df(
                [
                    _make_filing_row(
                        turnover_gross_operating_revenue=Decimal("1000.00"),
                    )
                ]
            )
            db.upsert(df1)

            df2 = _make_df(
                [
                    _make_filing_row(
                        turnover_gross_operating_revenue=Decimal("2000.00"),
                    )
                ]
            )
            db.upsert(df2)

            assert db.row_count() == 1
            result = db.query_company("01873499")
            val = result["turnover_gross_operating_revenue"][0]
            assert float(val) == 2000.0

    def test_upsert_empty_df(self):
        with CompaniesHouseDB(":memory:") as db:
            df = pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
            count = db.upsert(df)
            assert count == 0

    def test_multiple_companies(self):
        with CompaniesHouseDB(":memory:") as db:
            rows = [
                _make_filing_row(company_id="00000001"),
                _make_filing_row(company_id="00000002"),
            ]
            db.upsert(_make_df(rows))
            assert db.row_count() == 2
            assert len(db.query_company("00000001")) == 1
            assert len(db.query_company("00000002")) == 1
            assert len(db.query_company("99999999")) == 0

    def test_search_companies(self):
        with CompaniesHouseDB(":memory:") as db:
            db.upsert(
                _make_df(
                    [
                        _make_filing_row(
                            company_id="00000001",
                            entity_current_legal_name="Acme Corp",
                        ),
                        _make_filing_row(
                            company_id="00000002",
                            entity_current_legal_name="Beta Industries",
                        ),
                    ]
                )
            )
            result = db.search_companies("acme")
            assert len(result) == 1
            assert result["company_id"][0] == "00000001"

    def test_latest_date_empty(self):
        with CompaniesHouseDB(":memory:") as db:
            assert db.latest_date() is None

    def test_latest_date(self):
        with CompaniesHouseDB(":memory:") as db:
            db.upsert(
                _make_df(
                    [
                        _make_filing_row(date=datetime.date(2023, 4, 1)),
                        _make_filing_row(
                            company_id="00000002",
                            date=datetime.date(2024, 6, 15),
                        ),
                    ]
                )
            )
            assert db.latest_date() == datetime.date(2024, 6, 15)

    def test_export_parquet(self, tmp_path):
        with CompaniesHouseDB(":memory:") as db:
            db.upsert(_make_df())
            out = tmp_path / "export.parquet"
            db.export_parquet(out)
            assert out.exists()
            exported = pl.read_parquet(out)
            assert len(exported) == 1

    def test_import_parquet(self, tmp_path):
        # Write a parquet, then import into a fresh DB
        parquet = tmp_path / "source.parquet"
        _make_df().write_parquet(parquet)

        with CompaniesHouseDB(":memory:") as db:
            count = db.import_parquet(parquet)
            assert count == 1
            assert db.row_count() == 1

    def test_execute_query(self):
        with CompaniesHouseDB(":memory:") as db:
            db.upsert(_make_df())
            result = db.execute_query("SELECT company_id FROM filings")
            assert len(result) == 1

    def test_file_based_db(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        with CompaniesHouseDB(db_path) as db:
            db.upsert(_make_df())
            assert db.row_count() == 1

        # Re-open and verify data persists
        with CompaniesHouseDB(db_path) as db:
            assert db.row_count() == 1


class TestMigrateParquetToDuckdb:
    def test_migrate(self, tmp_path):
        from companies_house.storage.migrations import migrate_parquet_to_duckdb

        parquet = tmp_path / "source.parquet"
        _make_df(
            [
                _make_filing_row(company_id="00000001"),
                _make_filing_row(company_id="00000002"),
            ]
        ).write_parquet(parquet)

        count = migrate_parquet_to_duckdb(parquet, db_path=tmp_path / "migrated.duckdb")
        assert count == 2

    def test_missing_parquet(self, tmp_path):
        from companies_house.storage.migrations import migrate_parquet_to_duckdb

        with pytest.raises(FileNotFoundError):
            migrate_parquet_to_duckdb(tmp_path / "nonexistent.parquet")
