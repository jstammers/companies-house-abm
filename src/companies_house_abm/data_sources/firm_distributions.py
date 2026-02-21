"""Firm data profiling, sector assignment, and distribution fitting.

This module processes Companies House accounts data to:

1. Profile balance-sheet and P&L fields (nullity, outliers).
2. Assign SIC-code-based sectors using the 13-sector ABM taxonomy.
3. Fit statistical distributions to key financial variables per sector
   and financial year.
4. Export fitted parameters as YAML for downstream ABM sampling.

The key financial fields mapped to :class:`~companies_house_abm.abm.agents.firm.Firm`
attributes are:

.. list-table::
   :header-rows: 1

   * - Firm attribute
     - Parquet column
   * - employees
     - ``average_number_employees_during_period``
   * - turnover
     - ``turnover_gross_operating_revenue``
   * - capital
     - ``tangible_fixed_assets``
   * - cash
     - ``cash_bank_in_hand``
   * - debt
     - ``creditors_due_within_one_year`` + ``creditors_due_after_one_year``
   * - equity
     - ``shareholder_funds``
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

logger = logging.getLogger(__name__)


# =====================================================================
# SIC Division → ABM Sector mapping
# =====================================================================

#: Map from 2-digit SIC division prefix to ABM sector name.
#: Based on the UK SIC 2007 classification and the 13-sector taxonomy
#: defined in :class:`~companies_house_abm.abm.config.FirmConfig`.
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
    "69": "professional_services",
    "70": "professional_services",
    "71": "professional_services",
    "72": "professional_services",
    "73": "professional_services",
    "74": "professional_services",
    "75": "professional_services",
    # Administrative and support: SIC divisions 77 to 82
    "77": "professional_services",
    "78": "professional_services",
    "79": "professional_services",
    "80": "professional_services",
    "81": "professional_services",
    "82": "professional_services",
    # Public administration
    "84": "public_admin",
    # Education
    "85": "education",
    # Health and social work: SIC divisions 86 to 88
    "86": "health",
    "87": "health",
    "88": "health",
    # Arts, entertainment, other services: SIC divisions 90 to 99
    "90": "other_services",
    "91": "other_services",
    "92": "other_services",
    "93": "other_services",
    "94": "other_services",
    "95": "other_services",
    "96": "other_services",
    "97": "other_services",
    "98": "other_services",
    "99": "other_services",
}

#: Columns from the parquet that map to Firm agent constructor arguments.
FIRM_FIELD_MAP: dict[str, str] = {
    "employees": "average_number_employees_during_period",
    "turnover": "turnover_gross_operating_revenue",
    "capital": "tangible_fixed_assets",
    "cash": "cash_bank_in_hand",
    "equity": "shareholder_funds",
}

#: Additional columns that are summed to derive ``debt``.
DEBT_COLUMNS: tuple[str, ...] = (
    "creditors_due_within_one_year",
    "creditors_due_after_one_year",
)

#: Candidate distribution families for scipy fitting.
CANDIDATE_DISTRIBUTIONS: tuple[str, ...] = (
    "lognorm",
    "expon",
    "gamma",
    "norm",
    "pareto",
)

#: Minimum number of non-null observations required to attempt a fit.
MIN_OBSERVATIONS: int = 30

#: Default quantile thresholds used for outlier detection.
OUTLIER_QUANTILES: tuple[float, float] = (0.01, 0.99)


# =====================================================================
# Dataclasses for results
# =====================================================================


@dataclass
class FieldProfile:
    """Summary statistics for a single numeric column."""

    name: str
    count: int
    null_count: int
    null_pct: float
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    q25: float | None = None
    median: float | None = None
    q75: float | None = None
    max: float | None = None
    outlier_low: float | None = None
    outlier_high: float | None = None
    outlier_count: int = 0


@dataclass
class DataProfile:
    """Profile for the full accounts dataset."""

    total_rows: int
    total_companies: int
    date_range: tuple[str, str]
    fields: list[FieldProfile]


@dataclass
class FittedDistribution:
    """Result of fitting a statistical distribution to observed data."""

    field: str
    distribution: str
    params: dict[str, float]
    aic: float
    ks_statistic: float
    ks_pvalue: float
    n_observations: int


@dataclass
class SectorYearParameters:
    """Fitted distribution parameters for one sector in one year."""

    sector: str
    financial_year: int
    n_companies: int
    distributions: list[FittedDistribution]


@dataclass
class FirmDistributionSummary:
    """Complete summary of fitted parameters across sectors and years."""

    generated_at: str
    total_companies: int
    sectors: list[str]
    financial_years: list[int]
    parameters: list[SectorYearParameters]
    metadata: dict[str, Any] = field(default_factory=dict)


# =====================================================================
# Data loading & cleaning
# =====================================================================


def _financial_year(date_col: pl.Expr) -> pl.Expr:
    """Derive UK financial year (April-March) from a date expression.

    Returns the *start* year of the financial year, e.g. a date in
    January 2023 -> FY 2022 (Apr 2022 - Mar 2023).
    """
    return (
        pl.when(date_col.dt.month() >= 4)
        .then(date_col.dt.year())
        .otherwise(date_col.dt.year() - 1)
    ).alias("financial_year")


def load_accounts(
    path: Path,
    *,
    drop_dormant: bool = True,
    drop_errors: bool = True,
) -> pl.LazyFrame:
    """Load and clean Companies House accounts from a parquet file.

    Args:
        path: Path to ``companies_house_accounts.parquet``.
        drop_dormant: Exclude companies flagged as dormant.
        drop_errors: Exclude rows where the ``error`` column is non-null.

    Returns:
        A lazy frame with cleaned data, financial year column, and
        a derived ``debt`` column.
    """
    lf = pl.scan_parquet(path)

    # Drop rows with errors.
    # NOTE: cast to Utf8 first to work around a Polars predicate-pushdown
    # bug where filtering `is_null()` on an all-null string column read
    # from parquet raises a ShapeError.
    if drop_errors:
        lf = lf.with_columns(pl.col("error").cast(pl.Utf8)).filter(
            pl.col("error").is_null()
        )

    # Drop dormant companies
    if drop_dormant:
        lf = lf.filter(pl.col("company_dormant").is_null() | ~pl.col("company_dormant"))

    # Clean date outliers: only keep balance_sheet_date in [1990, 2030]
    lf = lf.filter(
        pl.col("balance_sheet_date").is_not_null()
        & (pl.col("balance_sheet_date").dt.year() >= 1990)
        & (pl.col("balance_sheet_date").dt.year() <= 2030)
    )

    # Derive financial year
    lf = lf.with_columns(_financial_year(pl.col("balance_sheet_date")))

    # Cast decimal columns to float for computation
    decimal_cols = [
        *FIRM_FIELD_MAP.values(),
        *DEBT_COLUMNS,
    ]
    lf = lf.with_columns(
        [pl.col(c).cast(pl.Float64, strict=False) for c in decimal_cols]
    )

    # Derive debt as sum of creditors columns
    lf = lf.with_columns(
        (
            pl.col("creditors_due_within_one_year").fill_null(0.0)
            + pl.col("creditors_due_after_one_year").fill_null(0.0)
        ).alias("debt_total")
    )

    return lf


# =====================================================================
# Sector assignment
# =====================================================================


def map_sic_to_sector(sic_code: str) -> str:
    """Map a SIC code string to the ABM sector taxonomy.

    Args:
        sic_code: A SIC 2007 code (e.g. ``"62020"``).

    Returns:
        The corresponding ABM sector name, or ``"other_services"``
        if the code cannot be mapped.
    """
    if not sic_code or len(sic_code) < 2:
        return "other_services"
    prefix = sic_code[:2]
    return SIC_TO_SECTOR.get(prefix, "other_services")


def assign_sectors(
    accounts: pl.LazyFrame,
    sic_path: Path | None = None,
) -> pl.LazyFrame:
    """Join SIC codes and assign sectors to accounts data.

    If *sic_path* is provided it should point to a parquet or CSV with
    at least ``companies_house_registered_number`` and ``sic_code``
    columns.  When no SIC data is available, all firms are assigned to
    ``"other_services"``.

    Args:
        accounts: Lazy frame from :func:`load_accounts`.
        sic_path: Optional path to SIC code lookup file.

    Returns:
        The accounts frame with an added ``sector`` column.
    """
    if sic_path is not None and sic_path.exists():
        logger.info("Loading SIC codes from %s", sic_path)
        suffix = sic_path.suffix.lower()
        if suffix == ".parquet":
            sic_df = pl.scan_parquet(sic_path)
        elif suffix == ".csv":
            sic_df = pl.scan_csv(sic_path)
        else:
            msg = f"Unsupported SIC file format: {suffix}"
            raise ValueError(msg)

        # Expect columns: companies_house_registered_number, sic_code
        sic_df = sic_df.select(
            pl.col("companies_house_registered_number").cast(pl.Utf8),
            pl.col("sic_code").cast(pl.Utf8),
        )

        # Map SIC codes to sectors
        sic_sector_map = pl.DataFrame(
            {
                "sic_prefix": list(SIC_TO_SECTOR.keys()),
                "sector": list(SIC_TO_SECTOR.values()),
            }
        ).lazy()

        sic_df = sic_df.with_columns(
            pl.col("sic_code").str.slice(0, 2).alias("sic_prefix")
        )
        sic_df = sic_df.join(sic_sector_map, on="sic_prefix", how="left")
        sic_df = sic_df.with_columns(
            pl.col("sector").fill_null("other_services")
        ).select("companies_house_registered_number", "sector")

        # Deduplicate SIC data (one sector per company)
        sic_df = sic_df.unique(
            subset=["companies_house_registered_number"], keep="first"
        )

        accounts = accounts.join(
            sic_df,
            on="companies_house_registered_number",
            how="left",
        )
        accounts = accounts.with_columns(pl.col("sector").fill_null("other_services"))
    else:
        logger.warning(
            "No SIC code file provided; assigning all firms to 'other_services'"
        )
        accounts = accounts.with_columns(pl.lit("other_services").alias("sector"))

    return accounts


# =====================================================================
# Data profiling
# =====================================================================


def profile_field(
    series: pl.Series,
    *,
    outlier_quantiles: tuple[float, float] = OUTLIER_QUANTILES,
) -> FieldProfile:
    """Compute summary statistics for a single numeric series.

    Args:
        series: A Polars Series of numeric values.
        outlier_quantiles: Lower and upper quantile thresholds for
            outlier detection.

    Returns:
        A :class:`FieldProfile` with the computed statistics.
    """
    total = len(series)
    null_count = series.null_count()
    null_pct = (null_count / total * 100) if total > 0 else 0.0

    non_null = series.drop_nulls()
    if len(non_null) == 0:
        return FieldProfile(
            name=series.name,
            count=total,
            null_count=null_count,
            null_pct=null_pct,
        )

    q_low = non_null.quantile(outlier_quantiles[0], interpolation="linear")
    q_high = non_null.quantile(outlier_quantiles[1], interpolation="linear")
    outlier_count = 0
    if q_low is not None and q_high is not None:
        outlier_count = int(((non_null < q_low) | (non_null > q_high)).sum())

    return FieldProfile(
        name=series.name,
        count=total,
        null_count=null_count,
        null_pct=null_pct,
        mean=non_null.mean(),
        std=non_null.std(),
        min=non_null.min(),
        q25=non_null.quantile(0.25, interpolation="linear"),
        median=non_null.median(),
        q75=non_null.quantile(0.75, interpolation="linear"),
        max=non_null.max(),
        outlier_low=q_low,
        outlier_high=q_high,
        outlier_count=outlier_count,
    )


def profile_accounts(df: pl.DataFrame) -> DataProfile:
    """Generate a data profile for the accounts dataset.

    Args:
        df: Collected (non-lazy) accounts DataFrame.

    Returns:
        A :class:`DataProfile` summarising each financial field.
    """
    total_rows = len(df)
    total_companies = df["company_id"].n_unique()

    bs_date = df["balance_sheet_date"].drop_nulls()
    date_min = str(bs_date.min()) if len(bs_date) > 0 else "N/A"
    date_max = str(bs_date.max()) if len(bs_date) > 0 else "N/A"

    fields_to_profile = [
        *FIRM_FIELD_MAP.values(),
        *DEBT_COLUMNS,
        "debt_total",
        "profit_loss_for_period",
    ]

    field_profiles = []
    for col_name in fields_to_profile:
        if col_name in df.columns:
            series = df[col_name].cast(pl.Float64, strict=False)
            field_profiles.append(profile_field(series))

    return DataProfile(
        total_rows=total_rows,
        total_companies=total_companies,
        date_range=(date_min, date_max),
        fields=field_profiles,
    )


# =====================================================================
# Distribution fitting
# =====================================================================


def fit_distribution(
    values: pl.Series,
    field_name: str,
    candidates: tuple[str, ...] = CANDIDATE_DISTRIBUTIONS,
) -> FittedDistribution | None:
    """Fit the best statistical distribution to *values*.

    Tries each candidate from *candidates*, selects the one with
    lowest AIC, and returns a :class:`FittedDistribution`.

    Args:
        values: Non-null numeric observations.
        field_name: Name for the fitted field.
        candidates: Distribution family names from ``scipy.stats``.

    Returns:
        The best-fitting distribution, or ``None`` when there are
        fewer than :data:`MIN_OBSERVATIONS` data points.
    """
    import numpy as np
    from scipy import stats

    clean = values.drop_nulls().to_numpy().astype(np.float64)
    clean = clean[np.isfinite(clean)]

    if len(clean) < MIN_OBSERVATIONS:
        return None

    best: FittedDistribution | None = None
    best_aic = float("inf")

    for dist_name in candidates:
        dist = getattr(stats, dist_name, None)
        if dist is None:
            continue

        try:
            # Some distributions only work with positive data
            data = clean
            if dist_name in ("lognorm", "gamma", "pareto", "expon"):
                data = data[data > 0]
                if len(data) < MIN_OBSERVATIONS:
                    continue

            params = dist.fit(data)
            log_likelihood = np.sum(dist.logpdf(data, *params))

            if not np.isfinite(log_likelihood):
                continue

            k = len(params)
            aic = 2 * k - 2 * log_likelihood

            ks_stat, ks_p = stats.kstest(data, dist_name, args=params)

            if aic < best_aic:
                best_aic = aic

                # Build a human-readable parameter dict
                param_names = _distribution_param_names(dist_name, params)

                best = FittedDistribution(
                    field=field_name,
                    distribution=dist_name,
                    params=param_names,
                    aic=float(aic),
                    ks_statistic=float(ks_stat),
                    ks_pvalue=float(ks_p),
                    n_observations=len(data),
                )
        except Exception:
            logger.debug("Failed to fit %s to %s", dist_name, field_name, exc_info=True)
            continue

    return best


def _distribution_param_names(
    dist_name: str, params: tuple[float, ...]
) -> dict[str, float]:
    """Map positional scipy parameters to named keys.

    Args:
        dist_name: The scipy distribution name.
        params: Positional parameters from ``dist.fit()``.

    Returns:
        Dictionary mapping parameter names to values.
    """
    if dist_name == "lognorm":
        return {"s": params[0], "loc": params[1], "scale": params[2]}
    if dist_name == "gamma":
        return {"a": params[0], "loc": params[1], "scale": params[2]}
    if dist_name == "expon":
        return {"loc": params[0], "scale": params[1]}
    if dist_name == "norm":
        return {"loc": params[0], "scale": params[1]}
    if dist_name == "pareto":
        return {"b": params[0], "loc": params[1], "scale": params[2]}
    # Generic fallback
    return {f"p{i}": float(v) for i, v in enumerate(params)}


# =====================================================================
# Per-sector, per-year parameter generation
# =====================================================================


def _firm_fields() -> list[str]:
    """Return the list of field names to fit distributions for."""
    return [*FIRM_FIELD_MAP.keys(), "debt"]


def compute_sector_year_parameters(
    df: pl.DataFrame,
    *,
    candidates: tuple[str, ...] = CANDIDATE_DISTRIBUTIONS,
) -> list[SectorYearParameters]:
    """Fit distributions to firm fields grouped by sector and year.

    Args:
        df: Collected accounts DataFrame with ``sector`` and
            ``financial_year`` columns.
        candidates: Distribution families to try.

    Returns:
        A list of :class:`SectorYearParameters`, one per
        (sector, year) combination that has enough data.
    """
    results: list[SectorYearParameters] = []
    field_names = _firm_fields()

    # Build column mapping for extraction
    col_map: dict[str, str] = {**FIRM_FIELD_MAP, "debt": "debt_total"}

    groups = df.group_by(["sector", "financial_year"])
    for (sector, fy), group_df in groups:
        distributions: list[FittedDistribution] = []

        for firm_field in field_names:
            parquet_col = col_map.get(firm_field, firm_field)
            if parquet_col not in group_df.columns:
                continue
            series = group_df[parquet_col].cast(pl.Float64, strict=False)
            fitted = fit_distribution(series, firm_field, candidates)
            if fitted is not None:
                distributions.append(fitted)

        if distributions:
            results.append(
                SectorYearParameters(
                    sector=str(sector),
                    financial_year=int(fy),  # type: ignore[arg-type]
                    n_companies=len(group_df),
                    distributions=distributions,
                )
            )

    # Sort for deterministic output
    results.sort(key=lambda r: (r.sector, r.financial_year))
    return results


def build_summary(
    parameters: list[SectorYearParameters],
    total_companies: int,
) -> FirmDistributionSummary:
    """Wrap fitted parameters into a complete summary.

    Args:
        parameters: Fitted sector-year parameters.
        total_companies: Total number of unique companies in the data.

    Returns:
        A :class:`FirmDistributionSummary` ready for serialisation.
    """
    import datetime

    sectors = sorted({p.sector for p in parameters})
    years = sorted({p.financial_year for p in parameters})

    return FirmDistributionSummary(
        generated_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
        total_companies=total_companies,
        sectors=sectors,
        financial_years=years,
        parameters=parameters,
    )


# =====================================================================
# I/O helpers
# =====================================================================


def save_parameters_yaml(summary: FirmDistributionSummary, path: Path) -> None:
    """Write the fitted parameters to a YAML file.

    Args:
        summary: The complete distribution summary.
        path: Output file path.
    """
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    data = _summary_to_dict(summary)
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    logger.info("Parameters written to %s", path)


def save_parameters_json(summary: FirmDistributionSummary, path: Path) -> None:
    """Write the fitted parameters to a JSON file.

    Args:
        summary: The complete distribution summary.
        path: Output file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _summary_to_dict(summary)
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Parameters written to %s", path)


def _summary_to_dict(summary: FirmDistributionSummary) -> dict[str, Any]:
    """Convert a summary dataclass tree to a plain dict."""
    return asdict(summary)


# =====================================================================
# High-level pipeline
# =====================================================================


def run_profile_pipeline(
    parquet_path: Path,
    *,
    sic_path: Path | None = None,
    output_path: Path | None = None,
    output_format: str = "yaml",
    sample_fraction: float | None = None,
) -> FirmDistributionSummary:
    """Run the full profiling and distribution-fitting pipeline.

    This is the main entry-point used by the CLI.

    Args:
        parquet_path: Path to Companies House accounts parquet.
        sic_path: Optional path to SIC code lookup file.
        output_path: Where to write the fitted parameters.
            When ``None``, parameters are not written.
        output_format: ``"yaml"`` or ``"json"``.
        sample_fraction: Fraction of data to sample (for speed).
            ``None`` uses all data.

    Returns:
        The :class:`FirmDistributionSummary` with all fitted parameters.
    """
    logger.info("Loading accounts from %s", parquet_path)
    lf = load_accounts(parquet_path)
    lf = assign_sectors(lf, sic_path)

    if sample_fraction is not None:
        logger.info("Sampling %.1f%% of data", sample_fraction * 100)
        # Collect and sample — sampling a lazy frame requires collecting
        df = lf.collect()
        df = df.sample(fraction=sample_fraction, seed=42)
    else:
        df = lf.collect()

    logger.info("Loaded %d rows for %d companies", len(df), df["company_id"].n_unique())

    # Profile
    profile = profile_accounts(df)
    logger.info(
        "Data profile: %d rows, %d companies, dates %s to %s",
        profile.total_rows,
        profile.total_companies,
        profile.date_range[0],
        profile.date_range[1],
    )

    # Fit distributions
    parameters = compute_sector_year_parameters(df)
    summary = build_summary(parameters, profile.total_companies)

    logger.info(
        "Fitted %d sector-year parameter sets across %d sectors and %d years",
        len(summary.parameters),
        len(summary.sectors),
        len(summary.financial_years),
    )

    # Write output
    if output_path is not None:
        if output_format == "json":
            save_parameters_json(summary, output_path)
        else:
            save_parameters_yaml(summary, output_path)

    return summary
