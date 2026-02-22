"""Tests for the XBRL ingestion ETL pipeline."""

from __future__ import annotations

import datetime
from contextlib import contextmanager
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import patch
from zipfile import ZipFile

import polars as pl
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

from companies_house_abm.cli import app
from companies_house_abm.ingest import (
    COMPANIES_HOUSE_SCHEMA,
    DEDUP_COLUMNS,
    _zip_bytes_iter,
    deduplicate,
    infer_start_date,
    ingest_from_stream,
    ingest_from_zips,
    merge_and_write,
)

# NO_COLOR=1 prevents ANSI colour codes. FORCE_COLOR=None *deletes* the key
# from os.environ during each test invocation (Click CliRunner treats a None
# value as "unset this variable"). This is necessary because CI sets
# FORCE_COLOR=1 globally; when FORCE_COLOR is merely set to "" Rich still sees
# the key present in os.environ via `if "FORCE_COLOR" in os.environ`, which
# some code paths use to force colour output regardless of the value, splitting
# option names like --zip-dir across ANSI escape sequences and breaking
# substring assertions such as `"zip-dir" in result.stdout`.
runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COLUMNS = tuple(COMPANIES_HOUSE_SCHEMA.keys())


def _make_row(**overrides: object) -> tuple:
    """Build a row tuple with sensible defaults, applying overrides by column name."""
    defaults: dict[str, object] = {
        "run_code": "R001",
        "company_id": "00000001",
        "date": datetime.date(2024, 1, 15),
        "file_type": "html",
        "taxonomy": "uk-gaap",
        "balance_sheet_date": datetime.date(2023, 12, 31),
        "companies_house_registered_number": "00000001",
        "entity_current_legal_name": "Test Co",
        "company_dormant": False,
        "average_number_employees_during_period": Decimal("10.00"),
        "period_start": datetime.date(2023, 1, 1),
        "period_end": datetime.date(2023, 12, 31),
        "tangible_fixed_assets": Decimal("1000.00"),
        "debtors": Decimal("500.00"),
        "cash_bank_in_hand": Decimal("200.00"),
        "current_assets": Decimal("700.00"),
        "creditors_due_within_one_year": Decimal("300.00"),
        "creditors_due_after_one_year": Decimal("100.00"),
        "net_current_assets_liabilities": Decimal("400.00"),
        "total_assets_less_current_liabilities": Decimal("1400.00"),
        "net_assets_liabilities_including_pension_asset_liability": Decimal("1300.00"),
        "called_up_share_capital": Decimal("100.00"),
        "profit_loss_account_reserve": Decimal("1200.00"),
        "shareholder_funds": Decimal("1300.00"),
        "turnover_gross_operating_revenue": Decimal("5000.00"),
        "other_operating_income": Decimal("0.00"),
        "cost_sales": Decimal("2000.00"),
        "gross_profit_loss": Decimal("3000.00"),
        "administrative_expenses": Decimal("500.00"),
        "raw_materials_consumables": Decimal("0.00"),
        "staff_costs": Decimal("1000.00"),
        "depreciation_other_amounts_written_off_tangible_intangible_fixed_assets": Decimal(  # noqa: E501
            "200.00"
        ),
        "other_operating_charges_format2": Decimal("0.00"),
        "operating_profit_loss": Decimal("1300.00"),
        "profit_loss_on_ordinary_activities_before_tax": Decimal("1300.00"),
        "tax_on_profit_or_loss_on_ordinary_activities": Decimal("260.00"),
        "profit_loss_for_period": Decimal("1040.00"),
        "error": None,
        "zip_url": "http://example.com/test.zip",
    }
    defaults.update(overrides)
    return tuple(defaults[col] for col in _COLUMNS)


def _make_df(rows: list[tuple]) -> pl.DataFrame:
    """Build a DataFrame from row tuples using the standard schema."""
    return pl.DataFrame(rows, orient="row", schema=COMPANIES_HOUSE_SCHEMA)


@contextmanager
def _mock_stream_read_xbrl_zip(rows: list[tuple]):
    """Mock stream_read_xbrl_zip to yield known rows."""

    @contextmanager
    def fake_zip(zip_bytes_iter, zip_url=None):
        yield (_COLUMNS, iter(rows))

    with patch("companies_house_abm.ingest.stream_read_xbrl_zip", fake_zip):
        yield


@contextmanager
def _mock_stream_read_xbrl_zip_error():
    """Mock stream_read_xbrl_zip to raise an error."""

    @contextmanager
    def fake_zip(zip_bytes_iter, zip_url=None):
        raise RuntimeError("Corrupt ZIP")
        yield  # pragma: no cover

    with patch("companies_house_abm.ingest.stream_read_xbrl_zip", fake_zip):
        yield


@contextmanager
def _mock_stream_read_xbrl_sync(
    rows: list[tuple], *, capture_kwargs: dict | None = None
):
    """Mock stream_read_xbrl_sync to yield known rows."""

    @contextmanager
    def fake_sync(**kwargs):
        if capture_kwargs is not None:
            capture_kwargs.update(kwargs)

        def batches():
            yield (datetime.date(2024, 1, 1), datetime.date(2024, 1, 31)), iter(rows)

        yield (_COLUMNS, batches())

    with patch("companies_house_abm.ingest.stream_read_xbrl_sync", fake_sync):
        yield


# ---------------------------------------------------------------------------
# TestSchema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_column_count(self):
        assert len(COMPANIES_HOUSE_SCHEMA) == 39

    def test_column_names_match(self):
        from stream_read_xbrl import _COLUMNS as LIB_COLUMNS

        assert tuple(COMPANIES_HOUSE_SCHEMA.keys()) == LIB_COLUMNS

    def test_date_columns_are_date_type(self):
        for col in ("date", "balance_sheet_date", "period_start", "period_end"):
            assert COMPANIES_HOUSE_SCHEMA[col] == pl.Date

    def test_dedup_columns_exist_in_schema(self):
        for col in DEDUP_COLUMNS:
            assert col in COMPANIES_HOUSE_SCHEMA


# ---------------------------------------------------------------------------
# TestDeduplicate
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_exact_duplicates_removed(self):
        row = _make_row()
        df = _make_df([row, row])
        result = deduplicate(df)
        assert len(result) == 1

    def test_keep_last_on_key_collision(self):
        row_old = _make_row(entity_current_legal_name="Old Name")
        row_new = _make_row(entity_current_legal_name="New Name")
        df = _make_df([row_old, row_new])
        result = deduplicate(df)
        assert len(result) == 1
        assert result["entity_current_legal_name"][0] == "New Name"

    def test_unique_rows_preserved(self):
        row_a = _make_row(company_id="A")
        row_b = _make_row(company_id="B")
        df = _make_df([row_a, row_b])
        result = deduplicate(df)
        assert len(result) == 2

    def test_empty_dataframe(self):
        df = pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
        result = deduplicate(df)
        assert len(result) == 0
        assert result.schema == df.schema


# ---------------------------------------------------------------------------
# TestInferStartDate
# ---------------------------------------------------------------------------


class TestInferStartDate:
    def test_max_date_from_parquet(self, tmp_path: Path):
        dates = [datetime.date(2024, 1, 1), datetime.date(2024, 6, 15)]
        rows = [_make_row(date=d) for d in dates]
        df = _make_df(rows)
        path = tmp_path / "data.parquet"
        df.write_parquet(path)
        assert infer_start_date(path) == datetime.date(2024, 6, 15)

    def test_missing_file_returns_none(self, tmp_path: Path):
        assert infer_start_date(tmp_path / "nonexistent.parquet") is None

    def test_empty_parquet_returns_none(self, tmp_path: Path):
        df = pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
        path = tmp_path / "empty.parquet"
        df.write_parquet(path)
        assert infer_start_date(path) is None


# ---------------------------------------------------------------------------
# TestZipBytesIter
# ---------------------------------------------------------------------------


class TestZipBytesIter:
    def test_reads_file_in_chunks(self, tmp_path: Path):
        content = b"x" * 200_000
        path = tmp_path / "test.zip"
        path.write_bytes(content)
        result = b"".join(_zip_bytes_iter(path))
        assert result == content


# ---------------------------------------------------------------------------
# TestIngestFromZips
# ---------------------------------------------------------------------------


class TestIngestFromZips:
    def test_processes_zip_files(self, tmp_path: Path):
        # Create a dummy zip file (content doesn't matter since we mock)
        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("dummy.txt", "dummy")

        rows = [_make_row(company_id="A"), _make_row(company_id="B")]
        with _mock_stream_read_xbrl_zip(rows):
            result = ingest_from_zips([zip_path])
        assert len(result) == 2

    def test_corrupt_zip_skipped(self, tmp_path: Path):
        zip_path = tmp_path / "bad.zip"
        zip_path.write_bytes(b"not a zip")
        with _mock_stream_read_xbrl_zip_error():
            result = ingest_from_zips([zip_path])
        assert len(result) == 0
        assert result.schema == COMPANIES_HOUSE_SCHEMA

    def test_empty_list_returns_empty_df(self):
        result = ingest_from_zips([])
        assert len(result) == 0
        assert result.schema == COMPANIES_HOUSE_SCHEMA


# ---------------------------------------------------------------------------
# TestIngestFromStream
# ---------------------------------------------------------------------------


class TestIngestFromStream:
    def test_rows_collected(self):
        rows = [_make_row(company_id="X"), _make_row(company_id="Y")]
        with _mock_stream_read_xbrl_sync(rows):
            result = ingest_from_stream()
        assert len(result) == 2

    def test_start_date_forwarded(self):
        captured: dict = {}
        rows = [_make_row()]
        with _mock_stream_read_xbrl_sync(rows, capture_kwargs=captured):
            ingest_from_stream(start_date=datetime.date(2024, 6, 1))
        assert captured["ingest_data_after_date"] == datetime.date(2024, 6, 1)

    def test_no_start_date_uses_min(self):
        captured: dict = {}
        rows = [_make_row()]
        with _mock_stream_read_xbrl_sync(rows, capture_kwargs=captured):
            ingest_from_stream(start_date=None)
        assert captured["ingest_data_after_date"] == datetime.date(
            datetime.MINYEAR, 1, 1
        )


# ---------------------------------------------------------------------------
# TestMergeAndWrite
# ---------------------------------------------------------------------------


class TestMergeAndWrite:
    def test_new_data_only(self, tmp_path: Path):
        output = tmp_path / "out.parquet"
        df = _make_df([_make_row(company_id="A")])
        result = merge_and_write(df, output)
        assert len(result) == 1
        assert output.exists()

    def test_merge_with_existing_dedup(self, tmp_path: Path):
        existing_path = tmp_path / "existing.parquet"
        output = tmp_path / "out.parquet"
        # Same row in both - should be deduped
        row = _make_row(company_id="A")
        _make_df([row]).write_parquet(existing_path)
        result = merge_and_write(_make_df([row]), output, existing_path=existing_path)
        assert len(result) == 1

    def test_merge_with_new_rows(self, tmp_path: Path):
        existing_path = tmp_path / "existing.parquet"
        output = tmp_path / "out.parquet"
        _make_df([_make_row(company_id="A")]).write_parquet(existing_path)
        result = merge_and_write(
            _make_df([_make_row(company_id="B")]),
            output,
            existing_path=existing_path,
        )
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestCLIIngest
# ---------------------------------------------------------------------------


class TestCLIIngest:
    def test_zip_mode(self, tmp_path: Path):
        zip_path = tmp_path / "data.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("dummy.txt", "dummy")
        output = tmp_path / "out.parquet"

        rows = [_make_row()]
        with _mock_stream_read_xbrl_zip(rows):
            result = runner.invoke(
                app,
                ["ingest", "-z", str(tmp_path), "-o", str(output)],
            )
        assert result.exit_code == 0, result.stdout
        assert "Done" in result.stdout

    def test_stream_mode(self, tmp_path: Path):
        output = tmp_path / "out.parquet"
        rows = [_make_row()]
        with _mock_stream_read_xbrl_sync(rows):
            result = runner.invoke(
                app,
                ["ingest", "-o", str(output)],
            )
        assert result.exit_code == 0, result.stdout
        assert "Done" in result.stdout

    def test_invalid_dir(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["ingest", "-z", str(tmp_path / "nonexistent")],
        )
        assert result.exit_code != 0

    def test_explicit_start_date(self, tmp_path: Path):
        output = tmp_path / "out.parquet"
        captured: dict = {}
        rows = [_make_row()]
        with _mock_stream_read_xbrl_sync(rows, capture_kwargs=captured):
            result = runner.invoke(
                app,
                ["ingest", "-o", str(output), "-s", "2024-06-01"],
            )
        assert result.exit_code == 0, result.stdout
        assert captured["ingest_data_after_date"] == datetime.date(2024, 6, 1)

    def test_help(self):
        result = runner.invoke(app, ["ingest", "--help"], color=False)
        assert result.exit_code == 0
        assert "output" in result.stdout
        assert "zip-dir" in result.stdout
        assert "start-date" in result.stdout
