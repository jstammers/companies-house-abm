"""Tests for the standalone financial-crash module (Phase 1).

See ``docs/financial-market-crash.md``. Covers the core mechanisms M1-M8:
leveraged position-taking, procyclical haircuts, margin calls, price impact,
capital-limited liquidity supply, mark-to-market, overlapping portfolios and
insolvency/resolution.
"""

from __future__ import annotations

import numpy as np
import pytest

from companies_house_abm.abm.agents.dealer import Dealer
from companies_house_abm.abm.agents.investor import LeveragedInvestor
from companies_house_abm.abm.assets.security import RiskyAsset
from companies_house_abm.abm.config import (
    FinancialMarketConfig,
    InvestorConfig,
    MarginConfig,
    RiskyAssetConfig,
)
from companies_house_abm.abm.financial_model import FinancialSimulation
from companies_house_abm.abm.markets.funding import compute_haircuts
from companies_house_abm.reporting.financial_metrics import (
    autocorrelation,
    excess_kurtosis,
    hill_tail_exponent,
    max_drawdown,
    skewness,
    stylised_facts_report,
)


def _small_config(**overrides) -> FinancialMarketConfig:
    defaults = {
        "days": 60,
        "assets": RiskyAssetConfig(count=4),
        "investors": InvestorConfig(count=20),
    }
    defaults.update(overrides)
    return FinancialMarketConfig(**defaults)


class TestRiskyAsset:
    def test_daily_return_and_mispricing(self):
        asset = RiskyAsset(price=110.0, previous_price=100.0, fundamental_value=120.0)
        assert asset.daily_return == pytest.approx(0.10)
        assert asset.mispricing == pytest.approx((120.0 - 110.0) / 110.0)

    def test_volatility_floor_prevents_collapse(self):
        asset = RiskyAsset(price=100.0, previous_price=100.0, realised_volatility=0.01)
        for _ in range(200):
            asset.update_volatility(ewma_lambda=0.94, floor=0.001)
        assert asset.realised_volatility == pytest.approx(0.001)

    def test_roll_resets_return_anchor(self):
        asset = RiskyAsset(price=105.0, previous_price=100.0)
        asset.roll()
        assert asset.daily_return == 0.0


class TestFunding:
    def test_haircuts_procyclical(self):
        vol = np.array([0.01, 0.05, 0.20])
        haircuts = compute_haircuts(
            vol, var_multiplier=3.0, haircut_min=0.05, haircut_max=0.5
        )
        assert haircuts[0] == pytest.approx(0.05)  # floored
        assert haircuts[2] == pytest.approx(0.5)  # capped
        assert haircuts[1] == pytest.approx(0.15)

    def test_haircuts_off_pin_to_minimum(self):
        vol = np.array([0.01, 0.05, 0.20])
        haircuts = compute_haircuts(
            vol,
            var_multiplier=3.0,
            haircut_min=0.05,
            haircut_max=0.5,
            procyclical=False,
        )
        assert np.allclose(haircuts, 0.05)


class TestLeveragedInvestor:
    def _investor(self, target_leverage: float = 3.0) -> LeveragedInvestor:
        inv = LeveragedInvestor.__new__(LeveragedInvestor)
        inv.basket = np.array([True, True, False])
        inv.target_leverage = target_leverage
        inv.rebalancing_speed = 0.25
        inv.holdings = np.array([100.0, 50.0, 0.0])
        inv.net_debt = 0.0
        inv.defaulted = False
        inv._config = None
        return inv

    def test_equity_and_leverage_identities(self):
        inv = self._investor()
        prices = np.array([10.0, 10.0, 10.0])
        inv.net_debt = 500.0
        assert inv.gross_assets(prices) == pytest.approx(1500.0)
        assert inv.equity(prices) == pytest.approx(1000.0)
        assert inv.leverage(prices) == pytest.approx(1.5)

    def test_leverage_is_infinite_when_insolvent(self):
        inv = self._investor()
        prices = np.array([10.0, 10.0, 10.0])
        inv.net_debt = 2000.0  # exceeds asset value of 1500
        assert inv.equity(prices) < 0
        assert inv.leverage(prices) == float("inf")

    def test_forced_orders_triggered_by_over_leverage(self):
        inv = self._investor(target_leverage=2.0)
        prices = np.array([10.0, 10.0, 10.0])
        haircuts = np.array([0.1, 0.1, 0.1])
        # gross assets = 1500, net_debt tuned so leverage >> target*1.15
        inv.net_debt = 1000.0  # equity=500, leverage=3.0 >> 2.0*1.15
        orders = inv.forced_orders(
            prices, haircuts, max_liquidation_rate=1.0, margin_call_multiple=1.15
        )
        assert np.all(orders <= 0.0)
        assert np.any(orders < 0.0)

    def test_forced_orders_zero_when_within_constraint(self):
        inv = self._investor(target_leverage=3.0)
        prices = np.array([10.0, 10.0, 10.0])
        haircuts = np.array([0.5, 0.5, 0.5])
        inv.net_debt = 500.0  # equity=1000, leverage=1.5 << 3.0
        orders = inv.forced_orders(
            prices, haircuts, max_liquidation_rate=1.0, margin_call_multiple=1.15
        )
        assert np.allclose(orders, 0.0)

    def test_apply_fill_updates_balance_sheet(self):
        inv = self._investor()
        filled = np.array([10.0, 0.0, 0.0])
        fill_prices = np.array([10.0, 10.0, 10.0])
        inv.apply_fill(filled, fill_prices)
        assert inv.holdings[0] == pytest.approx(110.0)
        assert inv.net_debt == pytest.approx(100.0)  # bought on margin


class TestDealer:
    def test_capacity_scales_with_capital(self):
        dealer = Dealer.__new__(Dealer)
        dealer.capital = 50.0
        dealer.target_capital = 100.0
        dealer.inventory = np.zeros(2)
        dealer.inventory_limit = np.array([400.0, 400.0])
        assert np.allclose(dealer.capacity(), [200.0, 200.0])

    def test_absorb_caps_at_capacity(self):
        dealer = Dealer.__new__(Dealer)
        dealer.capital = 100.0
        dealer.target_capital = 100.0
        dealer.inventory = np.zeros(2)
        dealer.inventory_limit = np.array([400.0, 400.0])
        absorbed = dealer.absorb(np.array([1000.0, -1000.0]))
        assert np.allclose(absorbed, [400.0, -400.0])


class TestFinancialSimulation:
    def test_run_produces_expected_length(self):
        sim = FinancialSimulation.from_config(_small_config())
        result = sim.run(60)
        assert len(result.records) == 60

    def test_prices_stay_positive(self):
        sim = FinancialSimulation.from_config(_small_config())
        result = sim.run(60)
        assert (result.price_paths > 0).all()

    def test_reproducible_with_same_seed(self):
        cfg = _small_config()
        sim_a = FinancialSimulation.from_config(cfg)
        sim_b = FinancialSimulation.from_config(cfg)
        result_a = sim_a.run(40)
        result_b = sim_b.run(40)
        assert np.allclose(result_a.price_paths, result_b.price_paths)

    def test_leverage_stays_near_target_in_calm_regime(self):
        cfg = _small_config(
            days=200, investors=InvestorConfig(count=40, target_leverage_mean=3.0)
        )
        sim = FinancialSimulation.from_config(cfg)
        result = sim.run(200)
        leverage = np.array(result.leverage_series)
        leverage = leverage[np.isfinite(leverage)]
        # Should hover around the 3.0 target, not diverge to zero or infinity.
        assert 1.0 < leverage[-50:].mean() < 6.0

    def test_procyclical_haircuts_off_reduces_amplification(self):
        """M2-off counterfactual (§7, Tier 3): without procyclical haircuts,
        a fundamental shock should produce a smaller price fall."""
        shock_day = 30

        def run_with_shock(procyclical: bool) -> float:
            cfg = _small_config(
                days=80,
                investors=InvestorConfig(count=60, target_leverage_mean=4.0),
                margin=MarginConfig(procyclical_haircuts=procyclical),
            )
            sim = FinancialSimulation.from_config(cfg)
            for day in range(80):
                if day == shock_day:
                    for asset in sim.assets:
                        asset.fundamental_value *= 0.6
                sim.step()
            return min(a.price for a in sim.assets)

        min_price_on = run_with_shock(procyclical=True)
        min_price_off = run_with_shock(procyclical=False)
        # With the amplifier on, the post-shock price should fall at least as
        # far as with it off (the counterfactual is the smaller/equal fall).
        assert min_price_on <= min_price_off + 1e-6


class TestFinancialMetrics:
    def test_autocorrelation_of_white_noise_near_zero(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=5000)
        acf = autocorrelation(x, max_lag=5)
        assert np.all(np.abs(acf) < 0.1)

    def test_hill_tail_exponent_of_gaussian_near_gaussian_regime(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=5000)
        tail_exp = hill_tail_exponent(x, tail_fraction=0.1)
        assert tail_exp > 2.0  # Gaussian tails are thin => high tail exponent

    def test_skew_and_kurtosis_of_gaussian_near_zero(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=20000)
        assert abs(skewness(x)) < 0.1
        assert abs(excess_kurtosis(x)) < 0.2

    def test_max_drawdown_is_negative_on_falling_series(self):
        prices = np.array([100.0, 110.0, 90.0, 95.0, 80.0])
        dd = max_drawdown(prices)
        assert dd == pytest.approx((80.0 - 110.0) / 110.0)

    def test_stylised_facts_report_shape(self):
        rng = np.random.default_rng(0)
        returns = rng.standard_t(df=3, size=2000) * 0.01
        report = stylised_facts_report(returns)
        assert report["n_obs"] == 2000
        assert "tail_exponent" in report
        assert "leverage_effect" in report
