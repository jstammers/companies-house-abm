"""Report text formatting helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from companies_house.analysis.benchmarks import SectorBenchmark
    from companies_house.analysis.reports import CompanyReport

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
    """Return ordinal string for integer (1->'1st', 72->'72nd', etc.)."""
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
        return f"\u00a3{v / 1_000_000:.2f}m"
    if abs(v) >= 1_000:
        return f"\u00a3{v / 1_000:.1f}k"
    return f"\u00a3{v:.0f}"


def _section(title: str, width: int = 70) -> str:
    return f"\n{'-' * width}\n{title}\n{'-' * width}"


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
            p25_s = _fmt(quartiles[0], is_pct=True)
            p50_s = _fmt(quartiles[1], is_pct=True)
            p75_s = _fmt(quartiles[2], is_pct=True)
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


def build_report_text(report: CompanyReport) -> str:
    """Build the full formatted report text."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("  COMPANY FINANCIAL REPORT")
    lines.append(f"  {report.company_name}  (Companies House ID: {report.company_id})")
    lines.append("=" * 70)

    pl_hist = report.pl_history
    bs_hist = report.bs_history

    # Overview
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

    # P&L History
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

        if "revenue_yoy_growth_pct" in pl_hist.columns and len(pl_hist) > 1:
            lines.append("")
            lines.append("  Revenue YoY growth:")
            for row in pl_hist.iter_rows(named=True):
                g = row.get("revenue_yoy_growth_pct")
                if g is not None and not np.isnan(g):
                    arrow = "^" if g >= 0 else "v"
                    lines.append(f"    {row['period_end']}: {arrow} {abs(g):.1f}%")

    # Balance Sheet History
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
                row_vals.append(
                    _fmt(
                        row.get(col),
                        is_pct=is_pct,
                        is_headcount=is_head,
                    )
                )
            row_str = "".join(f"{v:<{date_col_w}}" for v in row_vals)
            lines.append(f"  {label:<{label_w}}" + row_str)

    # Sector Comparison
    if report.sector_benchmark is not None:
        lines.extend(_format_sector_section(report.sector_benchmark))

    # Forecasts
    if report.forecasts:
        lines.append(_section("FORECASTS (LINEAR TREND EXTRAPOLATION)"))
        for fc in report.forecasts:
            direction_sym = {
                "improving": "^",
                "declining": "v",
                "flat": "->",
            }[fc.trend_direction]
            lines.append(f"\n  {fc.display_name}  {direction_sym}")
            is_pct_metric = "pct" in fc.metric
            slope_str = f"{fc.slope:+.2f}pp" if is_pct_metric else f"{fc.slope:+,.0f}"
            lines.append(f"  Trend: {slope_str} per year | {fc.confidence_note}")
            lines.append("  Historical:")
            for y, v in zip(
                fc.historical_years,
                fc.historical_values,
                strict=False,
            ):
                lines.append(f"    {y}: {_fmt(v, is_pct=is_pct_metric)}")
            lines.append("  Forecast:")
            for y, v in zip(
                fc.forecast_years,
                fc.forecast_values,
                strict=False,
            ):
                lines.append(f"    {y}: {_fmt(v, is_pct=is_pct_metric)} (projected)")

    # Narrative
    lines.append(_section("NARRATIVE SUMMARY"))
    _write_narrative(lines, report)

    lines.append("\n" + "=" * 70)
    lines.append("  NOTE: Forecast uses simple linear regression on available data.")
    if report.num_periods < 3:
        lines.append(
            f"  Only {report.num_periods} accounting period(s) "
            "found in the dataset -- projections are highly uncertain."
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
            f"  with an operating profit of {_fmt(op)} "
            f"({profitability} at the operating level)."
        )
    if gm:
        lines.append(
            f"  Gross margin: {gm:.1f}%  |  Operating margin: {_fmt(om, is_pct=True)}"
        )

    rev_metric = "turnover_gross_operating_revenue"
    revenue_fcs = [f for f in report.forecasts if f.metric == rev_metric]
    if revenue_fcs:
        fc = revenue_fcs[0]
        lines.append("")
        if fc.trend_direction == "improving":
            lines.append(
                f"  Revenue shows a positive trend "
                f"(+{fc.slope:,.0f}/yr), and if this"
                f" continues, the company could reach "
                f"{_fmt(fc.forecast_values[-1])}"
                f" by {fc.forecast_years[-1]}."
            )
        elif fc.trend_direction == "declining":
            lines.append(
                f"  Revenue shows a declining trend "
                f"({fc.slope:+,.0f}/yr). If the"
                f" trend continues, revenue could fall to"
                f" {_fmt(fc.forecast_values[-1])}"
                f" by {fc.forecast_years[-1]}."
            )
        else:
            lines.append("  Revenue is broadly flat over the observed period.")
        lines.append(f"  ({fc.confidence_note})")
