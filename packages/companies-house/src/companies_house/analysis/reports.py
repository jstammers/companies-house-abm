"""Company financial analysis and report generation.

The main entry points are :func:`analyse_company` (returns a structured
:class:`CompanyReport`) and :func:`generate_report` (returns formatted text).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

from companies_house.analysis.benchmarks import (
    SectorBenchmark,
    _load_sic_sector_ids,
    build_peer_group,
    compute_sector_benchmark,
)
from companies_house.analysis.forecasting import ForecastResult, forecast_metric
from companies_house.analysis.formatting import build_report_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PL_COLS = [
    "turnover_gross_operating_revenue",
    "other_operating_income",
    "cost_sales",
    "gross_profit_loss",
    "administrative_expenses",
    "raw_materials_consumables",
    "staff_costs",
    "depreciation_other_amounts_written_off_tangible_intangible_fixed_assets",
    "operating_profit_loss",
    "profit_loss_on_ordinary_activities_before_tax",
    "tax_on_profit_or_loss_on_ordinary_activities",
    "profit_loss_for_period",
]

_BS_COLS = [
    "tangible_fixed_assets",
    "debtors",
    "cash_bank_in_hand",
    "current_assets",
    "creditors_due_within_one_year",
    "creditors_due_after_one_year",
    "net_current_assets_liabilities",
    "total_assets_less_current_liabilities",
    "net_assets_liabilities_including_pension_asset_liability",
    "called_up_share_capital",
    "profit_loss_account_reserve",
    "shareholder_funds",
    "average_number_employees_during_period",
]

_INSTANT_THRESHOLD_DAYS = 5

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _find_default_parquet() -> Path:
    """Walk up from this file to find data/companies_house_accounts.parquet."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "companies_house_accounts.parquet"
        if candidate.exists():
            return candidate
    return Path("data") / "companies_house_accounts.parquet"


_DEFAULT_PARQUET = _find_default_parquet()


# ---------------------------------------------------------------------------
# Data-classes
# ---------------------------------------------------------------------------


@dataclass
class CompanyReport:
    """Structured output of a company analysis."""

    company_name: str
    company_id: str
    num_periods: int
    pl_history: pl.DataFrame
    bs_history: pl.DataFrame
    forecasts: list[ForecastResult] = field(default_factory=list)
    report_text: str = ""
    sector_benchmark: SectorBenchmark | None = None


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------


def search_companies(
    name: str,
    parquet_path: Path | None = None,
    *,
    max_results: int = 20,
) -> pl.DataFrame:
    """Return distinct companies whose name contains *name*."""
    path = Path(parquet_path) if parquet_path else _DEFAULT_PARQUET
    return (
        pl.scan_parquet(path)
        .filter(
            pl.col("entity_current_legal_name")
            .str.to_lowercase()
            .str.contains(name.lower())
        )
        .select(["company_id", "entity_current_legal_name"])
        .unique()
        .sort("entity_current_legal_name")
        .head(max_results)
        .collect()
    )


# ---------------------------------------------------------------------------
# Data loading & reshaping
# ---------------------------------------------------------------------------


def load_company_data(
    company_id: str,
    parquet_path: Path | None = None,
) -> pl.DataFrame:
    """Load every row for *company_id* from the parquet."""
    path = Path(parquet_path) if parquet_path else _DEFAULT_PARQUET
    return pl.scan_parquet(path).filter(pl.col("company_id") == company_id).collect()


def _is_instant(df: pl.DataFrame) -> pl.Series:
    """Boolean mask: True for balance-sheet (instant) rows."""
    diff = (pl.col("period_end") - pl.col("period_start")).dt.total_days()
    return df.select(diff.alias("d"))["d"].abs() <= _INSTANT_THRESHOLD_DAYS


def split_statements(
    df: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Split into (P&L duration rows, balance-sheet instant rows)."""
    mask = _is_instant(df)
    bs = df.filter(mask)
    pl_ = df.filter(~mask)
    return pl_, bs


def build_pl_history(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Return a clean annual P&L time-series sorted by period_end."""
    if pl_df.is_empty():
        return pl_df
    cols = ["period_start", "period_end"] + [c for c in _PL_COLS if c in pl_df.columns]
    return (
        pl_df.select(cols)
        .sort("period_end")
        .with_columns(
            pl.col(c).cast(pl.Float64) for c in _PL_COLS if c in pl_df.columns
        )
    )


def build_bs_history(bs_df: pl.DataFrame) -> pl.DataFrame:
    """Return a clean balance-sheet time-series sorted by period_end."""
    if bs_df.is_empty():
        return bs_df
    cols = ["period_end"] + [c for c in _BS_COLS if c in bs_df.columns]
    return (
        bs_df.select(cols)
        .sort("period_end")
        .with_columns(
            pl.col(c).cast(pl.Float64)
            for c in _BS_COLS
            if c in bs_df.columns and c != "average_number_employees_during_period"
        )
        .with_columns(
            pl.col("average_number_employees_during_period").cast(pl.Float64)
            if "average_number_employees_during_period" in bs_df.columns
            else pl.lit(None, dtype=pl.Float64).alias(
                "average_number_employees_during_period"
            )
        )
    )


def compute_derived_metrics(
    pl_hist: pl.DataFrame,
    bs_hist: pl.DataFrame,
) -> pl.DataFrame:
    """Merge P&L and BS data and add derived financial ratios."""
    if pl_hist.is_empty():
        return pl_hist

    df = pl_hist
    bs = bs_hist.rename({"period_end": "bs_date"}) if not bs_hist.is_empty() else None

    if bs is not None and not bs.is_empty():
        df = df.join_asof(
            bs.sort("bs_date"),
            left_on="period_end",
            right_on="bs_date",
            strategy="nearest",
            tolerance="60d",
        )

    def safe_ratio(num: str, den: str, alias: str) -> pl.Expr:
        return (
            pl.when(pl.col(den).is_not_null() & (pl.col(den) != 0))
            .then(pl.col(num) / pl.col(den) * 100)
            .otherwise(None)
            .alias(alias)
        ).cast(pl.Float64)

    rev_col = "turnover_gross_operating_revenue"
    exprs = []
    if "gross_profit_loss" in df.columns and rev_col in df.columns:
        exprs.append(safe_ratio("gross_profit_loss", rev_col, "gross_margin_pct"))
    if "operating_profit_loss" in df.columns and rev_col in df.columns:
        exprs.append(
            safe_ratio(
                "operating_profit_loss",
                rev_col,
                "operating_margin_pct",
            )
        )
    if "profit_loss_for_period" in df.columns and rev_col in df.columns:
        exprs.append(safe_ratio("profit_loss_for_period", rev_col, "net_margin_pct"))

    if exprs:
        df = df.with_columns(exprs)

    if "turnover_gross_operating_revenue" in df.columns and len(df) > 1:
        df = df.with_columns(
            (
                pl.col("turnover_gross_operating_revenue")
                / pl.col("turnover_gross_operating_revenue").shift(1)
                - 1
            ).alias("revenue_yoy_growth_pct")
            * 100
        )

    return df.sort("period_end")


# ---------------------------------------------------------------------------
# Top-level API
# ---------------------------------------------------------------------------


def analyse_company(
    company_id: str,
    company_name: str | None = None,
    parquet_path: Path | None = None,
    forecast_horizon: int = 3,
    sic_path: Path | None = None,
) -> CompanyReport:
    """Load, analyse, and forecast for a single company."""
    path = Path(parquet_path) if parquet_path else _DEFAULT_PARQUET
    raw = load_company_data(company_id, path)
    pl_df, bs_df = split_statements(raw)
    pl_hist = build_pl_history(pl_df)
    bs_hist = build_bs_history(bs_df)
    merged = compute_derived_metrics(pl_hist, bs_hist)

    name = company_name
    if not name and not raw.is_empty():
        name = raw["entity_current_legal_name"][0]
    name = name or company_id

    report = CompanyReport(
        company_name=name,
        company_id=company_id,
        num_periods=len(pl_hist),
        pl_history=merged,
        bs_history=bs_hist,
    )

    # Sector benchmark
    rev_col = "turnover_gross_operating_revenue"
    if not merged.is_empty() and rev_col in merged.columns:
        _latest_pl = merged.row(-1, named=True)
        _company_rev = _latest_pl.get(rev_col)
        _company_rev_float = float(_company_rev) if _company_rev else None
        if (
            _company_rev_float
            and not np.isnan(_company_rev_float)
            and _company_rev_float > 0
        ):
            _target_year = merged["period_end"][-1].year

            _sector_name: str | None = None
            _sector_ids: frozenset[str] | None = None
            if sic_path is not None:
                _sector_name, _sector_ids = _load_sic_sector_ids(
                    Path(sic_path), company_id
                )

            if _sector_name is not None:
                _sector_label = f"{_sector_name.replace('_', ' ').title()} sector"
            else:
                _sector_label = "size-matched peers"

            _peers = build_peer_group(
                target_revenue=_company_rev_float,
                target_year=_target_year,
                parquet_path=path,
                sector_company_ids=_sector_ids,
                exclude_company_id=company_id,
            )
            report.sector_benchmark = compute_sector_benchmark(
                peers=_peers,
                company_revenue=_company_rev_float,
                company_gross_margin=_latest_pl.get("gross_margin_pct"),
                company_op_margin=_latest_pl.get("operating_margin_pct"),
                company_net_margin=_latest_pl.get("net_margin_pct"),
                sector_label=_sector_label,
                target_year=_target_year,
            )

    # Forecast key metrics
    forecast_targets = [
        ("turnover_gross_operating_revenue", "Revenue"),
        ("gross_profit_loss", "Gross Profit"),
        ("operating_profit_loss", "Operating Profit"),
        ("profit_loss_for_period", "Net Profit"),
        ("gross_margin_pct", "Gross Margin %"),
        ("operating_margin_pct", "Operating Margin %"),
    ]
    years = [r["period_end"].year for r in merged.iter_rows(named=True)]
    for metric, label in forecast_targets:
        if metric not in merged.columns:
            continue
        values = [
            float(v) if v is not None else float("nan")
            for v in merged[metric].to_list()
        ]
        fc = forecast_metric(years, values, metric, label, horizon=forecast_horizon)
        if fc is not None:
            report.forecasts.append(fc)

    report.report_text = build_report_text(report)
    return report


def generate_report(
    company_name_or_id: str,
    parquet_path: Path | None = None,
    forecast_horizon: int = 3,
    sic_path: Path | None = None,
) -> str:
    """Search for a company and return a formatted report."""
    matches = search_companies(company_name_or_id, parquet_path)

    if matches.is_empty():
        return f"No company found matching '{company_name_or_id}'."

    if len(matches) > 1:
        listing = "\n".join(
            f"  {r['company_id']:12s}  {r['entity_current_legal_name']}"
            for r in matches.iter_rows(named=True)
        )
        first_id = matches["company_id"][0]
        first_name = matches["entity_current_legal_name"][0]
        msg = (
            f"Multiple companies matched "
            f"'{company_name_or_id}':\n{listing}\n\n"
            f"Using: {first_id} - {first_name}\n"
            "(Pass the exact company_id to analyse_company() "
            "to pick a specific one.)\n"
        )
    else:
        msg = ""

    chosen_id = matches["company_id"][0]
    chosen_name = matches["entity_current_legal_name"][0]
    report = analyse_company(
        chosen_id,
        chosen_name,
        parquet_path,
        forecast_horizon,
        sic_path=sic_path,
    )
    return msg + report.report_text
