"""ETL pipeline for Companies House XBRL data ingestion."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import polars as pl
from stream_read_xbrl import stream_read_xbrl_sync, stream_read_xbrl_zip

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from datetime import date
    from pathlib import Path

logger = logging.getLogger(__name__)

_DECIMAL = pl.Decimal(20, 2)

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


def infer_start_date(parquet_path: Path) -> date | None:
    """Scan parquet for max `date` column value.

    Returns None if the file is missing or empty.
    """
    if not parquet_path.exists():
        return None
    try:
        result = pl.scan_parquet(parquet_path).select(pl.col("date").max()).collect()
        if result.is_empty() or result[0, 0] is None:
            return None
        return result[0, 0]
    except Exception:
        logger.warning("Could not read parquet at %s", parquet_path, exc_info=True)
        return None


def deduplicate(df: pl.DataFrame) -> pl.DataFrame:
    """Remove duplicate rows, keeping the last occurrence."""
    return df.unique(subset=DEDUP_COLUMNS, keep="last", maintain_order=True)


def _zip_bytes_iter(zip_path: Path) -> Generator[bytes]:
    """Yield 64KB chunks from a local ZIP file."""
    chunk_size = 64 * 1024
    with zip_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def ingest_from_zips(zip_paths: Sequence[Path]) -> pl.DataFrame:
    """Process local ZIP files via stream_read_xbrl_zip.

    Corrupt or unreadable ZIPs are logged and skipped.
    """
    frames: list[pl.DataFrame] = []
    for zip_path in zip_paths:
        try:
            with stream_read_xbrl_zip(
                _zip_bytes_iter(zip_path), zip_url=str(zip_path)
            ) as (_columns, rows):
                df = pl.DataFrame(
                    list(rows),
                    orient="row",
                    schema=COMPANIES_HOUSE_SCHEMA,
                )
                frames.append(df)
                logger.info("Ingested %d rows from %s", len(df), zip_path)
        except Exception:
            logger.warning("Skipping corrupt ZIP: %s", zip_path, exc_info=True)
    if not frames:
        return pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
    return pl.concat(frames)


def ingest_from_stream(*, start_date: date | None = None) -> pl.DataFrame:
    """Download and ingest XBRL data from Companies House.

    If start_date is provided, only data after that date is ingested.
    """
    import datetime

    if start_date is not None:
        after_date = start_date
    else:
        after_date = datetime.date(datetime.MINYEAR, 1, 1)

    frames: list[pl.DataFrame] = []
    with stream_read_xbrl_sync(
        ingest_data_after_date=after_date,
    ) as (_columns, date_range_and_rows):
        for (batch_start, batch_end), rows in date_range_and_rows:
            df = pl.DataFrame(
                list(rows),
                orient="row",
                schema=COMPANIES_HOUSE_SCHEMA,
            )
            frames.append(df)
            logger.info(
                "Ingested %d rows for %s to %s",
                len(df),
                batch_start,
                batch_end,
            )
    if not frames:
        return pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
    return pl.concat(frames)


def merge_and_write(
    new_data: pl.DataFrame,
    output_path: Path,
    *,
    existing_path: Path | None = None,
) -> pl.DataFrame:
    """Concat with existing parquet, deduplicate, and write."""
    if existing_path is not None and existing_path.exists():
        existing = pl.read_parquet(existing_path)
        combined = pl.concat([existing, new_data])
    else:
        combined = new_data

    result = deduplicate(combined)
    result.write_parquet(output_path)
    logger.info("Wrote %d rows to %s", len(result), output_path)
    return result
