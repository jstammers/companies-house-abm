"""Integration tests verifying real XBRL files parse into the expected schema.

These tests use real XBRL filings extracted from Companies House bulk-download
ZIPs (stored in tests/fixtures/) as fixtures, parsing them with the live
stream_read_xbrl_zip library and asserting that the resulting DataFrame matches
COMPANIES_HOUSE_SCHEMA — both structurally (column names, dtypes, order) and
value-wise (field values agree with what the same file produced when it was
ingested into the production parquet).

Fixtures
--------
Prod224_0012_01873499_20230131.html
    Inline iXBRL (HTML) — Exel Computer Systems PLC, FY ending 2023-01-31.
    Extracted from: Accounts_Monthly_Data-April2023.zip
    Format: modern iXBRL / HTML (post-2013)

Prod224_9953_00003006_20090731.xml
    Old-style XBRL (XML) — Nalder and Nalder Limited, FY ending 2009-07-31.
    Extracted from: Accounts_Monthly_Data-April2010.zip
    Format: legacy UK-GAAP XML (pre-2014)

These cover both XBRL format variants handled by stream_read_xbrl_zip.
"""

from __future__ import annotations

import datetime
import zipfile
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from companies_house.ingest.xbrl import ingest_from_zips
from companies_house.schema import COMPANIES_HOUSE_SCHEMA

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# iXBRL / HTML format — Exel Computer Systems PLC
EXEL_HTML = FIXTURES_DIR / "Prod224_0012_01873499_20230131.html"
EXEL_COMPANY_ID = "01873499"

# Legacy XML format — Nalder and Nalder Limited
NALDER_XML = FIXTURES_DIR / "Prod224_9953_00003006_20090731.xml"
NALDER_COMPANY_ID = "00003006"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_zip(fixture_path: Path, zip_path: Path) -> Path:
    """Write *fixture_path* into a fresh ZIP at *zip_path* and return it."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(fixture_path, fixture_path.name)
    return zip_path


# ---------------------------------------------------------------------------
# Schema-level tests (apply to both formats)
# ---------------------------------------------------------------------------


class TestSchemaConformance:
    """Verify that ingest_from_zips always produces COMPANIES_HOUSE_SCHEMA."""

    @pytest.mark.parametrize(
        "fixture_file",
        [EXEL_HTML, NALDER_XML],
        ids=["html-ixbrl", "xml-legacy"],
    )
    def test_schema_matches_exactly(self, fixture_file: Path, tmp_path: Path):
        """Parsed DataFrame schema must be identical to COMPANIES_HOUSE_SCHEMA."""
        zip_path = _make_zip(fixture_file, tmp_path / "test.zip")
        df = ingest_from_zips([zip_path])

        assert df.schema == COMPANIES_HOUSE_SCHEMA, (
            f"Schema mismatch for {fixture_file.name}.\n"
            f"Expected: {COMPANIES_HOUSE_SCHEMA}\n"
            f"Got:      {df.schema}"
        )

    @pytest.mark.parametrize(
        "fixture_file",
        [EXEL_HTML, NALDER_XML],
        ids=["html-ixbrl", "xml-legacy"],
    )
    def test_column_names_and_order(self, fixture_file: Path, tmp_path: Path):
        """Column names must match COMPANIES_HOUSE_SCHEMA in the exact order."""
        zip_path = _make_zip(fixture_file, tmp_path / "test.zip")
        df = ingest_from_zips([zip_path])

        expected_cols = list(COMPANIES_HOUSE_SCHEMA.keys())
        assert df.columns == expected_cols, (
            f"Column name/order mismatch for {fixture_file.name}.\n"
            f"Expected: {expected_cols}\n"
            f"Got:      {df.columns}"
        )

    @pytest.mark.parametrize(
        "fixture_file",
        [EXEL_HTML, NALDER_XML],
        ids=["html-ixbrl", "xml-legacy"],
    )
    def test_column_dtypes(self, fixture_file: Path, tmp_path: Path):
        """Every column dtype must match the COMPANIES_HOUSE_SCHEMA declaration."""
        zip_path = _make_zip(fixture_file, tmp_path / "test.zip")
        df = ingest_from_zips([zip_path])

        for col, expected_dtype in COMPANIES_HOUSE_SCHEMA.items():
            actual_dtype = df.schema[col]
            assert actual_dtype == expected_dtype, (
                f"Dtype mismatch on column '{col}' for {fixture_file.name}: "
                f"expected {expected_dtype}, got {actual_dtype}"
            )

    @pytest.mark.parametrize(
        "fixture_file",
        [EXEL_HTML, NALDER_XML],
        ids=["html-ixbrl", "xml-legacy"],
    )
    def test_nonempty(self, fixture_file: Path, tmp_path: Path):
        """Parsing a real fixture must yield at least one row."""
        zip_path = _make_zip(fixture_file, tmp_path / "test.zip")
        df = ingest_from_zips([zip_path])
        assert len(df) > 0, (
            f"Expected rows from {fixture_file.name}, got empty DataFrame"
        )

    @pytest.mark.parametrize(
        "fixture_file",
        [EXEL_HTML, NALDER_XML],
        ids=["html-ixbrl", "xml-legacy"],
    )
    def test_parquet_roundtrip_preserves_schema(
        self, fixture_file: Path, tmp_path: Path
    ):
        """Data written to Parquet and read back must retain COMPANIES_HOUSE_SCHEMA."""
        zip_path = _make_zip(fixture_file, tmp_path / "test.zip")
        df = ingest_from_zips([zip_path])

        pq_path = tmp_path / "out.parquet"
        df.write_parquet(pq_path)
        df_back = pl.read_parquet(pq_path)

        assert df_back.schema == COMPANIES_HOUSE_SCHEMA, (
            f"Schema changed after Parquet round-trip for {fixture_file.name}.\n"
            f"Expected: {COMPANIES_HOUSE_SCHEMA}\n"
            f"Got:      {df_back.schema}"
        )

    @pytest.mark.parametrize(
        "fixture_file",
        [EXEL_HTML, NALDER_XML],
        ids=["html-ixbrl", "xml-legacy"],
    )
    def test_parquet_roundtrip_preserves_values(
        self, fixture_file: Path, tmp_path: Path
    ):
        """Numeric values must survive a Parquet write-read cycle unchanged."""
        zip_path = _make_zip(fixture_file, tmp_path / "test.zip")
        df = ingest_from_zips([zip_path])

        pq_path = tmp_path / "out.parquet"
        df.write_parquet(pq_path)
        df_back = pl.read_parquet(pq_path)

        assert df.equals(df_back), (
            f"Data changed after Parquet round-trip for {fixture_file.name}"
        )


# ---------------------------------------------------------------------------
# HTML iXBRL — Exel Computer Systems PLC (01873499, FY 2023-01-31)
# Values cross-checked against production parquet rows.
# ---------------------------------------------------------------------------


class TestExelHTMLFixture:
    """Field-value assertions for the Exel Computer Systems iXBRL filing.

    Expected values are drawn from the production parquet for company 01873499,
    zip_url = 'data/Accounts_Monthly_Data-April2023.zip'.
    """

    @pytest.fixture()
    def exel_df(self, tmp_path: Path) -> pl.DataFrame:
        zip_path = _make_zip(EXEL_HTML, tmp_path / "April2023.zip")
        return ingest_from_zips([zip_path])

    def test_row_count(self, exel_df: pl.DataFrame):
        """Exel filing produces exactly 5 rows (3 instant + 2 duration periods)."""
        assert len(exel_df) == 5

    def test_file_type_is_html(self, exel_df: pl.DataFrame):
        assert (exel_df["file_type"] == "html").all()

    def test_company_id(self, exel_df: pl.DataFrame):
        assert (exel_df["company_id"] == EXEL_COMPANY_ID).all()

    def test_entity_name(self, exel_df: pl.DataFrame):
        assert (
            exel_df["entity_current_legal_name"] == "EXEL COMPUTER SYSTEMS PLC"
        ).all()

    def test_balance_sheet_date(self, exel_df: pl.DataFrame):

        assert (exel_df["balance_sheet_date"] == datetime.date(2023, 1, 31)).all()

    def test_run_code(self, exel_df: pl.DataFrame):
        assert (exel_df["run_code"] == "Prod224_0012").all()

    def test_not_dormant(self, exel_df: pl.DataFrame):
        assert (exel_df["company_dormant"] == False).all()  # noqa: E712

    def test_employees(self, exel_df: pl.DataFrame):
        """All rows carry the employee headcount (89)."""
        non_null = exel_df["average_number_employees_during_period"].drop_nulls()
        assert len(non_null) > 0
        assert (non_null == Decimal("89")).all()

    # --- Current year P&L row (period_start=2022-02-01, period_end=2023-01-31) ---

    def test_current_year_turnover(self, exel_df: pl.DataFrame):
        """Current-year turnover must match the parquet value exactly."""

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert len(row) == 1
        assert row["turnover_gross_operating_revenue"][0] == Decimal("9281499")

    def test_current_year_profit_for_period(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["profit_loss_for_period"][0] == Decimal("1468342")

    def test_current_year_profit_before_tax(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["profit_loss_on_ordinary_activities_before_tax"][0] == Decimal(
            "1496056"
        )

    def test_current_year_tax(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["tax_on_profit_or_loss_on_ordinary_activities"][0] == Decimal(
            "27714"
        )

    def test_current_year_gross_profit(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["gross_profit_loss"][0] == Decimal("3467967")

    def test_current_year_cost_of_sales(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["cost_sales"][0] == Decimal("5813532")

    def test_current_year_operating_profit(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["operating_profit_loss"][0] == Decimal("1488283")

    def test_current_year_admin_expenses(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["administrative_expenses"][0] == Decimal("1979684")

    def test_current_year_staff_costs(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2022, 2, 1))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["staff_costs"][0] == Decimal("5831530")

    # --- Current balance sheet (instant: period_start == period_end == 2023-01-31) ---

    def test_balance_sheet_tangible_assets(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2023, 1, 31))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["tangible_fixed_assets"][0] == Decimal("905613")

    def test_balance_sheet_debtors(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2023, 1, 31))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["debtors"][0] == Decimal("5095688")

    def test_balance_sheet_cash(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2023, 1, 31))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["cash_bank_in_hand"][0] == Decimal("1947590")

    def test_balance_sheet_current_assets(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2023, 1, 31))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["current_assets"][0] == Decimal("7046278")

    def test_balance_sheet_net_current_assets(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2023, 1, 31))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        assert row["net_current_assets_liabilities"][0] == Decimal("1766208")

    def test_balance_sheet_net_assets(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2023, 1, 31))
            & (pl.col("period_end") == datetime.date(2023, 1, 31))
        )
        val = row["net_assets_liabilities_including_pension_asset_liability"][0]
        assert val == Decimal("2649078")

    def test_no_errors(self, exel_df: pl.DataFrame):
        """None of the rows must carry a parse error."""
        assert exel_df["error"].is_null().all()

    # --- Prior year comparative rows ---

    def test_prior_year_pl_row_exists(self, exel_df: pl.DataFrame):
        """Prior-year P&L row (FY ending 2022-01-31) must be present."""

        rows = exel_df.filter(
            (pl.col("period_start") == datetime.date(2021, 2, 1))
            & (pl.col("period_end") == datetime.date(2022, 1, 31))
        )
        assert len(rows) == 1

    def test_prior_year_turnover(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2021, 2, 1))
            & (pl.col("period_end") == datetime.date(2022, 1, 31))
        )
        assert row["turnover_gross_operating_revenue"][0] == Decimal("9129706")

    def test_prior_year_profit_for_period(self, exel_df: pl.DataFrame):

        row = exel_df.filter(
            (pl.col("period_start") == datetime.date(2021, 2, 1))
            & (pl.col("period_end") == datetime.date(2022, 1, 31))
        )
        assert row["profit_loss_for_period"][0] == Decimal("1251533")


# ---------------------------------------------------------------------------
# Legacy XML — Nalder and Nalder Limited (00003006, FY 2009-07-31)
# Values cross-checked against production parquet rows.
# ---------------------------------------------------------------------------


class TestNalderXMLFixture:
    """Field-value assertions for the Nalder and Nalder XML XBRL filing.

    Expected values are drawn from the production parquet for company 00003006,
    zip_url = 'data/Accounts_Monthly_Data-April2010.zip'.
    """

    @pytest.fixture()
    def nalder_df(self, tmp_path: Path) -> pl.DataFrame:
        zip_path = _make_zip(NALDER_XML, tmp_path / "April2010.zip")
        return ingest_from_zips([zip_path])

    def test_row_count(self, nalder_df: pl.DataFrame):
        """XML filing produces exactly 2 rows (current + prior year instant)."""
        assert len(nalder_df) == 2

    def test_file_type_is_xml(self, nalder_df: pl.DataFrame):
        assert (nalder_df["file_type"] == "xml").all()

    def test_company_id(self, nalder_df: pl.DataFrame):
        assert (nalder_df["company_id"] == NALDER_COMPANY_ID).all()

    def test_entity_name(self, nalder_df: pl.DataFrame):
        assert (
            nalder_df["entity_current_legal_name"] == "NALDER AND NALDER LIMITED"
        ).all()

    def test_run_code(self, nalder_df: pl.DataFrame):
        assert (nalder_df["run_code"] == "Prod224_9953").all()

    def test_not_dormant(self, nalder_df: pl.DataFrame):
        assert (nalder_df["company_dormant"] == False).all()  # noqa: E712

    def test_taxonomy_is_old_gaap(self, nalder_df: pl.DataFrame):
        """Old XML filings report a GAAP taxonomy URI."""
        assert (
            nalder_df["taxonomy"] == "http://www.xbrl.org/uk/fr/gaap/pt/2004-12-01"
        ).all()

    def test_balance_sheet_date(self, nalder_df: pl.DataFrame):

        assert (nalder_df["balance_sheet_date"] == datetime.date(2009, 7, 31)).all()

    # --- Current year row (period = 2009-07-31 instant) ---

    def test_current_debtors(self, nalder_df: pl.DataFrame):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        assert row["debtors"][0] == Decimal("25853")

    def test_current_current_assets(self, nalder_df: pl.DataFrame):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        assert row["current_assets"][0] == Decimal("25853")

    def test_current_net_current_assets(self, nalder_df: pl.DataFrame):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        assert row["net_current_assets_liabilities"][0] == Decimal("25853")

    def test_current_total_assets_less_current_liabilities(
        self, nalder_df: pl.DataFrame
    ):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        assert row["total_assets_less_current_liabilities"][0] == Decimal("25853")

    def test_current_net_assets(self, nalder_df: pl.DataFrame):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        val = row["net_assets_liabilities_including_pension_asset_liability"][0]
        assert val == Decimal("25853")

    def test_current_called_up_share_capital(self, nalder_df: pl.DataFrame):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        assert row["called_up_share_capital"][0] == Decimal("25000")

    def test_current_profit_loss_reserve(self, nalder_df: pl.DataFrame):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        assert row["profit_loss_account_reserve"][0] == Decimal("853")

    def test_current_shareholder_funds(self, nalder_df: pl.DataFrame):

        row = nalder_df.filter(pl.col("period_start") == datetime.date(2009, 7, 31))
        assert row["shareholder_funds"][0] == Decimal("25853")

    def test_turnover_is_null_for_xml_filing(self, nalder_df: pl.DataFrame):
        """Nalder is a balance-sheet-only filing; P&L fields must be null."""
        assert nalder_df["turnover_gross_operating_revenue"].is_null().all()
        assert nalder_df["profit_loss_for_period"].is_null().all()

    def test_prior_year_row_present(self, nalder_df: pl.DataFrame):
        """Prior comparative period (2008-07-31 instant) must appear."""

        rows = nalder_df.filter(pl.col("period_start") == datetime.date(2008, 7, 31))
        assert len(rows) == 1

    def test_no_errors(self, nalder_df: pl.DataFrame):
        assert nalder_df["error"].is_null().all()

    # --- Decimal precision check ---

    def test_decimal_precision(self, nalder_df: pl.DataFrame):
        """Decimal columns must use Decimal(20, 2) — i.e. two decimal places."""
        for col, dtype in nalder_df.schema.items():
            if isinstance(dtype, pl.Decimal):
                assert dtype.precision == 20, f"{col}: expected precision 20"
                assert dtype.scale == 2, f"{col}: expected scale 2"
