"""Canonical schema for Companies House filing records.

Provides both a Polars schema (for DataFrame operations / Parquet I/O) and a
Pydantic model (for LLM extraction, API validation, and DuckDB mapping).
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

import polars as pl
from pydantic import BaseModel, ConfigDict

_DECIMAL = pl.Decimal(20, 2)

# ---------------------------------------------------------------------------
# Polars schema — the 39-column layout used throughout the pipeline
# ---------------------------------------------------------------------------

COMPANIES_HOUSE_SCHEMA: dict[str, pl.DataType] = {
    # Run-level fields
    "run_code": pl.Utf8,
    # Company-at-date fields
    "company_id": pl.Utf8,
    "date": pl.Date,
    "file_type": pl.Utf8,
    "taxonomy": pl.Utf8,
    "balance_sheet_date": pl.Date,
    "companies_house_registered_number": pl.Utf8,
    "entity_current_legal_name": pl.Utf8,
    "company_dormant": pl.Boolean,
    "average_number_employees_during_period": _DECIMAL,
    # Period-level fields
    "period_start": pl.Date,
    "period_end": pl.Date,
    # Balance sheet
    "tangible_fixed_assets": _DECIMAL,
    "debtors": _DECIMAL,
    "cash_bank_in_hand": _DECIMAL,
    "current_assets": _DECIMAL,
    "creditors_due_within_one_year": _DECIMAL,
    "creditors_due_after_one_year": _DECIMAL,
    "net_current_assets_liabilities": _DECIMAL,
    "total_assets_less_current_liabilities": _DECIMAL,
    "net_assets_liabilities_including_pension_asset_liability": _DECIMAL,
    "called_up_share_capital": _DECIMAL,
    "profit_loss_account_reserve": _DECIMAL,
    "shareholder_funds": _DECIMAL,
    # P&L
    "turnover_gross_operating_revenue": _DECIMAL,
    "other_operating_income": _DECIMAL,
    "cost_sales": _DECIMAL,
    "gross_profit_loss": _DECIMAL,
    "administrative_expenses": _DECIMAL,
    "raw_materials_consumables": _DECIMAL,
    "staff_costs": _DECIMAL,
    "depreciation_other_amounts_written_off_tangible_intangible_fixed_assets": _DECIMAL,
    "other_operating_charges_format2": _DECIMAL,
    "operating_profit_loss": _DECIMAL,
    "profit_loss_on_ordinary_activities_before_tax": _DECIMAL,
    "tax_on_profit_or_loss_on_ordinary_activities": _DECIMAL,
    "profit_loss_for_period": _DECIMAL,
    "error": pl.Utf8,
    "zip_url": pl.Utf8,
}

DEDUP_COLUMNS = [
    "company_id",
    "balance_sheet_date",
    "period_start",
    "period_end",
]

# ---------------------------------------------------------------------------
# SIC-to-sector mapping (extracted from firm_distributions for independence)
# ---------------------------------------------------------------------------

SIC_TO_SECTOR: dict[str, str] = {
    # Agriculture, forestry and fishing: SIC divisions 01 to 03
    "01": "agriculture",
    "02": "agriculture",
    "03": "agriculture",
    # Mining: SIC divisions 05 to 09 -> mapped to manufacturing
    "05": "manufacturing",
    "06": "manufacturing",
    "07": "manufacturing",
    "08": "manufacturing",
    "09": "manufacturing",
    # Manufacturing: SIC divisions 10 to 33
    **{f"{i:02d}": "manufacturing" for i in range(10, 34)},
    # Electricity, gas, water, waste: SIC divisions 35 to 39
    "35": "manufacturing",
    "36": "manufacturing",
    "37": "manufacturing",
    "38": "manufacturing",
    "39": "manufacturing",
    # Construction: SIC divisions 41 to 43
    "41": "construction",
    "42": "construction",
    "43": "construction",
    # Wholesale and retail trade: SIC divisions 45 to 47
    "45": "wholesale_retail",
    "46": "wholesale_retail",
    "47": "wholesale_retail",
    # Transport and storage: SIC divisions 49 to 53
    "49": "transport",
    "50": "transport",
    "51": "transport",
    "52": "transport",
    "53": "transport",
    # Accommodation and food: SIC divisions 55 to 56
    "55": "hospitality",
    "56": "hospitality",
    # Information and communication: SIC divisions 58 to 63
    "58": "information_communication",
    "59": "information_communication",
    "60": "information_communication",
    "61": "information_communication",
    "62": "information_communication",
    "63": "information_communication",
    # Financial and insurance: SIC divisions 64 to 66
    "64": "financial",
    "65": "financial",
    "66": "financial",
    # Real estate: SIC division 68 -> mapped to financial
    "68": "financial",
    # Professional, scientific and technical: SIC divisions 69 to 75
    "69": "professional",
    "70": "professional",
    "71": "professional",
    "72": "professional",
    "73": "professional",
    "74": "professional",
    "75": "professional",
    # Administrative and support: SIC divisions 77 to 82
    "77": "admin_support",
    "78": "admin_support",
    "79": "admin_support",
    "80": "admin_support",
    "81": "admin_support",
    "82": "admin_support",
    # Public administration and defence: SIC division 84
    "84": "public_admin",
    # Education: SIC division 85
    "85": "education",
    # Health and social work: SIC divisions 86 to 88
    "86": "health",
    "87": "health",
    "88": "health",
    # Arts, entertainment and recreation: SIC divisions 90 to 93
    "90": "other_services",
    "91": "other_services",
    "92": "other_services",
    "93": "other_services",
    # Other service activities: SIC divisions 94 to 96
    "94": "other_services",
    "95": "other_services",
    "96": "other_services",
}

# ---------------------------------------------------------------------------
# Pydantic model — mirrors the Polars schema for LLM / API use
# ---------------------------------------------------------------------------


class CompanyFiling(BaseModel):
    """One filing record, mapping 1:1 to the 39-column Polars schema.

    Used as the structured output target for LLM-based PDF extraction,
    for API response validation, and for DuckDB column mapping.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    # Run-level
    run_code: str | None = None
    # Company-at-date
    company_id: str
    date: datetime.date | None = None
    file_type: str | None = None
    taxonomy: str | None = None
    balance_sheet_date: datetime.date | None = None
    companies_house_registered_number: str | None = None
    entity_current_legal_name: str | None = None
    company_dormant: bool | None = None
    average_number_employees_during_period: Decimal | None = None
    # Period-level
    period_start: datetime.date | None = None
    period_end: datetime.date | None = None
    # Balance sheet
    tangible_fixed_assets: Decimal | None = None
    debtors: Decimal | None = None
    cash_bank_in_hand: Decimal | None = None
    current_assets: Decimal | None = None
    creditors_due_within_one_year: Decimal | None = None
    creditors_due_after_one_year: Decimal | None = None
    net_current_assets_liabilities: Decimal | None = None
    total_assets_less_current_liabilities: Decimal | None = None
    net_assets_liabilities_including_pension_asset_liability: Decimal | None = None
    called_up_share_capital: Decimal | None = None
    profit_loss_account_reserve: Decimal | None = None
    shareholder_funds: Decimal | None = None
    # P&L
    turnover_gross_operating_revenue: Decimal | None = None
    other_operating_income: Decimal | None = None
    cost_sales: Decimal | None = None
    gross_profit_loss: Decimal | None = None
    administrative_expenses: Decimal | None = None
    raw_materials_consumables: Decimal | None = None
    staff_costs: Decimal | None = None
    depreciation_other_amounts_written_off_tangible_intangible_fixed_assets: (
        Decimal | None
    ) = None
    other_operating_charges_format2: Decimal | None = None
    operating_profit_loss: Decimal | None = None
    profit_loss_on_ordinary_activities_before_tax: Decimal | None = None
    tax_on_profit_or_loss_on_ordinary_activities: Decimal | None = None
    profit_loss_for_period: Decimal | None = None
    error: str | None = None
    zip_url: str | None = None

    def to_polars_row(self) -> dict[str, Any]:
        """Convert to a dict compatible with ``pl.DataFrame`` construction."""
        return self.model_dump()

    @classmethod
    def polars_schema(cls) -> dict[str, pl.DataType]:
        """Return the canonical Polars schema."""
        return dict(COMPANIES_HOUSE_SCHEMA)

    @classmethod
    def duckdb_ddl(cls, table_name: str = "filings") -> str:
        """Generate a CREATE TABLE statement for DuckDB."""
        _type_map: dict[str, str] = {}
        for col_name, dtype in COMPANIES_HOUSE_SCHEMA.items():
            if dtype == pl.Utf8:
                _type_map[col_name] = "VARCHAR"
            elif dtype == pl.Date:
                _type_map[col_name] = "DATE"
            elif dtype == pl.Boolean:
                _type_map[col_name] = "BOOLEAN"
            elif isinstance(dtype, pl.Decimal):
                _type_map[col_name] = f"DECIMAL({dtype.precision}, {dtype.scale})"
            else:
                _type_map[col_name] = "VARCHAR"

        pk_cols = ", ".join(DEDUP_COLUMNS)
        col_defs = ",\n    ".join(
            f"{name} {sql_type}" for name, sql_type in _type_map.items()
        )
        return (
            f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            f"    {col_defs},\n"
            f"    PRIMARY KEY ({pk_cols})\n"
            f");"
        )
