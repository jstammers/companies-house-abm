"""Company financial analysis and forecasting from Companies House XBRL data.

Usage
-----
>>> from companies_house_abm.company_analysis import generate_report
>>> print(generate_report("Exel Computer Systems"))

CLI
---
    uv run python -m companies_house_abm.company_analysis "Exel Computer Systems"
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

logger = logging.getLogger(__name__)

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
    # Fall back to a path relative to cwd
    return Path("data") / "companies_house_accounts.parquet"


_DEFAULT_PARQUET = _find_default_parquet()

# ---------------------------------------------------------------------------
# Constants: which columns belong to which financial statement
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

# XBRL instant facts have period_start == period_end; duration facts differ.
_INSTANT_THRESHOLD_DAYS = 5  # allow minor rounding in XBRL filings


# ---------------------------------------------------------------------------
# Data-classes
# ---------------------------------------------------------------------------


@dataclass
class ForecastResult:
    """Linear trend forecast for a single metric."""

    metric: str
    display_name: str
    historical_years: list[int]
    historical_values: list[float]
    forecast_years: list[int]
    forecast_values: list[float]
    slope: float  # £ per year
    r_squared: float
    trend_direction: str  # "improving", "declining", "flat"
    confidence_note: str


@dataclass
class CompanyReport:
    """Structured output of a company analysis."""

    company_name: str
    company_id: str
    num_periods: int
    pl_history: pl.DataFrame  # one row per accounting period
    bs_history: pl.DataFrame  # one row per balance-sheet date
    forecasts: list[ForecastResult] = field(default_factory=list)
    report_text: str = ""
    sector_benchmark: SectorBenchmark | None = None


@dataclass
class SectorBenchmark:
    """Peer-group comparison for a company's key margin metrics.

    Peers are companies with revenue in [target_revenue / revenue_factor,
    target_revenue * revenue_factor] that filed accounts in the same year
    window.  When a SIC code lookup is provided the peer group is further
    restricted to companies in the same 13-sector ABM taxonomy bucket.

    All margins are expressed as percentages (e.g. 37.4 means 37.4 %).
    The revenue-weighted averages give more weight to larger companies,
    consistent with standard value-weighted sector-index methodology.
    """

    sector_label: str
    """Human-readable description of the peer group."""
    n_peers: int
    """Number of peer companies contributing to the benchmarks."""
    year: int
    """Fiscal year used for the comparison (target company's latest P&L year)."""
    peer_revenue_low: float
    """Lowest revenue in the peer group (£)."""
    peer_revenue_high: float
    """Highest revenue in the peer group (£)."""
    company_revenue: float | None = None
    """Target company revenue in the comparison year (£)."""
    # Revenue-weighted sector averages
    wt_gross_margin_pct: float | None = None
    wt_operating_margin_pct: float | None = None
    wt_net_margin_pct: float | None = None
    # Unweighted quartile distributions: (p25, p50, p75)
    gross_margin_quartiles: tuple[float, float, float] | None = None
    operating_margin_quartiles: tuple[float, float, float] | None = None
    net_margin_quartiles: tuple[float, float, float] | None = None
    # Company's own values and percentile rank within the peer distribution
    company_gross_margin_pct: float | None = None
    company_gross_margin_percentile: float | None = None
    company_operating_margin_pct: float | None = None
    company_operating_margin_percentile: float | None = None
    company_net_margin_pct: float | None = None
    company_net_margin_percentile: float | None = None


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------


def search_companies(
    name: str,
    parquet_path: Path | None = None,
    *,
    max_results: int = 20,
) -> pl.DataFrame:
    """Return distinct companies whose name contains *name* (case-insensitive).

    Parameters
    ----------
    name:
        Search string - matched as a substring against ``entity_current_legal_name``.
    parquet_path:
        Path to the processed Companies House parquet.  Defaults to
        ``data/companies_house_accounts.parquet`` relative to the repo root.
    max_results:
        Cap on number of rows returned.
    """
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


def split_statements(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Split raw company rows into (P&L duration rows, balance-sheet instant rows)."""
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
    """Return a clean balance-sheet snapshot time-series sorted by period_end."""
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
    """Merge P&L and balance-sheet data and add derived financial ratios."""
    if pl_hist.is_empty():
        return pl_hist

    df = pl_hist
    bs = bs_hist.rename({"period_end": "bs_date"}) if not bs_hist.is_empty() else None

    # Attach balance-sheet figures where period_end matches a balance-sheet instant date
    if bs is not None and not bs.is_empty():
        df = df.join_asof(
            bs.sort("bs_date"),
            left_on="period_end",
            right_on="bs_date",
            strategy="nearest",
            tolerance="60d",
        )

    # Derived ratios (safely handle division by zero / nulls)
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
            safe_ratio("operating_profit_loss", rev_col, "operating_margin_pct")
        )
    if "profit_loss_for_period" in df.columns and rev_col in df.columns:
        exprs.append(safe_ratio("profit_loss_for_period", rev_col, "net_margin_pct"))

    if exprs:
        df = df.with_columns(exprs)

    # YoY revenue growth
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


def build_peer_group(
    target_revenue: float,
    target_year: int,
    parquet_path: Path,
    *,
    revenue_factor: float = 4.0,
    year_window: int = 1,
    sector_company_ids: frozenset[str] | None = None,
    exclude_company_id: str | None = None,
    max_peers: int = 10_000,
) -> pl.DataFrame:
    """Return one P&L row per peer company for sector benchmarking.

    Parameters
    ----------
    target_revenue:
        Target company revenue (£).  Used to compute the size band
        ``[target_revenue / revenue_factor, target_revenue * revenue_factor]``.
    target_year:
        Target company's most recent P&L year.  Peers are accepted for years
        in ``[target_year - year_window, target_year + year_window]``.
    parquet_path:
        Path to the Companies House accounts parquet.
    revenue_factor:
        Half-width multiplier for the revenue band (default 4x, i.e. 1/4x to 4x).
    year_window:
        ± years from *target_year* to search (default 1).
    sector_company_ids:
        If supplied, restrict to this set of Companies House numbers (e.g.
        derived from a SIC-code lookup).
    exclude_company_id:
        Exclude the target company itself from the peer group.
    max_peers:
        Hard cap on the number of peers returned.

    Returns
    -------
    pl.DataFrame
        Columns: ``company_id``, ``period_end``,
        ``turnover_gross_operating_revenue``, ``gross_profit_loss``,
        ``operating_profit_loss``, ``profit_loss_for_period``.
        One row per peer (most recent qualifying period).
    """
    low = target_revenue / revenue_factor
    high = target_revenue * revenue_factor
    year_low = target_year - year_window
    year_high = target_year + year_window

    lf = (
        pl.scan_parquet(parquet_path)
        # Duration rows only (P&L, not balance-sheet instants)
        .filter(
            (pl.col("period_end") - pl.col("period_start")).dt.total_days().abs()
            > _INSTANT_THRESHOLD_DAYS
        )
        # Year range
        .filter(pl.col("period_end").dt.year().is_between(year_low, year_high))
        # Revenue band — also drops nulls
        .filter(
            pl.col("turnover_gross_operating_revenue").is_not_null()
            & pl.col("turnover_gross_operating_revenue").is_between(low, high)
        )
        .select(
            [
                "company_id",
                "period_end",
                "turnover_gross_operating_revenue",
                "gross_profit_loss",
                "operating_profit_loss",
                "profit_loss_for_period",
            ]
        )
    )

    if sector_company_ids is not None:
        lf = lf.filter(pl.col("company_id").is_in(list(sector_company_ids)))

    if exclude_company_id is not None:
        lf = lf.filter(pl.col("company_id") != exclude_company_id)

    # One row per company: keep the most recent period
    lf = lf.sort("period_end", descending=True).unique(
        subset=["company_id"], keep="first"
    )

    df = lf.collect()
    if len(df) > max_peers:
        df = df.head(max_peers)
    return df


def _load_sic_sector_ids(
    sic_path: Path,
    company_id: str,
) -> tuple[str | None, frozenset[str] | None]:
    """Look up *company_id* in a SIC code file and return its sector + co-sector IDs.

    The SIC file must have columns ``companies_house_registered_number`` (or
    ``company_number`` / similar) and ``sic_code``.  Both parquet and CSV are
    accepted.

    Returns
    -------
    (sector_name, frozenset_of_company_ids)
        ``sector_name`` is the ABM 13-sector label (e.g. ``"technology"``).
        Returns ``(None, None)`` if the lookup fails for any reason.
    """
    from companies_house_abm.data_sources.firm_distributions import SIC_TO_SECTOR

    try:
        p = Path(sic_path)
        if p.suffix == ".parquet":
            sic_df = pl.read_parquet(p)
        else:
            sic_df = pl.read_csv(p, infer_schema_length=2000)
    except Exception:
        logger.warning("Could not read SIC code file: %s", sic_path, exc_info=True)
        return None, None

    # Normalise column names
    rename: dict[str, str] = {}
    for col in sic_df.columns:
        cl = col.lower()
        if any(
            kw in cl for kw in ("registered_number", "company_number", "company_id")
        ):
            rename[col] = "_cid"
        elif "sic" in cl:
            rename[col] = "_sic"
    if "_cid" not in rename.values() or "_sic" not in rename.values():
        return None, None
    sic_df = sic_df.rename(rename)

    sic_df = sic_df.with_columns(
        [
            pl.col("_cid").cast(pl.Utf8).str.zfill(8),
            pl.col("_sic").cast(pl.Utf8).str.strip_chars(),
        ]
    )

    target_rows = sic_df.filter(pl.col("_cid") == company_id)
    if target_rows.is_empty():
        return None, None

    sic_code = str(target_rows["_sic"][0]).strip()
    division = sic_code[:2]
    sector = SIC_TO_SECTOR.get(division)
    if sector is None:
        return None, None

    # All divisions that map to the same sector
    same_sector_divs = {k for k, v in SIC_TO_SECTOR.items() if v == sector}
    sector_ids = frozenset(
        sic_df.filter(pl.col("_sic").str.slice(0, 2).is_in(same_sector_divs))[
            "_cid"
        ].to_list()
    )
    return sector, sector_ids


def compute_sector_benchmark(
    peers: pl.DataFrame,
    company_revenue: float,
    company_gross_margin: float | None,
    company_op_margin: float | None,
    company_net_margin: float | None,
    sector_label: str,
    target_year: int,
) -> SectorBenchmark | None:
    """Compute revenue-weighted benchmarks from a peer DataFrame.

    Returns ``None`` if the peer group is empty or has no valid margin data.

    Parameters
    ----------
    peers:
        Output of :func:`build_peer_group`.
    company_revenue:
        Target company revenue (for metadata).
    company_gross_margin, company_op_margin, company_net_margin:
        Target company margin values (%) for percentile positioning.
    sector_label:
        Human-readable peer-group description for display.
    target_year:
        Fiscal year label.
    """
    rev_col = "turnover_gross_operating_revenue"

    if peers.is_empty():
        return None

    # Compute margins per peer, drop rows with zero/null revenue
    df = peers.filter(
        pl.col(rev_col).is_not_null() & (pl.col(rev_col) > 0)
    ).with_columns(
        [
            (pl.col("gross_profit_loss") / pl.col(rev_col) * 100).alias("_gm"),
            (pl.col("operating_profit_loss") / pl.col(rev_col) * 100).alias("_om"),
            (pl.col("profit_loss_for_period") / pl.col(rev_col) * 100).alias("_nm"),
        ]
    )

    if df.is_empty():
        return None

    revenues = df[rev_col].cast(pl.Float64).to_numpy()

    def _weighted_avg(margin_col: str) -> float | None:
        vals = df[margin_col].cast(pl.Float64).to_numpy()
        mask = ~np.isnan(vals) & (revenues > 0)
        if mask.sum() < 2:
            return None
        return float(np.average(vals[mask], weights=revenues[mask]))

    def _quartiles(margin_col: str) -> tuple[float, float, float] | None:
        arr = df[margin_col].drop_nulls().cast(pl.Float64).to_numpy()
        arr = arr[~np.isnan(arr)]
        if len(arr) < 4:
            return None
        return (
            float(np.percentile(arr, 25)),
            float(np.percentile(arr, 50)),
            float(np.percentile(arr, 75)),
        )

    def _pct_rank(margin_col: str, company_val: float | None) -> float | None:
        if company_val is None or np.isnan(company_val):
            return None
        arr = df[margin_col].drop_nulls().cast(pl.Float64).to_numpy()
        arr = arr[~np.isnan(arr)]
        if len(arr) < 2:
            return None
        return float(stats.percentileofscore(arr, company_val, kind="mean"))

    return SectorBenchmark(
        sector_label=sector_label,
        n_peers=len(df),
        year=target_year,
        peer_revenue_low=float(df[rev_col].min()),
        peer_revenue_high=float(df[rev_col].max()),
        company_revenue=company_revenue,
        wt_gross_margin_pct=_weighted_avg("_gm"),
        wt_operating_margin_pct=_weighted_avg("_om"),
        wt_net_margin_pct=_weighted_avg("_nm"),
        gross_margin_quartiles=_quartiles("_gm"),
        operating_margin_quartiles=_quartiles("_om"),
        net_margin_quartiles=_quartiles("_nm"),
        company_gross_margin_pct=company_gross_margin,
        company_gross_margin_percentile=_pct_rank("_gm", company_gross_margin),
        company_operating_margin_pct=company_op_margin,
        company_operating_margin_percentile=_pct_rank("_om", company_op_margin),
        company_net_margin_pct=company_net_margin,
        company_net_margin_percentile=_pct_rank("_nm", company_net_margin),
    )


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------


def _trend_direction(slope: float, scale: float) -> str:
    if scale == 0:
        return "flat"
    rel = slope / abs(scale)
    if rel > 0.02:
        return "improving"
    if rel < -0.02:
        return "declining"
    return "flat"


def forecast_metric(
    years: list[int],
    values: list[float],
    metric: str,
    display_name: str,
    horizon: int = 3,
) -> ForecastResult | None:
    """Fit a linear trend and project *horizon* years ahead.

    Returns ``None`` if fewer than 2 non-null data points are available.
    """
    # Filter out NaN/None
    clean = [
        (y, v)
        for y, v in zip(years, values, strict=False)
        if v is not None and not np.isnan(v)
    ]
    if len(clean) < 2:
        return None

    xs = np.array([c[0] for c in clean], dtype=float)
    ys = np.array([c[1] for c in clean], dtype=float)

    slope, intercept, r_value, _p, _se = stats.linregress(xs, ys)
    r_squared = r_value**2

    last_year = round(xs[-1])
    forecast_years = list(range(last_year + 1, last_year + horizon + 1))
    forecast_values = [float(slope * y + intercept) for y in forecast_years]

    n_obs = len(clean)
    if n_obs < 3:
        confidence_note = (
            f"Low confidence: only {n_obs} data point(s) — treat as indicative only."
        )
    elif r_squared < 0.5:
        confidence_note = f"Moderate confidence: R²={r_squared:.2f} — trend is noisy."
    else:
        confidence_note = f"Good fit: R²={r_squared:.2f}."

    return ForecastResult(
        metric=metric,
        display_name=display_name,
        historical_years=[round(y) for y in xs],
        historical_values=ys.tolist(),
        forecast_years=forecast_years,
        forecast_values=forecast_values,
        slope=float(slope),
        r_squared=r_squared,
        trend_direction=_trend_direction(slope, float(np.mean(np.abs(ys)))),
        confidence_note=confidence_note,
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

_METRIC_LABELS: dict[str, str] = {
    "turnover_gross_operating_revenue": "Revenue",
    "gross_profit_loss": "Gross Profit",
    "operating_profit_loss": "Operating Profit",
    "profit_loss_for_period": "Net Profit",
    "cost_sales": "Cost of Sales",
    "administrative_expenses": "Admin Expenses",
    "staff_costs": "Staff Costs",
    "current_assets": "Current Assets",
    "debtors": "Debtors",
    "creditors_due_within_one_year": "Creditors (< 1yr)",
    "creditors_due_after_one_year": "Creditors (> 1yr)",
    "net_current_assets_liabilities": "Net Current Assets",
    "total_assets_less_current_liabilities": "Total Assets less CL",
    "net_assets_liabilities_including_pension_asset_liability": "Net Assets",
    "shareholder_funds": "Shareholder Funds",
    "cash_bank_in_hand": "Cash",
    "tangible_fixed_assets": "Tangible Fixed Assets",
    "average_number_employees_during_period": "Employees",
    "gross_margin_pct": "Gross Margin %",
    "operating_margin_pct": "Operating Margin %",
    "net_margin_pct": "Net Margin %",
}


def _ordinal(n: int) -> str:
    """Return ordinal string for integer (1→'1st', 72→'72nd', etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _fmt(v: float | None, is_pct: bool = False, is_headcount: bool = False) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    if is_headcount:
        return f"{round(v):,}"
    if is_pct:
        return f"{v:.1f}%"
    if abs(v) >= 1_000_000:
        return f"£{v / 1_000_000:.2f}m"
    if abs(v) >= 1_000:
        return f"£{v / 1_000:.1f}k"
    return f"£{v:.0f}"


def _section(title: str, width: int = 70) -> str:
    return f"\n{'─' * width}\n{title}\n{'─' * width}"


def _build_report_text(report: CompanyReport) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("  COMPANY FINANCIAL REPORT")
    lines.append(f"  {report.company_name}  (Companies House ID: {report.company_id})")
    lines.append("=" * 70)

    pl_hist = report.pl_history
    bs_hist = report.bs_history

    # ── Overview ──────────────────────────────────────────────────────────
    lines.append(_section("OVERVIEW"))
    if not pl_hist.is_empty():
        first_year = pl_hist["period_end"][0].year
        last_year = pl_hist["period_end"][-1].year
        lines.append(f"  P&L periods covered : {first_year} - {last_year}")
        lines.append(f"  Accounting periods  : {len(pl_hist)}")
    if not bs_hist.is_empty():
        lines.append(f"  Balance-sheet dates : {len(bs_hist)}")
    if pl_hist.is_empty() and bs_hist.is_empty():
        lines.append("  No financial data found for this company.")
        return "\n".join(lines)

    # ── P&L History ───────────────────────────────────────────────────────
    if not pl_hist.is_empty():
        lines.append(_section("PROFIT & LOSS HISTORY"))
        header_cols = [
            ("Period End", 12),
            ("Revenue", 12),
            ("Gross Profit", 13),
            ("Op. Profit", 12),
            ("Net Profit", 12),
            ("Gross Margin", 13),
            ("Op. Margin", 11),
        ]
        header = "  " + "".join(f"{h:<{w}}" for h, w in header_cols)
        lines.append(header)
        lines.append("  " + "-" * (sum(w for _, w in header_cols)))
        for row in pl_hist.iter_rows(named=True):
            pe = str(row["period_end"])
            rev = _fmt(row.get("turnover_gross_operating_revenue"))
            gp = _fmt(row.get("gross_profit_loss"))
            op = _fmt(row.get("operating_profit_loss"))
            np_ = _fmt(row.get("profit_loss_for_period"))
            gm = _fmt(row.get("gross_margin_pct"), is_pct=True)
            om = _fmt(row.get("operating_margin_pct"), is_pct=True)
            lines.append(
                f"  {pe:<12}{rev:<12}{gp:<13}{op:<12}{np_:<12}{gm:<13}{om:<11}"
            )

        # YoY growth
        if "revenue_yoy_growth_pct" in pl_hist.columns and len(pl_hist) > 1:
            lines.append("")
            lines.append("  Revenue YoY growth:")
            for row in pl_hist.iter_rows(named=True):
                g = row.get("revenue_yoy_growth_pct")
                if g is not None and not np.isnan(g):
                    arrow = "▲" if g >= 0 else "▼"
                    lines.append(f"    {row['period_end']}: {arrow} {abs(g):.1f}%")

    # ── Balance Sheet History ─────────────────────────────────────────────
    if not bs_hist.is_empty():
        lines.append(_section("BALANCE SHEET HISTORY"))
        bs_display = [
            ("current_assets", False, False),
            ("cash_bank_in_hand", False, False),
            ("debtors", False, False),
            ("creditors_due_within_one_year", False, False),
            ("net_current_assets_liabilities", False, False),
            ("shareholder_funds", False, False),
            ("average_number_employees_during_period", False, True),
        ]
        # Build header from available dates
        dates = [str(r["period_end"]) for r in bs_hist.iter_rows(named=True)]
        date_col_w = 13
        label_w = 42
        hdr = f"  {'Metric':<{label_w}}" + "".join(f"{d:<{date_col_w}}" for d in dates)
        lines.append(hdr)
        lines.append("  " + "-" * (label_w + date_col_w * len(dates)))
        for col, is_pct, is_head in bs_display:
            if col not in bs_hist.columns:
                continue
            label = _METRIC_LABELS.get(col, col)
            row_vals = []
            for row in bs_hist.iter_rows(named=True):
                row_vals.append(_fmt(row.get(col), is_pct=is_pct, is_headcount=is_head))
            row_str = "".join(f"{v:<{date_col_w}}" for v in row_vals)
            lines.append(f"  {label:<{label_w}}" + row_str)

    # ── Sector Comparison ─────────────────────────────────────────────────
    if report.sector_benchmark is not None:
        lines.extend(_format_sector_section(report.sector_benchmark))

    # ── Forecasts ─────────────────────────────────────────────────────────
    if report.forecasts:
        lines.append(_section("FORECASTS (LINEAR TREND EXTRAPOLATION)"))
        for fc in report.forecasts:
            direction_sym = {"improving": "▲", "declining": "▼", "flat": "→"}[
                fc.trend_direction
            ]
            lines.append(f"\n  {fc.display_name}  {direction_sym}")
            is_pct_metric = "pct" in fc.metric
            slope_str = f"{fc.slope:+.2f}pp" if is_pct_metric else f"{fc.slope:+,.0f}"
            lines.append(f"  Trend: {slope_str} per year | {fc.confidence_note}")
            is_m_pct = "pct" in fc.metric
            # Historical
            lines.append("  Historical:")
            for y, v in zip(fc.historical_years, fc.historical_values, strict=False):
                lines.append(f"    {y}: {_fmt(v, is_pct=is_m_pct)}")
            # Forecast
            lines.append("  Forecast:")
            for y, v in zip(fc.forecast_years, fc.forecast_values, strict=False):
                lines.append(f"    {y}: {_fmt(v, is_pct=is_m_pct)} (projected)")

    # ── Narrative Summary ─────────────────────────────────────────────────
    lines.append(_section("NARRATIVE SUMMARY"))
    _write_narrative(lines, report)

    lines.append("\n" + "=" * 70)
    lines.append("  NOTE: Forecast uses simple linear regression on available data.")
    if report.num_periods < 3:
        lines.append(
            f"  Only {report.num_periods} accounting period(s) found in the dataset — "
            "projections are highly uncertain."
        )
    lines.append("=" * 70 + "\n")

    return "\n".join(lines)


def _write_narrative(lines: list[str], report: CompanyReport) -> None:
    pl_hist = report.pl_history
    if pl_hist.is_empty():
        lines.append("  Insufficient P&L data available for narrative analysis.")
        return

    latest = pl_hist.row(-1, named=True)
    rev = latest.get("turnover_gross_operating_revenue")
    op = latest.get("operating_profit_loss")
    gm = latest.get("gross_margin_pct")
    om = latest.get("operating_margin_pct")

    lines.append(
        f"  In its most recent reported period (ending {latest['period_end']}),"
    )
    if rev:
        lines.append(f"  {report.company_name} reported revenue of {_fmt(rev)},")
    if op:
        profitability = "profitable" if op > 0 else "loss-making"
        lines.append(
            f"  with an operating profit of {_fmt(op)} ({profitability} at the"
            " operating level)."
        )
    if gm:
        lines.append(
            f"  Gross margin: {gm:.1f}%  |  Operating margin: {_fmt(om, is_pct=True)}"
        )

    # Trend commentary
    rev_metric = "turnover_gross_operating_revenue"
    revenue_fcs = [f for f in report.forecasts if f.metric == rev_metric]
    if revenue_fcs:
        fc = revenue_fcs[0]
        lines.append("")
        if fc.trend_direction == "improving":
            lines.append(
                f"  Revenue shows a positive trend (+{fc.slope:,.0f}/yr), and if this"
                f" continues, the company could reach {_fmt(fc.forecast_values[-1])}"
                f" by {fc.forecast_years[-1]}."
            )
        elif fc.trend_direction == "declining":
            lines.append(
                f"  Revenue shows a declining trend ({fc.slope:+,.0f}/yr). If the"
                f" trend continues, revenue could fall to"
                f" {_fmt(fc.forecast_values[-1])} by {fc.forecast_years[-1]}."
            )
        else:
            lines.append("  Revenue is broadly flat over the observed period.")
        lines.append(f"  ({fc.confidence_note})")


def _format_sector_section(bm: SectorBenchmark) -> list[str]:
    """Format the SECTOR COMPARISON section lines."""
    lines: list[str] = []
    lines.append(
        _section(
            f"SECTOR COMPARISON  ({bm.sector_label} | "
            f"{bm.n_peers:,} companies | FY {bm.year})"
        )
    )
    peer_range = (
        f"  Peer revenue range : {_fmt(bm.peer_revenue_low)}"
        f" - {_fmt(bm.peer_revenue_high)}"
    )
    if bm.company_revenue:
        peer_range += f"  |  This company: {_fmt(bm.company_revenue)}"
    lines.append(peer_range)
    if bm.n_peers < 10:
        lines.append(
            f"  Only {bm.n_peers} peers found -- benchmarks may not be representative."
        )
    lines.append("")

    # Table header
    col_widths = (26, 12, 12, 8, 8, 8, 12)
    hdr = (
        f"  {'Metric':<{col_widths[0]}}"
        f"{'This Co':>{col_widths[1]}}"
        f"{'Wt.Avg':>{col_widths[2]}}"
        f"{'p25':>{col_widths[3]}}"
        f"{'p50':>{col_widths[4]}}"
        f"{'p75':>{col_widths[5]}}"
        f"{'Percentile':>{col_widths[6]}}"
    )
    lines.append(hdr)
    lines.append("  " + "-" * (sum(col_widths) + 2))

    def _row(
        label: str,
        co_val: float | None,
        wt_avg: float | None,
        quartiles: tuple[float, float, float] | None,
        pct_rank: float | None,
    ) -> str:
        co_s = _fmt(co_val, is_pct=True) if co_val is not None else "n/a"
        wt_s = _fmt(wt_avg, is_pct=True) if wt_avg is not None else "n/a"
        if quartiles is not None:
            p25_s, p50_s, p75_s = (
                _fmt(quartiles[0], is_pct=True),
                _fmt(quartiles[1], is_pct=True),
                _fmt(quartiles[2], is_pct=True),
            )
        else:
            p25_s = p50_s = p75_s = "n/a"
        pct_s = _ordinal(round(pct_rank)) if pct_rank is not None else "n/a"
        return (
            f"  {label:<{col_widths[0]}}"
            f"{co_s:>{col_widths[1]}}"
            f"{wt_s:>{col_widths[2]}}"
            f"{p25_s:>{col_widths[3]}}"
            f"{p50_s:>{col_widths[4]}}"
            f"{p75_s:>{col_widths[5]}}"
            f"{pct_s:>{col_widths[6]}}"
        )

    lines.append(
        _row(
            "Gross Margin",
            bm.company_gross_margin_pct,
            bm.wt_gross_margin_pct,
            bm.gross_margin_quartiles,
            bm.company_gross_margin_percentile,
        )
    )
    lines.append(
        _row(
            "Operating Margin",
            bm.company_operating_margin_pct,
            bm.wt_operating_margin_pct,
            bm.operating_margin_quartiles,
            bm.company_operating_margin_percentile,
        )
    )
    lines.append(
        _row(
            "Net Margin",
            bm.company_net_margin_pct,
            bm.wt_net_margin_pct,
            bm.net_margin_quartiles,
            bm.company_net_margin_percentile,
        )
    )

    lines.append("")
    lines.append(
        "  Wt.Avg = revenue-weighted average  |  p25/p50/p75 = unweighted quartiles"
    )
    lines.append(
        "  Percentile = company's rank within the peer distribution"
        " (higher = better margin)"
    )
    return lines


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
    """Load, analyse, and forecast for a single company.

    Parameters
    ----------
    company_id:
        Companies House company number (e.g. ``"01873499"``).
    company_name:
        Display name — if omitted, inferred from the data.
    parquet_path:
        Override the default parquet location.
    forecast_horizon:
        Number of years to project forward.
    sic_path:
        Optional path to a SIC code file (parquet or CSV) for sector lookup.

    Returns
    -------
    CompanyReport
        Structured report including history DataFrames and forecast objects.
        Call ``report.report_text`` for the pre-formatted string output.
    """
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

    # ── Sector benchmark ──────────────────────────────────────────────────
    if not merged.is_empty() and "turnover_gross_operating_revenue" in merged.columns:
        _latest_pl = merged.row(-1, named=True)
        _company_rev = _latest_pl.get("turnover_gross_operating_revenue")
        _company_rev_float = float(_company_rev) if _company_rev else None
        if (
            _company_rev_float
            and not np.isnan(_company_rev_float)
            and _company_rev_float > 0
        ):
            _company_rev_f = _company_rev_float
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
                target_revenue=_company_rev_f,
                target_year=_target_year,
                parquet_path=path,
                sector_company_ids=_sector_ids,
                exclude_company_id=company_id,
            )
            report.sector_benchmark = compute_sector_benchmark(
                peers=_peers,
                company_revenue=_company_rev_f,
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

    report.report_text = _build_report_text(report)
    return report


def generate_report(
    company_name_or_id: str,
    parquet_path: Path | None = None,
    forecast_horizon: int = 3,
    sic_path: Path | None = None,
) -> str:
    """Search for a company by name (or exact ID) and return a formatted report.

    Parameters
    ----------
    company_name_or_id:
        Partial company name or exact Companies House number.
    parquet_path:
        Override the default parquet path.
    forecast_horizon:
        Years to project ahead.
    sic_path:
        Optional path to a SIC code file for sector comparison.

    Returns
    -------
    str
        Human-readable performance report.
    """
    # Try exact ID first (purely numeric / typical CH format)
    matches = search_companies(company_name_or_id, parquet_path)

    if matches.is_empty():
        return f"No company found matching '{company_name_or_id}'."

    if len(matches) > 1:
        listing = "\n".join(
            f"  {r['company_id']:12s}  {r['entity_current_legal_name']}"
            for r in matches.iter_rows(named=True)
        )
        # Use the first match but warn
        first_id = matches["company_id"][0]
        first_name = matches["entity_current_legal_name"][0]
        msg = (
            f"Multiple companies matched '{company_name_or_id}':\n{listing}\n\n"
            f"Using: {first_id} - {first_name}\n"
            "(Pass the exact company_id to analyse_company() to pick a specific one.)\n"
        )
    else:
        msg = ""

    chosen_id = matches["company_id"][0]
    chosen_name = matches["entity_current_legal_name"][0]
    report = analyse_company(
        chosen_id, chosen_name, parquet_path, forecast_horizon, sic_path=sic_path
    )
    return msg + report.report_text


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Exel Computer Systems"
    print(generate_report(query))
