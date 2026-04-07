"""Tests for the companies_house.schema module."""

from __future__ import annotations

import datetime
from decimal import Decimal

import polars as pl

from companies_house.schema import (
    COMPANIES_HOUSE_SCHEMA,
    DEDUP_COLUMNS,
    SIC_TO_SECTOR,
    CompanyFiling,
)


class TestPolarsSchema:
    def test_has_39_columns(self):
        assert len(COMPANIES_HOUSE_SCHEMA) == 39

    def test_dedup_columns_subset(self):
        for col in DEDUP_COLUMNS:
            assert col in COMPANIES_HOUSE_SCHEMA

    def test_financial_fields_are_decimal(self):
        for _col, dtype in COMPANIES_HOUSE_SCHEMA.items():
            if isinstance(dtype, pl.Decimal):
                assert dtype.precision == 20
                assert dtype.scale == 2


class TestSicToSector:
    def test_manufacturing_divisions(self):
        for i in range(10, 34):
            assert SIC_TO_SECTOR[f"{i:02d}"] == "manufacturing"

    def test_construction(self):
        assert SIC_TO_SECTOR["41"] == "construction"

    def test_financial(self):
        assert SIC_TO_SECTOR["64"] == "financial"


class TestCompanyFiling:
    def test_minimal_instance(self):
        filing = CompanyFiling(company_id="01873499")
        assert filing.company_id == "01873499"
        assert filing.turnover_gross_operating_revenue is None

    def test_full_instance(self):
        filing = CompanyFiling(
            company_id="01873499",
            entity_current_legal_name="Exel Computer Systems PLC",
            balance_sheet_date=datetime.date(2023, 1, 31),
            period_start=datetime.date(2022, 2, 1),
            period_end=datetime.date(2023, 1, 31),
            turnover_gross_operating_revenue=Decimal("9281499.00"),
            file_type="html",
        )
        assert filing.entity_current_legal_name == "Exel Computer Systems PLC"
        assert filing.turnover_gross_operating_revenue == Decimal("9281499.00")

    def test_to_polars_row(self):
        filing = CompanyFiling(
            company_id="12345678",
            turnover_gross_operating_revenue=Decimal("1000.50"),
        )
        row = filing.to_polars_row()
        assert isinstance(row, dict)
        assert row["company_id"] == "12345678"
        assert row["turnover_gross_operating_revenue"] == Decimal("1000.50")
        assert row["error"] is None

    def test_polars_schema_class_method(self):
        schema = CompanyFiling.polars_schema()
        assert schema == COMPANIES_HOUSE_SCHEMA

    def test_duckdb_ddl(self):
        ddl = CompanyFiling.duckdb_ddl("test_filings")
        assert "CREATE TABLE IF NOT EXISTS test_filings" in ddl
        assert "company_id VARCHAR" in ddl
        assert "balance_sheet_date DATE" in ddl
        assert "DECIMAL(20, 2)" in ddl
        pk_cols = ", ".join(DEDUP_COLUMNS)
        assert f"PRIMARY KEY ({pk_cols})" in ddl

    def test_to_polars_dataframe_round_trip(self):
        filing = CompanyFiling(
            company_id="00000001",
            balance_sheet_date=datetime.date(2023, 12, 31),
            period_start=datetime.date(2023, 1, 1),
            period_end=datetime.date(2023, 12, 31),
            turnover_gross_operating_revenue=Decimal("500000.00"),
        )
        df = pl.DataFrame([filing.to_polars_row()], schema=COMPANIES_HOUSE_SCHEMA)
        assert len(df) == 1
        assert df["company_id"][0] == "00000001"
