"""Tests for the firm distributions module.

Tests cover:
- SIC code → ABM sector mapping
- Data loading and cleaning
- Data profiling
- Distribution fitting
- Sector/year parameter computation
- I/O (YAML and JSON serialisation)
- CLI integration
- Pipeline end-to-end
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from companies_house_abm.data_sources.firm_distributions import (
    CANDIDATE_DISTRIBUTIONS,
    DEBT_COLUMNS,
    FIRM_FIELD_MAP,
    MIN_OBSERVATIONS,
    OUTLIER_QUANTILES,
    SIC_TO_SECTOR,
    DataProfile,
    FieldProfile,
    FirmDistributionSummary,
    FittedDistribution,
    SectorYearParameters,
    _distribution_param_names,
    _financial_year,
    assign_sectors,
    build_summary,
    compute_sector_year_parameters,
    fit_distribution,
    load_accounts,
    map_sic_to_sector,
    profile_accounts,
    profile_field,
    run_profile_pipeline,
    save_parameters_json,
    save_parameters_yaml,
)

# =====================================================================
# Fixtures
# =====================================================================

_DECIMAL = pl.Decimal(20, 2)


def _make_accounts_df(
    n: int = 200,
    *,
    include_dormant: bool = False,
    include_errors: bool = False,
) -> pl.DataFrame:
    """Create a synthetic accounts DataFrame for testing.

    Generates *n* rows with realistic-ish financial data.
    """
    import numpy as np

    rng = np.random.default_rng(42)

    base_year = 2020
    years = rng.integers(base_year - 3, base_year + 3, size=n)
    months = rng.integers(1, 13, size=n)
    days = [1] * n

    rows: dict[str, list[object]] = {
        "run_code": [f"run_{i}" for i in range(n)],
        "company_id": [f"company_{i % (n // 2 + 1)}" for i in range(n)],
        "date": [
            date(int(y), int(m), 1) for y, m, _ in zip(years, months, days, strict=True)
        ],
        "file_type": ["xml"] * n,
        "taxonomy": ["full"] * n,
        "balance_sheet_date": [
            date(int(y), int(m), 1) for y, m, _ in zip(years, months, days, strict=True)
        ],
        "companies_house_registered_number": [f"{i:08d}" for i in range(n)],
        "entity_current_legal_name": [f"Company {i}" for i in range(n)],
        "company_dormant": [False] * n,
        "average_number_employees_during_period": [
            float(max(1, int(v))) for v in rng.lognormal(2, 1, n)
        ],
        "period_start": [date(int(y), 1, 1) for y in years],
        "period_end": [date(int(y), 12, 31) for y in years],
        "tangible_fixed_assets": [float(max(0, v)) for v in rng.lognormal(10, 2, n)],
        "debtors": [None] * n,
        "cash_bank_in_hand": [float(max(0, v)) for v in rng.lognormal(9, 2, n)],
        "current_assets": [float(max(0, v)) for v in rng.lognormal(10, 2, n)],
        "creditors_due_within_one_year": [
            float(max(0, v)) for v in rng.lognormal(9, 1.5, n)
        ],
        "creditors_due_after_one_year": [
            float(max(0, v)) if rng.random() > 0.5 else None
            for v in rng.lognormal(8, 2, n)
        ],
        "net_current_assets_liabilities": [None] * n,
        "total_assets_less_current_liabilities": [None] * n,
        "net_assets_liabilities_including_pension_asset_liability": [None] * n,
        "called_up_share_capital": [None] * n,
        "profit_loss_account_reserve": [None] * n,
        "shareholder_funds": [float(v) for v in rng.normal(50000, 100000, n)],
        "turnover_gross_operating_revenue": [
            float(max(0, v)) if rng.random() > 0.3 else None
            for v in rng.lognormal(11, 2, n)
        ],
        "other_operating_income": [None] * n,
        "cost_sales": [None] * n,
        "gross_profit_loss": [None] * n,
        "administrative_expenses": [None] * n,
        "raw_materials_consumables": [None] * n,
        "staff_costs": [None] * n,
        "depreciation_other_amounts_written_off_tangible_intangible_fixed_assets": [
            None
        ]
        * n,
        "other_operating_charges_format2": [None] * n,
        "operating_profit_loss": [None] * n,
        "profit_loss_on_ordinary_activities_before_tax": [None] * n,
        "tax_on_profit_or_loss_on_ordinary_activities": [None] * n,
        "profit_loss_for_period": [
            float(v) if rng.random() > 0.5 else None
            for v in rng.normal(10000, 50000, n)
        ],
        "error": [None] * n,
        "zip_url": [f"https://example.com/{i}.zip" for i in range(n)],
    }

    if include_dormant:
        rows["company_dormant"][-5:] = [True] * 5

    if include_errors:
        rows["error"][-3:] = ["parse error"] * 3

    # Cast financials to Decimal
    decimal_cols = {
        "average_number_employees_during_period",
        "tangible_fixed_assets",
        "cash_bank_in_hand",
        "current_assets",
        "creditors_due_within_one_year",
        "creditors_due_after_one_year",
        "shareholder_funds",
        "turnover_gross_operating_revenue",
        "profit_loss_for_period",
    }

    schema_overrides = {c: _DECIMAL for c in decimal_cols if c in rows}
    return pl.DataFrame(rows, schema_overrides=schema_overrides)


def _write_test_parquet(path: Path, n: int = 200, **kwargs: object) -> Path:
    """Write a synthetic accounts parquet file for testing."""
    df = _make_accounts_df(n, **kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return path


@pytest.fixture
def accounts_df() -> pl.DataFrame:
    """A ready-to-use accounts DataFrame (not from parquet)."""
    return _make_accounts_df(200)


@pytest.fixture
def parquet_path(tmp_path: Path) -> Path:
    """Write a test parquet and return its path."""
    return _write_test_parquet(tmp_path / "accounts.parquet", n=200)


@pytest.fixture
def parquet_with_dormant(tmp_path: Path) -> Path:
    """Parquet with some dormant companies."""
    return _write_test_parquet(
        tmp_path / "accounts.parquet",
        n=200,
        include_dormant=True,
        include_errors=True,
    )


@pytest.fixture
def sic_csv(tmp_path: Path) -> Path:
    """Write a test SIC code CSV file."""
    sic_path = tmp_path / "sic_codes.csv"
    rows = []
    for i in range(200):
        sic_code = f"{(i % 90) + 1:02d}000"
        rows.append(
            {
                "companies_house_registered_number": f"{i:08d}",
                "sic_code": sic_code,
            }
        )
    pl.DataFrame(rows).write_csv(sic_path)
    return sic_path


@pytest.fixture
def sic_parquet(tmp_path: Path) -> Path:
    """Write a test SIC code parquet file."""
    sic_path = tmp_path / "sic_codes.parquet"
    rows = []
    for i in range(200):
        sic_code = f"{(i % 90) + 1:02d}000"
        rows.append(
            {
                "companies_house_registered_number": f"{i:08d}",
                "sic_code": sic_code,
            }
        )
    pl.DataFrame(rows).write_parquet(sic_path)
    return sic_path


# =====================================================================
# SIC → Sector mapping
# =====================================================================


class TestSICToSector:
    """Tests for SIC code to ABM sector mapping."""

    def test_agriculture(self) -> None:
        assert map_sic_to_sector("01110") == "agriculture"
        assert map_sic_to_sector("02100") == "agriculture"
        assert map_sic_to_sector("03110") == "agriculture"

    def test_manufacturing(self) -> None:
        assert map_sic_to_sector("10110") == "manufacturing"
        assert map_sic_to_sector("25620") == "manufacturing"
        assert map_sic_to_sector("33140") == "manufacturing"

    def test_construction(self) -> None:
        assert map_sic_to_sector("41100") == "construction"
        assert map_sic_to_sector("43990") == "construction"

    def test_wholesale_retail(self) -> None:
        assert map_sic_to_sector("45110") == "wholesale_retail"
        assert map_sic_to_sector("47910") == "wholesale_retail"

    def test_transport(self) -> None:
        assert map_sic_to_sector("49100") == "transport"
        assert map_sic_to_sector("53100") == "transport"

    def test_hospitality(self) -> None:
        assert map_sic_to_sector("55100") == "hospitality"
        assert map_sic_to_sector("56210") == "hospitality"

    def test_information_communication(self) -> None:
        assert map_sic_to_sector("58110") == "information_communication"
        assert map_sic_to_sector("62020") == "information_communication"

    def test_financial(self) -> None:
        assert map_sic_to_sector("64110") == "financial"
        assert map_sic_to_sector("66220") == "financial"
        assert map_sic_to_sector("68100") == "financial"

    def test_professional_services(self) -> None:
        assert map_sic_to_sector("69102") == "professional_services"
        assert map_sic_to_sector("74100") == "professional_services"
        assert map_sic_to_sector("82990") == "professional_services"

    def test_public_admin(self) -> None:
        assert map_sic_to_sector("84110") == "public_admin"

    def test_education(self) -> None:
        assert map_sic_to_sector("85100") == "education"

    def test_health(self) -> None:
        assert map_sic_to_sector("86100") == "health"
        assert map_sic_to_sector("88990") == "health"

    def test_other_services(self) -> None:
        assert map_sic_to_sector("90010") == "other_services"
        assert map_sic_to_sector("96090") == "other_services"

    def test_unknown_code_returns_other_services(self) -> None:
        assert map_sic_to_sector("00000") == "other_services"
        assert map_sic_to_sector("") == "other_services"
        assert map_sic_to_sector("X") == "other_services"

    def test_all_sectors_covered(self) -> None:
        """Every ABM sector appears in the SIC mapping."""
        from companies_house_abm.abm.config import FirmConfig

        expected = set(FirmConfig().sectors)
        mapped = set(SIC_TO_SECTOR.values())
        assert expected == mapped

    def test_sic_to_sector_keys_are_two_digit(self) -> None:
        for key in SIC_TO_SECTOR:
            assert len(key) == 2
            assert key.isdigit()


# =====================================================================
# Constants
# =====================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_firm_field_map_keys(self) -> None:
        expected = {"employees", "turnover", "capital", "cash", "equity"}
        assert set(FIRM_FIELD_MAP.keys()) == expected

    def test_debt_columns(self) -> None:
        assert len(DEBT_COLUMNS) == 2
        assert "creditors_due_within_one_year" in DEBT_COLUMNS
        assert "creditors_due_after_one_year" in DEBT_COLUMNS

    def test_candidate_distributions(self) -> None:
        assert "lognorm" in CANDIDATE_DISTRIBUTIONS
        assert "norm" in CANDIDATE_DISTRIBUTIONS
        assert len(CANDIDATE_DISTRIBUTIONS) >= 3

    def test_min_observations(self) -> None:
        assert MIN_OBSERVATIONS > 0

    def test_outlier_quantiles(self) -> None:
        low, high = OUTLIER_QUANTILES
        assert 0 < low < high < 1


# =====================================================================
# Financial year derivation
# =====================================================================


class TestFinancialYear:
    """Tests for the UK financial year derivation."""

    def test_april_is_current_year(self) -> None:
        df = pl.DataFrame({"d": [date(2023, 4, 1)]})
        result = df.select(_financial_year(pl.col("d")))
        assert result[0, 0] == 2023

    def test_march_is_previous_year(self) -> None:
        df = pl.DataFrame({"d": [date(2023, 3, 31)]})
        result = df.select(_financial_year(pl.col("d")))
        assert result[0, 0] == 2022

    def test_january_is_previous_year(self) -> None:
        df = pl.DataFrame({"d": [date(2023, 1, 15)]})
        result = df.select(_financial_year(pl.col("d")))
        assert result[0, 0] == 2022

    def test_december_is_current_year(self) -> None:
        df = pl.DataFrame({"d": [date(2023, 12, 31)]})
        result = df.select(_financial_year(pl.col("d")))
        assert result[0, 0] == 2023


# =====================================================================
# Data loading
# =====================================================================


class TestLoadAccounts:
    """Tests for loading and cleaning parquet data."""

    def test_loads_parquet(self, parquet_path: Path) -> None:
        lf = load_accounts(parquet_path)
        df = lf.collect()
        assert len(df) > 0
        assert "financial_year" in df.columns
        assert "debt_total" in df.columns

    def test_drops_dormant_by_default(self, parquet_with_dormant: Path) -> None:
        lf_default = load_accounts(parquet_with_dormant)
        lf_keep = load_accounts(parquet_with_dormant, drop_dormant=False)
        assert lf_default.collect().height <= lf_keep.collect().height

    def test_drops_errors_by_default(self, parquet_with_dormant: Path) -> None:
        lf_default = load_accounts(parquet_with_dormant)
        lf_keep = load_accounts(parquet_with_dormant, drop_errors=False)
        assert lf_default.collect().height <= lf_keep.collect().height

    def test_financial_year_column_added(self, parquet_path: Path) -> None:
        df = load_accounts(parquet_path).collect()
        assert "financial_year" in df.columns
        assert df["financial_year"].dtype == pl.Int32

    def test_debt_total_column_added(self, parquet_path: Path) -> None:
        df = load_accounts(parquet_path).collect()
        assert "debt_total" in df.columns
        # Debt should be non-negative where both creditor columns are non-null
        non_null_debt = df.filter(pl.col("debt_total").is_not_null())["debt_total"]
        assert (non_null_debt >= 0).all()

    def test_date_outliers_filtered(self, tmp_path: Path) -> None:
        """Dates outside 1990-2030 should be excluded."""
        df = _make_accounts_df(10)
        # Add a row with a very old date
        old_row = df.head(1).with_columns(
            pl.lit(date(1900, 1, 1)).alias("balance_sheet_date")
        )
        combined = pl.concat([df, old_row])
        path = tmp_path / "old_dates.parquet"
        combined.write_parquet(path)

        result = load_accounts(path).collect()
        dates = result["balance_sheet_date"]
        assert dates.min().year >= 1990  # type: ignore[union-attr]


# =====================================================================
# Sector assignment
# =====================================================================


class TestAssignSectors:
    """Tests for sector assignment."""

    def test_no_sic_file_assigns_other_services(self, parquet_path: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=None)
        df = lf.collect()
        assert "sector" in df.columns
        assert df["sector"].unique().to_list() == ["other_services"]

    def test_csv_sic_file(self, parquet_path: Path, sic_csv: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=sic_csv)
        df = lf.collect()
        assert "sector" in df.columns
        sectors = df["sector"].unique().to_list()
        assert len(sectors) >= 1

    def test_parquet_sic_file(self, parquet_path: Path, sic_parquet: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=sic_parquet)
        df = lf.collect()
        assert "sector" in df.columns

    def test_nonexistent_sic_file_falls_back(self, parquet_path: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=Path("/nonexistent/sic.csv"))
        df = lf.collect()
        assert df["sector"].unique().to_list() == ["other_services"]

    def test_unsupported_sic_format_raises(
        self, parquet_path: Path, tmp_path: Path
    ) -> None:
        bad_path = tmp_path / "sic.xlsx"
        bad_path.write_text("dummy")
        lf = load_accounts(parquet_path)
        with pytest.raises(ValueError, match="Unsupported SIC file format"):
            assign_sectors(lf, sic_path=bad_path)


# =====================================================================
# Data profiling
# =====================================================================


class TestProfileField:
    """Tests for single-field profiling."""

    def test_basic_profile(self) -> None:
        series = pl.Series("test", [1.0, 2.0, 3.0, 4.0, 5.0])
        p = profile_field(series)
        assert p.name == "test"
        assert p.count == 5
        assert p.null_count == 0
        assert p.null_pct == 0.0
        assert p.mean == pytest.approx(3.0)
        assert p.min == pytest.approx(1.0)
        assert p.max == pytest.approx(5.0)

    def test_profile_with_nulls(self) -> None:
        series = pl.Series("nulls", [1.0, None, 3.0, None, 5.0])
        p = profile_field(series)
        assert p.null_count == 2
        assert p.null_pct == pytest.approx(40.0)
        assert p.mean == pytest.approx(3.0)

    def test_all_nulls(self) -> None:
        series = pl.Series("empty", [None, None, None], dtype=pl.Float64)
        p = profile_field(series)
        assert p.null_count == 3
        assert p.mean is None
        assert p.std is None

    def test_outlier_detection(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        values = rng.normal(100, 10, 1000).tolist()
        # Add extreme outliers
        values.extend([1000, -500])
        series = pl.Series("outliers", values)
        p = profile_field(series)
        assert p.outlier_count > 0
        assert p.outlier_low is not None
        assert p.outlier_high is not None
        assert p.outlier_low < p.outlier_high  # type: ignore[operator]

    def test_single_value(self) -> None:
        series = pl.Series("single", [42.0])
        p = profile_field(series)
        assert p.count == 1
        assert p.mean == pytest.approx(42.0)


class TestProfileAccounts:
    """Tests for full dataset profiling."""

    def test_profile_returns_dataprofile(self, parquet_path: Path) -> None:
        df = load_accounts(parquet_path).collect()
        df = df.with_columns(pl.lit("other_services").alias("sector"))
        profile = profile_accounts(df)
        assert isinstance(profile, DataProfile)
        assert profile.total_rows > 0
        assert profile.total_companies > 0

    def test_profile_has_field_profiles(self, parquet_path: Path) -> None:
        df = load_accounts(parquet_path).collect()
        df = df.with_columns(pl.lit("other_services").alias("sector"))
        profile = profile_accounts(df)
        assert len(profile.fields) > 0
        field_names = {f.name for f in profile.fields}
        # Should include at least the core fields
        for col in FIRM_FIELD_MAP.values():
            assert col in field_names

    def test_date_range(self, parquet_path: Path) -> None:
        df = load_accounts(parquet_path).collect()
        profile = profile_accounts(df)
        assert profile.date_range[0] != "N/A"
        assert profile.date_range[1] != "N/A"


# =====================================================================
# Distribution fitting
# =====================================================================


class TestFitDistribution:
    """Tests for statistical distribution fitting."""

    def test_fits_lognormal_data(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        values = rng.lognormal(10, 1, 500)
        series = pl.Series("lognormal_data", values)

        result = fit_distribution(series, "test_field")
        assert result is not None
        assert isinstance(result, FittedDistribution)
        assert result.distribution in CANDIDATE_DISTRIBUTIONS
        assert result.n_observations == 500
        assert result.aic < float("inf")

    def test_fits_normal_data(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        values = rng.normal(1000, 200, 500)
        series = pl.Series("normal_data", values)

        result = fit_distribution(series, "test_field")
        assert result is not None
        assert result.distribution in CANDIDATE_DISTRIBUTIONS

    def test_returns_none_for_insufficient_data(self) -> None:
        series = pl.Series("small", [1.0, 2.0, 3.0])
        result = fit_distribution(series, "test")
        assert result is None

    def test_returns_none_for_empty_series(self) -> None:
        series = pl.Series("empty", [], dtype=pl.Float64)
        result = fit_distribution(series, "test")
        assert result is None

    def test_handles_nulls_gracefully(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        values: list[float | None] = rng.lognormal(5, 1, 100).tolist()
        values.extend([None] * 50)
        series = pl.Series("with_nulls", values)

        result = fit_distribution(series, "test")
        assert result is not None
        assert result.n_observations <= 100

    def test_ks_test_values(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        values = rng.lognormal(5, 0.5, 1000)
        series = pl.Series("ks_test", values)

        result = fit_distribution(series, "test")
        assert result is not None
        assert 0 <= result.ks_statistic <= 1
        assert 0 <= result.ks_pvalue <= 1

    def test_custom_candidates(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        values = rng.normal(100, 20, 200)
        series = pl.Series("custom", values)

        result = fit_distribution(series, "test", candidates=("norm", "expon"))
        assert result is not None
        assert result.distribution in ("norm", "expon")


class TestDistributionParamNames:
    """Tests for parameter name mapping."""

    def test_lognorm_params(self) -> None:
        result = _distribution_param_names("lognorm", (0.5, 0.0, 1.0))
        assert result == {"s": 0.5, "loc": 0.0, "scale": 1.0}

    def test_gamma_params(self) -> None:
        result = _distribution_param_names("gamma", (2.0, 0.0, 1.0))
        assert result == {"a": 2.0, "loc": 0.0, "scale": 1.0}

    def test_expon_params(self) -> None:
        result = _distribution_param_names("expon", (0.0, 5.0))
        assert result == {"loc": 0.0, "scale": 5.0}

    def test_norm_params(self) -> None:
        result = _distribution_param_names("norm", (100.0, 20.0))
        assert result == {"loc": 100.0, "scale": 20.0}

    def test_pareto_params(self) -> None:
        result = _distribution_param_names("pareto", (1.5, 0.0, 1.0))
        assert result == {"b": 1.5, "loc": 0.0, "scale": 1.0}

    def test_unknown_distribution_uses_generic_names(self) -> None:
        result = _distribution_param_names("unknown_dist", (1.0, 2.0, 3.0))
        assert result == {"p0": 1.0, "p1": 2.0, "p2": 3.0}


# =====================================================================
# Sector/year parameter computation
# =====================================================================


class TestComputeSectorYearParameters:
    """Tests for grouped distribution fitting."""

    def test_returns_sector_year_parameters(self, parquet_path: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=None)
        df = lf.collect()

        results = compute_sector_year_parameters(df)
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, SectorYearParameters) for r in results)

    def test_parameters_have_distributions(self, parquet_path: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=None)
        df = lf.collect()

        results = compute_sector_year_parameters(df)
        for r in results:
            assert r.n_companies > 0
            assert len(r.distributions) > 0
            for d in r.distributions:
                assert isinstance(d, FittedDistribution)
                assert d.n_observations >= MIN_OBSERVATIONS

    def test_results_sorted(self, parquet_path: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=None)
        df = lf.collect()

        results = compute_sector_year_parameters(df)
        keys = [(r.sector, r.financial_year) for r in results]
        assert keys == sorted(keys)

    def test_custom_candidates(self, parquet_path: Path) -> None:
        lf = load_accounts(parquet_path)
        lf = assign_sectors(lf, sic_path=None)
        df = lf.collect()

        results = compute_sector_year_parameters(df, candidates=("norm", "lognorm"))
        for r in results:
            for d in r.distributions:
                assert d.distribution in ("norm", "lognorm")


# =====================================================================
# Build summary
# =====================================================================


class TestBuildSummary:
    """Tests for building the distribution summary."""

    def test_summary_structure(self) -> None:
        params = [
            SectorYearParameters(
                sector="manufacturing",
                financial_year=2020,
                n_companies=100,
                distributions=[
                    FittedDistribution(
                        field="employees",
                        distribution="lognorm",
                        params={"s": 1.0, "loc": 0.0, "scale": 10.0},
                        aic=500.0,
                        ks_statistic=0.05,
                        ks_pvalue=0.8,
                        n_observations=100,
                    )
                ],
            )
        ]
        summary = build_summary(params, total_companies=1000)

        assert isinstance(summary, FirmDistributionSummary)
        assert summary.total_companies == 1000
        assert summary.sectors == ["manufacturing"]
        assert summary.financial_years == [2020]
        assert len(summary.parameters) == 1
        assert summary.generated_at  # non-empty timestamp

    def test_summary_multiple_sectors_and_years(self) -> None:
        params = [
            SectorYearParameters(
                sector="construction",
                financial_year=2019,
                n_companies=50,
                distributions=[],
            ),
            SectorYearParameters(
                sector="manufacturing",
                financial_year=2020,
                n_companies=100,
                distributions=[],
            ),
        ]
        summary = build_summary(params, total_companies=500)
        assert summary.sectors == ["construction", "manufacturing"]
        assert summary.financial_years == [2019, 2020]


# =====================================================================
# I/O helpers
# =====================================================================


class TestSaveParameters:
    """Tests for YAML and JSON serialisation."""

    def _make_summary(self) -> FirmDistributionSummary:
        return FirmDistributionSummary(
            generated_at="2025-01-01T00:00:00+00:00",
            total_companies=1000,
            sectors=["manufacturing"],
            financial_years=[2020],
            parameters=[
                SectorYearParameters(
                    sector="manufacturing",
                    financial_year=2020,
                    n_companies=100,
                    distributions=[
                        FittedDistribution(
                            field="employees",
                            distribution="lognorm",
                            params={"s": 1.0, "loc": 0.0, "scale": 10.0},
                            aic=500.0,
                            ks_statistic=0.05,
                            ks_pvalue=0.8,
                            n_observations=100,
                        )
                    ],
                )
            ],
        )

    def test_save_yaml(self, tmp_path: Path) -> None:
        import yaml

        summary = self._make_summary()
        path = tmp_path / "params.yml"
        save_parameters_yaml(summary, path)

        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert data["total_companies"] == 1000
        assert len(data["parameters"]) == 1
        assert data["parameters"][0]["sector"] == "manufacturing"

    def test_save_json(self, tmp_path: Path) -> None:
        summary = self._make_summary()
        path = tmp_path / "params.json"
        save_parameters_json(summary, path)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["total_companies"] == 1000
        assert len(data["parameters"]) == 1

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        summary = self._make_summary()
        path = tmp_path / "nested" / "dir" / "params.yml"
        save_parameters_yaml(summary, path)
        assert path.exists()

    def test_yaml_roundtrip_preserves_structure(self, tmp_path: Path) -> None:
        import yaml

        summary = self._make_summary()
        path = tmp_path / "roundtrip.yml"
        save_parameters_yaml(summary, path)

        data = yaml.safe_load(path.read_text())
        dist = data["parameters"][0]["distributions"][0]
        assert dist["field"] == "employees"
        assert dist["distribution"] == "lognorm"
        assert "s" in dist["params"]


# =====================================================================
# CLI integration
# =====================================================================


class TestProfileFirmsCLI:
    """Tests for the profile-firms CLI command."""

    def test_help(self) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})
        result = runner.invoke(app, ["profile-firms", "--help"])
        assert result.exit_code == 0
        assert "profile-firms" in result.output.lower() or "Profile" in result.output

    def test_missing_parquet_exits_with_error(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})
        result = runner.invoke(
            app,
            ["profile-firms", "--parquet", str(tmp_path / "nonexistent.parquet")],
        )
        assert result.exit_code == 1

    def test_unsupported_format_exits_with_error(
        self, parquet_path: Path, tmp_path: Path
    ) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})
        result = runner.invoke(
            app,
            [
                "profile-firms",
                "--parquet",
                str(parquet_path),
                "--format",
                "xml",
                "--output",
                str(tmp_path / "out.xml"),
            ],
        )
        assert result.exit_code == 1

    def test_runs_with_sample(self, parquet_path: Path, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})
        output = tmp_path / "output.yml"
        result = runner.invoke(
            app,
            [
                "profile-firms",
                "--parquet",
                str(parquet_path),
                "--output",
                str(output),
                "--sample",
                "0.5",
            ],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_json_output(self, parquet_path: Path, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})
        output = tmp_path / "output.json"
        result = runner.invoke(
            app,
            [
                "profile-firms",
                "--parquet",
                str(parquet_path),
                "--output",
                str(output),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert "parameters" in data

    def test_with_sic_file(
        self, parquet_path: Path, sic_csv: Path, tmp_path: Path
    ) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})
        output = tmp_path / "output.yml"
        result = runner.invoke(
            app,
            [
                "profile-firms",
                "--parquet",
                str(parquet_path),
                "--sic-file",
                str(sic_csv),
                "--output",
                str(output),
                "--sample",
                "0.5",
            ],
        )
        assert result.exit_code == 0


# =====================================================================
# Pipeline end-to-end
# =====================================================================


class TestRunProfilePipeline:
    """Tests for the high-level pipeline."""

    def test_pipeline_returns_summary(self, parquet_path: Path) -> None:
        summary = run_profile_pipeline(parquet_path)
        assert isinstance(summary, FirmDistributionSummary)
        assert summary.total_companies > 0

    def test_pipeline_writes_yaml(self, parquet_path: Path, tmp_path: Path) -> None:
        output = tmp_path / "params.yml"
        summary = run_profile_pipeline(
            parquet_path, output_path=output, output_format="yaml"
        )
        assert output.exists()
        assert len(summary.parameters) > 0

    def test_pipeline_writes_json(self, parquet_path: Path, tmp_path: Path) -> None:
        output = tmp_path / "params.json"
        run_profile_pipeline(parquet_path, output_path=output, output_format="json")
        assert output.exists()

    def test_pipeline_with_sample(self, parquet_path: Path, tmp_path: Path) -> None:
        output = tmp_path / "params.yml"
        summary = run_profile_pipeline(
            parquet_path,
            output_path=output,
            sample_fraction=0.5,
        )
        assert isinstance(summary, FirmDistributionSummary)

    def test_pipeline_with_sic(
        self, parquet_path: Path, sic_csv: Path, tmp_path: Path
    ) -> None:
        output = tmp_path / "params.yml"
        summary = run_profile_pipeline(
            parquet_path,
            sic_path=sic_csv,
            output_path=output,
        )
        assert isinstance(summary, FirmDistributionSummary)

    def test_pipeline_no_output_path(self, parquet_path: Path) -> None:
        """Pipeline works even when no output path is given."""
        summary = run_profile_pipeline(parquet_path)
        assert isinstance(summary, FirmDistributionSummary)


# =====================================================================
# Dataclass serialization
# =====================================================================


class TestDataclasses:
    """Tests for dataclass construction and serialization."""

    def test_field_profile_dataclass(self) -> None:
        fp = FieldProfile(name="test", count=100, null_count=10, null_pct=10.0)
        assert fp.name == "test"
        assert fp.mean is None

    def test_fitted_distribution_dataclass(self) -> None:
        fd = FittedDistribution(
            field="employees",
            distribution="lognorm",
            params={"s": 1.0},
            aic=100.0,
            ks_statistic=0.05,
            ks_pvalue=0.9,
            n_observations=50,
        )
        assert fd.field == "employees"

    def test_sector_year_parameters_dataclass(self) -> None:
        syp = SectorYearParameters(
            sector="manufacturing",
            financial_year=2020,
            n_companies=100,
            distributions=[],
        )
        assert syp.sector == "manufacturing"
        assert syp.n_companies == 100

    def test_summary_to_dict(self) -> None:
        from companies_house_abm.data_sources.firm_distributions import (
            _summary_to_dict,
        )

        summary = FirmDistributionSummary(
            generated_at="2025-01-01",
            total_companies=100,
            sectors=["manufacturing"],
            financial_years=[2020],
            parameters=[],
        )
        d = _summary_to_dict(summary)
        assert isinstance(d, dict)
        assert d["total_companies"] == 100
        assert d["sectors"] == ["manufacturing"]
