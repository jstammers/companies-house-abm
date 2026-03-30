"""Sector benchmarking: peer-group comparison with revenue-weighted margins."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

from companies_house.schema import SIC_TO_SECTOR

logger = logging.getLogger(__name__)

# XBRL instant facts have period_start == period_end; duration facts differ.
_INSTANT_THRESHOLD_DAYS = 5


@dataclass
class SectorBenchmark:
    """Peer-group comparison for a company's key margin metrics.

    All margins are expressed as percentages (e.g. 37.4 means 37.4 %).
    Revenue-weighted averages give more weight to larger companies.
    """

    sector_label: str
    n_peers: int
    year: int
    peer_revenue_low: float
    peer_revenue_high: float
    company_revenue: float | None = None
    # Revenue-weighted sector averages
    wt_gross_margin_pct: float | None = None
    wt_operating_margin_pct: float | None = None
    wt_net_margin_pct: float | None = None
    # Unweighted quartile distributions: (p25, p50, p75)
    gross_margin_quartiles: tuple[float, float, float] | None = None
    operating_margin_quartiles: tuple[float, float, float] | None = None
    net_margin_quartiles: tuple[float, float, float] | None = None
    # Company's own values and percentile rank
    company_gross_margin_pct: float | None = None
    company_gross_margin_percentile: float | None = None
    company_operating_margin_pct: float | None = None
    company_operating_margin_percentile: float | None = None
    company_net_margin_pct: float | None = None
    company_net_margin_percentile: float | None = None


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
    """Return one P&L row per peer company for sector benchmarking."""
    low = target_revenue / revenue_factor
    high = target_revenue * revenue_factor
    year_low = target_year - year_window
    year_high = target_year + year_window

    lf = (
        pl.scan_parquet(parquet_path)
        .filter(
            (pl.col("period_end") - pl.col("period_start")).dt.total_days().abs()
            > _INSTANT_THRESHOLD_DAYS
        )
        .filter(pl.col("period_end").dt.year().is_between(year_low, year_high))
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
    """Look up *company_id* in a SIC code file and return its sector.

    Returns ``(sector_name, frozenset_of_company_ids)`` or
    ``(None, None)`` if the lookup fails.
    """
    try:
        p = Path(sic_path)
        if p.suffix == ".parquet":
            sic_df = pl.read_parquet(p)
        else:
            sic_df = pl.read_csv(p, infer_schema_length=2000)
    except Exception:
        logger.warning("Could not read SIC code file: %s", sic_path, exc_info=True)
        return None, None

    rename: dict[str, str] = {}
    for col in sic_df.columns:
        cl = col.lower()
        if any(
            kw in cl
            for kw in (
                "registered_number",
                "company_number",
                "company_id",
            )
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

    Returns ``None`` if the peer group is empty.
    """
    rev_col = "turnover_gross_operating_revenue"

    if peers.is_empty():
        return None

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

    def _quartiles(
        margin_col: str,
    ) -> tuple[float, float, float] | None:
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
