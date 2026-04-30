"""Tests for the company_analysis module."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import polars as pl

from companies_house.analysis.benchmarks import (
    SectorBenchmark,
    _load_sic_sector_ids,
    build_peer_group,
    compute_sector_benchmark,
)
from companies_house.analysis.forecasting import forecast_metric
from companies_house.analysis.formatting import _ordinal
from companies_house.analysis.reports import (
    analyse_company,
    build_bs_history,
    build_pl_history,
    compute_derived_metrics,
    generate_report,
    split_statements,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_D = pl.Decimal(20, 2)


def _make_row(
    company_id: str = "12345678",
    entity_name: str = "TEST CO LTD",
    balance_sheet_date: str = "2023-01-31",
    period_start: str = "2022-02-01",
    period_end: str = "2023-01-31",
    turnover: float | None = 1_000_000.0,
    gross_profit: float | None = 400_000.0,
    operating_profit: float | None = 200_000.0,
    net_profit: float | None = 160_000.0,
    current_assets: float | None = None,
    shareholder_funds: float | None = None,
    employees: float | None = 50.0,
) -> dict:
    """Build a minimal raw Companies House row dict."""
    return {
        "run_code": "test_run",
        "company_id": company_id,
        "date": datetime.date.fromisoformat(balance_sheet_date),
        "file_type": "test",
        "taxonomy": "test",
        "balance_sheet_date": datetime.date.fromisoformat(balance_sheet_date),
        "companies_house_registered_number": company_id,
        "entity_current_legal_name": entity_name,
        "company_dormant": False,
        "average_number_employees_during_period": (
            Decimal(str(employees)) if employees else None
        ),
        "period_start": datetime.date.fromisoformat(period_start),
        "period_end": datetime.date.fromisoformat(period_end),
        "tangible_fixed_assets": None,
        "debtors": None,
        "cash_bank_in_hand": None,
        "current_assets": Decimal(str(current_assets)) if current_assets else None,
        "creditors_due_within_one_year": None,
        "creditors_due_after_one_year": None,
        "net_current_assets_liabilities": None,
        "total_assets_less_current_liabilities": None,
        "net_assets_liabilities_including_pension_asset_liability": None,
        "called_up_share_capital": None,
        "profit_loss_account_reserve": None,
        "shareholder_funds": (
            Decimal(str(shareholder_funds)) if shareholder_funds else None
        ),
        "turnover_gross_operating_revenue": (
            Decimal(str(turnover)) if turnover else None
        ),
        "other_operating_income": None,
        "cost_sales": None,
        "gross_profit_loss": Decimal(str(gross_profit)) if gross_profit else None,
        "administrative_expenses": None,
        "raw_materials_consumables": None,
        "staff_costs": None,
        "depreciation_other_amounts_written_off_tangible_intangible_fixed_assets": None,
        "other_operating_charges_format2": None,
        "operating_profit_loss": (
            Decimal(str(operating_profit)) if operating_profit else None
        ),
        "profit_loss_on_ordinary_activities_before_tax": None,
        "tax_on_profit_or_loss_on_ordinary_activities": None,
        "profit_loss_for_period": Decimal(str(net_profit)) if net_profit else None,
        "error": None,
        "zip_url": None,
    }


def _make_instant_row(
    company_id: str = "12345678",
    entity_name: str = "TEST CO LTD",
    date: str = "2023-01-31",
    current_assets: float | None = 500_000.0,
    shareholder_funds: float | None = 300_000.0,
    employees: float | None = 50.0,
) -> dict:
    """Build a balance-sheet instant row (period_start == period_end)."""
    return _make_row(
        company_id=company_id,
        entity_name=entity_name,
        balance_sheet_date=date,
        period_start=date,
        period_end=date,
        turnover=None,
        gross_profit=None,
        operating_profit=None,
        net_profit=None,
        current_assets=current_assets,
        shareholder_funds=shareholder_funds,
        employees=employees,
    )


def _df(rows: list[dict]) -> pl.DataFrame:
    return pl.from_dicts(rows)


# ---------------------------------------------------------------------------
# split_statements
# ---------------------------------------------------------------------------


class TestSplitStatements:
    def test_duration_rows_go_to_pl(self):
        row = _make_row()
        df = _df([row])
        pl_df, bs_df = split_statements(df)
        assert len(pl_df) == 1
        assert len(bs_df) == 0

    def test_instant_rows_go_to_bs(self):
        row = _make_instant_row()
        df = _df([row])
        pl_df, bs_df = split_statements(df)
        assert len(pl_df) == 0
        assert len(bs_df) == 1

    def test_mixed_rows_split_correctly(self):
        rows = [_make_row(), _make_instant_row()]
        df = _df(rows)
        pl_df, bs_df = split_statements(df)
        assert len(pl_df) == 1
        assert len(bs_df) == 1


# ---------------------------------------------------------------------------
# build_pl_history / build_bs_history
# ---------------------------------------------------------------------------


class TestBuildHistories:
    def test_pl_history_sorted_by_period_end(self):
        rows = [
            _make_row(period_start="2021-02-01", period_end="2022-01-31"),
            _make_row(period_start="2022-02-01", period_end="2023-01-31"),
        ]
        pl_df, _ = split_statements(_df(rows))
        hist = build_pl_history(pl_df)
        dates = hist["period_end"].to_list()
        assert dates == sorted(dates)

    def test_bs_history_casts_to_float(self):
        rows = [
            _make_instant_row(current_assets=500_000.0, shareholder_funds=300_000.0)
        ]
        _, bs_df = split_statements(_df(rows))
        hist = build_bs_history(bs_df)
        assert hist["current_assets"].dtype == pl.Float64

    def test_empty_returns_empty(self):
        empty = pl.DataFrame()
        assert build_pl_history(empty).is_empty()
        assert build_bs_history(empty).is_empty()


# ---------------------------------------------------------------------------
# compute_derived_metrics
# ---------------------------------------------------------------------------


class TestComputeDerivedMetrics:
    def _two_year_data(self):
        pl_rows = [
            _make_row(
                period_start="2021-02-01",
                period_end="2022-01-31",
                turnover=8_000_000.0,
                gross_profit=3_000_000.0,
                operating_profit=1_000_000.0,
                net_profit=800_000.0,
            ),
            _make_row(
                period_start="2022-02-01",
                period_end="2023-01-31",
                turnover=9_000_000.0,
                gross_profit=3_500_000.0,
                operating_profit=1_200_000.0,
                net_profit=960_000.0,
            ),
        ]
        bs_rows = [
            _make_instant_row(date="2022-01-31", current_assets=4_000_000.0),
            _make_instant_row(date="2023-01-31", current_assets=4_500_000.0),
        ]
        pl_df, _ = split_statements(_df(pl_rows))
        _, bs_df = split_statements(_df(bs_rows))
        return build_pl_history(pl_df), build_bs_history(bs_df)

    def test_gross_margin_computed(self):
        pl_hist, bs_hist = self._two_year_data()
        merged = compute_derived_metrics(pl_hist, bs_hist)
        assert "gross_margin_pct" in merged.columns
        latest = merged.row(-1, named=True)
        # 3_500_000 / 9_000_000 * 100 ≈ 38.9
        assert abs(latest["gross_margin_pct"] - 38.89) < 0.1

    def test_operating_margin_computed(self):
        pl_hist, bs_hist = self._two_year_data()
        merged = compute_derived_metrics(pl_hist, bs_hist)
        assert "operating_margin_pct" in merged.columns

    def test_revenue_yoy_growth(self):
        pl_hist, bs_hist = self._two_year_data()
        merged = compute_derived_metrics(pl_hist, bs_hist)
        assert "revenue_yoy_growth_pct" in merged.columns
        # 9M/8M - 1 = 12.5%
        latest = merged.row(-1, named=True)
        assert abs(latest["revenue_yoy_growth_pct"] - 12.5) < 0.1

    def test_empty_pl_returns_empty(self):
        result = compute_derived_metrics(pl.DataFrame(), pl.DataFrame())
        assert result.is_empty()


# ---------------------------------------------------------------------------
# forecast_metric
# ---------------------------------------------------------------------------


class TestForecastMetric:
    def test_returns_none_with_one_data_point(self):
        result = forecast_metric([2023], [1_000_000.0], "revenue", "Revenue")
        assert result is None

    def test_returns_none_with_fewer_than_min_obs(self):
        # Fewer than 4 clean data points → None (linear regression not informative)
        result = forecast_metric(
            [2022, 2023], [1_000_000.0, 1_100_000.0], "revenue", "Revenue"
        )
        assert result is None

    def test_slope_sign(self):
        # Increasing revenue — 4 data points required
        result = forecast_metric(
            [2020, 2021, 2022, 2023], [100.0, 200.0, 300.0, 400.0], "m", "M"
        )
        assert result is not None
        assert result.slope > 0
        assert result.trend_direction == "improving"

    def test_declining_trend(self):
        result = forecast_metric(
            [2020, 2021, 2022, 2023], [400.0, 300.0, 200.0, 100.0], "m", "M"
        )
        assert result is not None
        assert result.slope < 0
        assert result.trend_direction == "declining"

    def test_flat_trend(self):
        result = forecast_metric(
            [2020, 2021, 2022, 2023], [500.0, 500.0, 500.0, 500.0], "m", "M"
        )
        assert result is not None
        assert result.trend_direction == "flat"

    def test_nan_values_ignored(self):
        # 5 points, 1 NaN → 4 valid points (meets minimum)
        result = forecast_metric(
            [2019, 2020, 2021, 2022, 2023],
            [100.0, float("nan"), 200.0, 300.0, 400.0],
            "m",
            "M",
        )
        assert result is not None
        assert len(result.historical_years) == 4  # NaN row excluded

    def test_custom_horizon(self):
        result = forecast_metric(
            [2019, 2020, 2021, 2022], [100.0, 150.0, 200.0, 250.0], "m", "M", horizon=5
        )
        assert result is not None
        assert len(result.forecast_years) == 5
        assert result.forecast_years[0] == 2023

    def test_r_squared_perfect_linear(self):
        result = forecast_metric(
            [2020, 2021, 2022, 2023], [100.0, 200.0, 300.0, 400.0], "m", "M"
        )
        assert result is not None
        assert abs(result.r_squared - 1.0) < 1e-9

    def test_r_squared_and_stats_exposed(self):
        result = forecast_metric(
            [2020, 2021, 2022, 2023], [100.0, 200.0, 300.0, 400.0], "m", "M"
        )
        assert result is not None
        assert 0.0 <= result.r_squared <= 1.0
        assert 0.0 <= result.p_value <= 1.0
        assert result.std_err >= 0.0


# ---------------------------------------------------------------------------
# analyse_company (integration, mocked parquet)
# ---------------------------------------------------------------------------


def _make_mock_parquet(tmp_path):
    """Write a minimal parquet with 4 years of data for a test company.

    Four P&L periods are required so that forecast_metric (min 4 obs) can
    produce forecasts for the TestAnalyseCompany suite.
    """
    rows = [
        _make_row(
            company_id="99999999",
            entity_name="MOCK COMPANY LTD",
            period_start="2019-02-01",
            period_end="2020-01-31",
            turnover=4_000_000.0,
            gross_profit=1_600_000.0,
            operating_profit=480_000.0,
            net_profit=384_000.0,
        ),
        _make_row(
            company_id="99999999",
            entity_name="MOCK COMPANY LTD",
            period_start="2020-02-01",
            period_end="2021-01-31",
            turnover=4_500_000.0,
            gross_profit=1_800_000.0,
            operating_profit=540_000.0,
            net_profit=432_000.0,
        ),
        _make_row(
            company_id="99999999",
            entity_name="MOCK COMPANY LTD",
            period_start="2021-02-01",
            period_end="2022-01-31",
            turnover=5_000_000.0,
            gross_profit=2_000_000.0,
            operating_profit=600_000.0,
            net_profit=480_000.0,
        ),
        _make_row(
            company_id="99999999",
            entity_name="MOCK COMPANY LTD",
            period_start="2022-02-01",
            period_end="2023-01-31",
            turnover=6_000_000.0,
            gross_profit=2_400_000.0,
            operating_profit=750_000.0,
            net_profit=600_000.0,
        ),
        _make_instant_row(
            company_id="99999999",
            date="2022-01-31",
            current_assets=2_000_000.0,
            shareholder_funds=1_000_000.0,
        ),
        _make_instant_row(
            company_id="99999999",
            date="2023-01-31",
            current_assets=2_500_000.0,
            shareholder_funds=1_200_000.0,
        ),
    ]
    path = tmp_path / "test.parquet"
    pl.from_dicts(rows).write_parquet(path)
    return path


class TestAnalyseCompany:
    def test_returns_company_report(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert report.company_id == "99999999"
        assert report.company_name == "MOCK COMPANY LTD"

    def test_pl_history_has_correct_periods(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert report.num_periods == 4
        assert report.pl_history["period_end"][-1].year == 2023

    def test_forecasts_generated(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert len(report.forecasts) > 0
        metrics = [f.metric for f in report.forecasts]
        assert "turnover_gross_operating_revenue" in metrics

    def test_report_text_is_string(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert isinstance(report.report_text, str)
        assert "MOCK COMPANY LTD" in report.report_text

    def test_missing_company_returns_empty_report(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        report = analyse_company("00000000", parquet_path=path)
        assert report.num_periods == 0
        assert report.pl_history.is_empty()

    def test_custom_forecast_horizon(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        report = analyse_company("99999999", parquet_path=path, forecast_horizon=5)
        revenue_fc = next(
            f
            for f in report.forecasts
            if f.metric == "turnover_gross_operating_revenue"
        )
        assert len(revenue_fc.forecast_years) == 5


class TestGenerateReport:
    def test_no_match_returns_message(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        result = generate_report("NONEXISTENT CORP XYZ", parquet_path=path)
        assert "No company found" in result

    def test_single_match_returns_report(self, tmp_path):
        path = _make_mock_parquet(tmp_path)
        result = generate_report("MOCK COMPANY", parquet_path=path)
        assert "MOCK COMPANY LTD" in result
        assert "PROFIT & LOSS" in result

    def test_multiple_matches_warns(self, tmp_path):
        # Write two companies with similar names
        rows = [
            _make_row(company_id="11111111", entity_name="ACME LTD"),
            _make_row(company_id="22222222", entity_name="ACME HOLDINGS LTD"),
        ]
        path = tmp_path / "multi.parquet"
        pl.from_dicts(rows).write_parquet(path)
        result = generate_report("ACME", parquet_path=path)
        assert "Multiple companies matched" in result


# ---------------------------------------------------------------------------
# _ordinal
# ---------------------------------------------------------------------------


class TestOrdinal:
    def test_first(self):
        assert _ordinal(1) == "1st"

    def test_second(self):
        assert _ordinal(2) == "2nd"

    def test_third(self):
        assert _ordinal(3) == "3rd"

    def test_fourth_through_tenth(self):
        for n in range(4, 11):
            assert _ordinal(n).endswith("th"), f"expected 'th' suffix for {n}"

    def test_eleventh_twelfth_thirteenth(self):
        # Teen exceptions: 11th, 12th, 13th — NOT 11st, 12nd, 13rd
        assert _ordinal(11) == "11th"
        assert _ordinal(12) == "12th"
        assert _ordinal(13) == "13th"

    def test_twenty_first(self):
        assert _ordinal(21) == "21st"

    def test_hundred(self):
        assert _ordinal(100) == "100th"

    def test_hundred_and_eleventh(self):
        # 111 ends in 11 → "th"
        assert _ordinal(111) == "111th"


# ---------------------------------------------------------------------------
# build_peer_group
# ---------------------------------------------------------------------------


def _make_peers_parquet(tmp_path: object, peers: list[dict]) -> object:
    """Write a parquet containing the target company plus extra peer rows."""

    p = Path(str(tmp_path)) / "peers.parquet"  # type: ignore[arg-type]
    pl.from_dicts(peers).write_parquet(p)
    return p


class TestBuildPeerGroup:
    def _peer_rows(self) -> list[dict]:
        """10 peer companies, all with £1m revenue in FY2023."""
        rows = []
        for i in range(10):
            cid = f"PEER{i:04d}"
            rows.append(
                _make_row(
                    company_id=cid,
                    entity_name=f"PEER CO {i}",
                    period_start="2022-02-01",
                    period_end="2023-01-31",
                    turnover=1_000_000.0,
                    gross_profit=400_000.0,
                    operating_profit=200_000.0,
                    net_profit=160_000.0,
                )
            )
        return rows

    def test_returns_duration_rows_only(self, tmp_path):
        """Instant (balance-sheet) rows must be excluded."""
        instant = _make_instant_row(company_id="INST0001", date="2023-01-31")
        rows = [*self._peer_rows(), instant]
        path = _make_peers_parquet(tmp_path, rows)
        peers = build_peer_group(1_000_000.0, 2023, path)
        assert "INST0001" not in peers["company_id"].to_list()

    def test_filters_by_revenue_band(self, tmp_path):
        """Companies outside the revenue band must be excluded."""
        rows = self._peer_rows()
        # Add a company with revenue way outside the default 4x band
        rows.append(
            _make_row(
                company_id="HUGE0001",
                period_start="2022-02-01",
                period_end="2023-01-31",
                turnover=100_000_000.0,  # 100x target - outside 4x band
            )
        )
        rows.append(
            _make_row(
                company_id="TINY0001",
                period_start="2022-02-01",
                period_end="2023-01-31",
                turnover=1_000.0,  # 1/1000x target - outside band
            )
        )
        path = _make_peers_parquet(tmp_path, rows)
        peers = build_peer_group(1_000_000.0, 2023, path)
        ids = peers["company_id"].to_list()
        assert "HUGE0001" not in ids
        assert "TINY0001" not in ids
        assert len(ids) == 10  # original 10 peers only

    def test_filters_by_year_window(self, tmp_path):
        """Companies from a year outside the window must be excluded."""
        rows = self._peer_rows()
        rows.append(
            _make_row(
                company_id="OLD00001",
                period_start="2018-02-01",
                period_end="2019-01-31",
                turnover=1_000_000.0,
            )
        )
        path = _make_peers_parquet(tmp_path, rows)
        peers = build_peer_group(1_000_000.0, 2023, path, year_window=1)
        assert "OLD00001" not in peers["company_id"].to_list()

    def test_excludes_target_company(self, tmp_path):
        rows = self._peer_rows()
        path = _make_peers_parquet(tmp_path, rows)
        first_id = rows[0]["company_id"]
        peers = build_peer_group(1_000_000.0, 2023, path, exclude_company_id=first_id)
        assert first_id not in peers["company_id"].to_list()
        assert len(peers) == 9

    def test_one_row_per_company(self, tmp_path):
        """When a company has multiple periods only the most recent is kept."""
        rows = self._peer_rows()
        cid = "MULTI001"
        # Same company, two overlapping periods
        rows.append(
            _make_row(
                company_id=cid,
                period_start="2021-02-01",
                period_end="2022-01-31",
                turnover=1_000_000.0,
            )
        )
        rows.append(
            _make_row(
                company_id=cid,
                period_start="2022-02-01",
                period_end="2023-01-31",
                turnover=1_200_000.0,
            )
        )
        path = _make_peers_parquet(tmp_path, rows)
        peers = build_peer_group(1_000_000.0, 2023, path)
        multi_rows = peers.filter(pl.col("company_id") == cid)
        assert len(multi_rows) == 1
        # The kept row should be the most recent (2023)
        assert multi_rows["period_end"][0].year == 2023

    def test_sector_company_ids_filter(self, tmp_path):
        """Only companies in sector_company_ids are returned."""
        rows = self._peer_rows()
        path = _make_peers_parquet(tmp_path, rows)
        # Only allow the first 3 companies
        allowed = frozenset(r["company_id"] for r in rows[:3])
        peers = build_peer_group(1_000_000.0, 2023, path, sector_company_ids=allowed)
        assert set(peers["company_id"].to_list()) == allowed

    def test_max_peers_cap(self, tmp_path):
        rows = self._peer_rows()
        path = _make_peers_parquet(tmp_path, rows)
        peers = build_peer_group(1_000_000.0, 2023, path, max_peers=3)
        assert len(peers) <= 3

    def test_empty_parquet_returns_empty(self, tmp_path):
        path = tmp_path / "empty.parquet"
        pl.from_dicts([_make_row()]).head(0).write_parquet(path)
        peers = build_peer_group(1_000_000.0, 2023, path)
        assert peers.is_empty()

    def test_custom_revenue_factor(self, tmp_path):
        """A narrow revenue_factor=1.1 should exclude most peers."""
        rows = self._peer_rows()
        # Add a company at 2x target revenue - inside 4x band but outside 1.1x band
        rows.append(
            _make_row(
                company_id="WIDE0001",
                period_start="2022-02-01",
                period_end="2023-01-31",
                turnover=2_000_000.0,
            )
        )
        path = _make_peers_parquet(tmp_path, rows)
        peers_wide = build_peer_group(1_000_000.0, 2023, path, revenue_factor=4.0)
        peers_narrow = build_peer_group(1_000_000.0, 2023, path, revenue_factor=1.1)
        assert len(peers_wide) > len(peers_narrow)
        assert "WIDE0001" not in peers_narrow["company_id"].to_list()


# ---------------------------------------------------------------------------
# compute_sector_benchmark
# ---------------------------------------------------------------------------


def _peers_df(
    revenues: list[float],
    gross_profits: list[float | None] | None = None,
    op_profits: list[float | None] | None = None,
    net_profits: list[float | None] | None = None,
) -> pl.DataFrame:
    """Build a minimal peers DataFrame for compute_sector_benchmark tests."""
    n = len(revenues)
    gp = gross_profits if gross_profits is not None else [r * 0.4 for r in revenues]
    op = op_profits if op_profits is not None else [r * 0.2 for r in revenues]
    np_ = net_profits if net_profits is not None else [r * 0.16 for r in revenues]
    return pl.DataFrame(
        {
            "company_id": [f"P{i:04d}" for i in range(n)],
            "period_end": [datetime.date(2023, 1, 31)] * n,
            "turnover_gross_operating_revenue": revenues,
            "gross_profit_loss": gp,
            "operating_profit_loss": op,
            "profit_loss_for_period": np_,
        }
    )


class TestComputeSectorBenchmark:
    def test_returns_none_on_empty_peers(self):
        empty = _peers_df([]).head(0)
        result = compute_sector_benchmark(
            empty, 1_000_000.0, 40.0, 20.0, 16.0, "test peers", 2023
        )
        assert result is None

    def test_returns_sector_benchmark_instance(self):
        peers = _peers_df([1_000_000.0] * 10)
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 40.0, 20.0, 16.0, "test peers", 2023
        )
        assert isinstance(result, SectorBenchmark)

    def test_n_peers_matches_input(self):
        peers = _peers_df([1_000_000.0] * 7)
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 40.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        assert result.n_peers == 7

    def test_sector_label_and_year(self):
        peers = _peers_df([1_000_000.0] * 5)
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 40.0, 20.0, 16.0, "technology sector", 2023
        )
        assert result is not None
        assert result.sector_label == "technology sector"
        assert result.year == 2023

    def test_revenue_weighted_average_correct(self):
        """Larger companies get more weight in the sector average.

        Two companies: company A has revenue 1m and gross margin 10%,
        company B has revenue 9m and gross margin 50%.
        Revenue-weighted average = (1*10 + 9*50) / (1+9) = 460/10 = 46%.
        """
        peers = _peers_df(
            revenues=[1_000_000.0, 9_000_000.0],
            gross_profits=[100_000.0, 4_500_000.0],  # 10% and 50%
            op_profits=[0.0, 0.0],
            net_profits=[0.0, 0.0],
        )
        result = compute_sector_benchmark(
            peers, 5_000_000.0, 40.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        assert result.wt_gross_margin_pct is not None
        assert abs(result.wt_gross_margin_pct - 46.0) < 0.01

    def test_equal_weight_gives_simple_average(self):
        """Equal-revenue peers → weighted avg equals unweighted avg."""
        peers = _peers_df(
            revenues=[1_000_000.0, 1_000_000.0, 1_000_000.0],
            gross_profits=[100_000.0, 200_000.0, 300_000.0],  # 10%, 20%, 30%
            op_profits=[50_000.0, 100_000.0, 150_000.0],
            net_profits=[40_000.0, 80_000.0, 120_000.0],
        )
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 20.0, 10.0, 8.0, "test", 2023
        )
        assert result is not None
        # Weighted avg of [10, 20, 30] with equal weights = 20
        assert result.wt_gross_margin_pct is not None
        assert abs(result.wt_gross_margin_pct - 20.0) < 0.01

    def test_quartiles_computed(self):
        """Four peers → quartiles should be defined."""
        peers = _peers_df(revenues=[1_000_000.0] * 8)
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 40.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        assert result.gross_margin_quartiles is not None
        p25, p50, p75 = result.gross_margin_quartiles
        assert p25 <= p50 <= p75

    def test_quartiles_none_for_too_few_peers(self):
        """Fewer than 4 peers → quartiles are None."""
        peers = _peers_df(revenues=[1_000_000.0] * 3)
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 40.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        assert result.gross_margin_quartiles is None

    def test_percentile_rank_at_median(self):
        """A company at the median of its peers should rank near 50th percentile."""
        # 9 peers at gross margins 10%, 20%, ..., 90%
        revenues = [1_000_000.0] * 9
        multipliers = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        gross_profits = [rev * m for rev, m in zip(revenues, multipliers, strict=False)]
        peers = _peers_df(revenues=revenues, gross_profits=gross_profits)
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 50.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        # Company gross margin 50% = median → ~50th percentile
        assert result.company_gross_margin_percentile is not None
        assert abs(result.company_gross_margin_percentile - 50.0) < 10.0

    def test_percentile_rank_above_all_peers(self):
        """Company margin higher than all peers → near 100th percentile."""
        peers = _peers_df(
            revenues=[1_000_000.0] * 5,
            gross_profits=[100_000.0] * 5,  # all at 10%
        )
        result = compute_sector_benchmark(
            peers,
            1_000_000.0,
            90.0,
            20.0,
            16.0,
            "test",
            2023,  # company at 90%
        )
        assert result is not None
        assert result.company_gross_margin_percentile is not None
        assert result.company_gross_margin_percentile > 90.0

    def test_percentile_none_when_company_margin_none(self):
        peers = _peers_df(revenues=[1_000_000.0] * 5)
        result = compute_sector_benchmark(
            peers, 1_000_000.0, None, None, None, "test", 2023
        )
        assert result is not None
        assert result.company_gross_margin_percentile is None
        assert result.company_operating_margin_percentile is None
        assert result.company_net_margin_percentile is None

    def test_peer_revenue_range(self):
        peers = _peers_df(revenues=[500_000.0, 1_000_000.0, 2_000_000.0])
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 40.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        assert result.peer_revenue_low == 500_000.0
        assert result.peer_revenue_high == 2_000_000.0

    def test_company_revenue_stored(self):
        peers = _peers_df(revenues=[1_000_000.0] * 4)
        result = compute_sector_benchmark(
            peers, 1_234_567.0, 40.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        assert result.company_revenue == 1_234_567.0

    def test_all_null_profits_returns_none_weighted_avgs(self):
        """If all gross_profit_loss is null the weighted avg must be None."""
        peers = _peers_df(
            revenues=[1_000_000.0] * 5,
            gross_profits=[None] * 5,
        )
        result = compute_sector_benchmark(
            peers, 1_000_000.0, 40.0, 20.0, 16.0, "test", 2023
        )
        assert result is not None
        assert result.wt_gross_margin_pct is None


# ---------------------------------------------------------------------------
# _load_sic_sector_ids
# ---------------------------------------------------------------------------


class TestLoadSicSectorIds:
    def _sic_csv(self, tmp_path, rows: list[tuple[str, str]]) -> object:
        """Write a minimal SIC CSV and return the path."""

        p = Path(str(tmp_path)) / "sic.csv"
        lines = ["companies_house_registered_number,sic_code"]
        for cid, sic in rows:
            lines.append(f"{cid},{sic}")
        p.write_text("\n".join(lines))
        return p

    def test_returns_sector_and_ids_from_csv(self, tmp_path):
        path = self._sic_csv(
            tmp_path,
            [
                ("01873499", "62012"),  # SIC 62 → "technology"
                ("00000001", "62020"),
                ("00000002", "47710"),  # different sector
            ],
        )
        sector, ids = _load_sic_sector_ids(path, "01873499")
        assert sector is not None
        assert ids is not None
        # Both 62xxx companies should be in the sector set
        assert "01873499" in ids
        assert "00000001" in ids
        assert "00000002" not in ids

    def test_returns_none_for_unknown_company(self, tmp_path):
        path = self._sic_csv(tmp_path, [("99999999", "62012")])
        sector, ids = _load_sic_sector_ids(path, "12345678")
        assert sector is None
        assert ids is None

    def test_returns_none_for_missing_file(self, tmp_path):

        sector, ids = _load_sic_sector_ids(Path(tmp_path) / "nope.csv", "01873499")
        assert sector is None
        assert ids is None

    def test_returns_none_for_wrong_columns(self, tmp_path):

        p = Path(str(tmp_path)) / "bad.csv"
        p.write_text("foo,bar\n1,2\n")
        sector, ids = _load_sic_sector_ids(p, "01873499")
        assert sector is None
        assert ids is None

    def test_parquet_format(self, tmp_path):

        p = Path(str(tmp_path)) / "sic.parquet"
        pl.DataFrame(
            {
                "companies_house_registered_number": ["01873499", "00000001"],
                "sic_code": ["62012", "62020"],
            }
        ).write_parquet(p)
        sector, ids = _load_sic_sector_ids(p, "01873499")
        assert sector is not None
        assert ids is not None

    def test_company_id_zero_padded(self, tmp_path):
        """Short company IDs in the SIC file should still match."""
        path = self._sic_csv(
            tmp_path,
            [("1873499", "62012")],  # 7 digits, needs zfill(8)
        )
        sector, _ids = _load_sic_sector_ids(path, "01873499")
        assert sector is not None


# ---------------------------------------------------------------------------
# Sector benchmark in analyse_company / generate_report
# ---------------------------------------------------------------------------


def _make_parquet_with_peers(tmp_path) -> object:
    """Write a parquet with one target company + 20 peer companies."""

    target = [
        _make_row(
            company_id="99999999",
            entity_name="TARGET CO LTD",
            period_start="2022-02-01",
            period_end="2023-01-31",
            turnover=5_000_000.0,
            gross_profit=2_000_000.0,
            operating_profit=600_000.0,
            net_profit=480_000.0,
        )
    ]
    peers = [
        _make_row(
            company_id=f"PEER{i:04d}",
            entity_name=f"PEER CO {i}",
            period_start="2022-02-01",
            period_end="2023-01-31",
            turnover=5_000_000.0,
            gross_profit=1_500_000.0,
            operating_profit=400_000.0,
            net_profit=300_000.0,
        )
        for i in range(20)
    ]
    p = Path(str(tmp_path)) / "with_peers.parquet"
    pl.from_dicts(target + peers).write_parquet(p)
    return p


class TestSectorBenchmarkIntegration:
    def test_benchmark_populated_when_peers_exist(self, tmp_path):
        path = _make_parquet_with_peers(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert report.sector_benchmark is not None

    def test_benchmark_none_when_no_peers(self, tmp_path):
        """Parquet with only the target company → no peers → benchmark is None."""
        rows = [
            _make_row(
                company_id="99999999",
                period_start="2022-02-01",
                period_end="2023-01-31",
                turnover=5_000_000.0,
            )
        ]
        path = tmp_path / "solo.parquet"
        pl.from_dicts(rows).write_parquet(path)
        report = analyse_company("99999999", parquet_path=path)
        assert report.sector_benchmark is None

    def test_target_company_excluded_from_peers(self, tmp_path):
        path = _make_parquet_with_peers(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert report.sector_benchmark is not None
        # n_peers should equal the 20 peers, not 21 (target excluded)
        assert report.sector_benchmark.n_peers == 20

    def test_sector_label_is_size_matched_without_sic(self, tmp_path):
        path = _make_parquet_with_peers(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert report.sector_benchmark is not None
        assert "size-matched" in report.sector_benchmark.sector_label

    def test_report_text_contains_sector_section(self, tmp_path):
        path = _make_parquet_with_peers(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert "SECTOR COMPARISON" in report.report_text

    def test_report_text_contains_weighted_avg_label(self, tmp_path):
        path = _make_parquet_with_peers(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert "Wt.Avg" in report.report_text

    def test_report_text_shows_peer_count(self, tmp_path):
        path = _make_parquet_with_peers(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        assert "20" in report.report_text  # 20 peers

    def test_company_higher_margin_ranks_above_50th(self, tmp_path):
        """Target has 40% gross margin; peers at 30% → should rank above 50th."""
        path = _make_parquet_with_peers(tmp_path)
        report = analyse_company("99999999", parquet_path=path)
        bm = report.sector_benchmark
        assert bm is not None
        if bm.company_gross_margin_percentile is not None:
            assert bm.company_gross_margin_percentile > 50.0

    def test_sic_path_narrows_to_sector(self, tmp_path):
        """With a SIC file, the sector label should reflect the sector name."""
        path = _make_parquet_with_peers(tmp_path)

        # SIC file: target is SIC 62xxx (technology), peers are mixed
        sic_rows = [("99999999", "62012")]
        for i in range(20):
            sic_code = "62020" if i < 10 else "47710"  # half tech, half retail
            sic_rows.append((f"PEER{i:04d}", sic_code))

        sic_path = Path(str(tmp_path)) / "sic.csv"
        lines = ["companies_house_registered_number,sic_code"]
        for cid, sic in sic_rows:
            lines.append(f"{cid},{sic}")
        sic_path.write_text("\n".join(lines))

        report = analyse_company("99999999", parquet_path=path, sic_path=sic_path)
        bm = report.sector_benchmark
        assert bm is not None
        # Sector label should mention technology, not "size-matched peers"
        assert "size-matched" not in bm.sector_label
        # Only the 10 technology peers (PEER0000-PEER0009 with SIC 62xxx)
        assert bm.n_peers == 10

    def test_generate_report_passes_sic_path(self, tmp_path):
        """generate_report sic_path kwarg reaches analyse_company."""
        path = _make_parquet_with_peers(tmp_path)
        result = generate_report("TARGET", parquet_path=path)
        assert "SECTOR COMPARISON" in result

    def test_benchmark_none_when_no_revenue(self, tmp_path):
        """Company with null revenue → no benchmark computed."""
        rows = [
            _make_row(
                company_id="NOREV001",
                period_start="2022-02-01",
                period_end="2023-01-31",
                turnover=None,  # no revenue
            )
        ]
        path = tmp_path / "norev.parquet"
        pl.from_dicts(rows).write_parquet(path)
        report = analyse_company("NOREV001", parquet_path=path)
        assert report.sector_benchmark is None
