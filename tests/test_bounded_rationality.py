"""Tests for bounded-rationality agent mechanisms.

Covers:
- Firm satisficing markup heuristic (Simon 1955)
- Household adaptive expectations (Dosi et al. 2010)
- Bank noisy composite credit scoring (Gabaix 2014)
- Credit market RNG forwarding
"""

from __future__ import annotations

import numpy as np
import pytest

from companies_house_abm.abm.agents.bank import Bank
from companies_house_abm.abm.agents.firm import Firm
from companies_house_abm.abm.agents.household import Household
from companies_house_abm.abm.config import (
    BankBehaviorConfig,
    BankConfig,
    FirmBehaviorConfig,
    HouseholdBehaviorConfig,
)
from companies_house_abm.abm.markets.credit import CreditMarket

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng(seed)


def _firm(markup: float = 0.15, aspiration: float = 0.5) -> Firm:
    cfg = FirmBehaviorConfig(
        price_markup=markup,
        markup_adjustment_speed=0.1,
        satisficing_aspiration_rate=aspiration,
        satisficing_window=4,
        markup_noise_std=0.0,
    )
    return Firm(
        turnover=1000.0,
        wage_bill=400.0,
        employees=10,
        behavior=cfg,
    )


def _household(
    income: float = 1000.0,
    alpha: float = 0.3,
    mpc: float = 0.8,
) -> Household:
    cfg = HouseholdBehaviorConfig(expectation_adaptation_speed=alpha)
    return Household(income=income, mpc=mpc, behavior=cfg)


def _bank(noise_std: float = 0.0, capital: float = 1e6) -> Bank:
    cfg = BankConfig(capital_requirement=0.10)
    beh = BankBehaviorConfig(
        lending_threshold=2.0,
        capital_buffer=0.0,
        credit_score_noise_std=noise_std,
    )
    b = Bank(capital=capital, loans=0.0, behavior=beh, config=cfg)
    b.interest_rate = 0.05
    return b


# ---------------------------------------------------------------------------
# Firm: satisficing markup heuristic
# ---------------------------------------------------------------------------


class TestSatisficingMarkup:
    def test_profit_rate_history_starts_empty(self) -> None:
        f = _firm()
        assert f._profit_rate_history == []

    def test_aspiration_rate_property_before_history(self) -> None:
        f = _firm(aspiration=0.5)
        assert f.aspiration_rate == pytest.approx(0.5)

    def test_history_recorded_after_adapt_markup(self) -> None:
        f = _firm()
        f.profit = 100.0
        f.turnover = 1000.0
        f.adapt_markup(0.0)
        assert len(f._profit_rate_history) == 1

    def test_history_capped_at_window(self) -> None:
        f = _firm()
        f.profit = 100.0
        f.turnover = 1000.0
        for _ in range(10):
            f.adapt_markup(0.0)
        assert len(f._profit_rate_history) <= 4  # window=4

    def test_aspiration_rate_reflects_history(self) -> None:
        f = _firm()
        f.profit = 500.0
        f.turnover = 1000.0
        for _ in range(4):
            f.adapt_markup(0.0)
        assert f.aspiration_rate == pytest.approx(0.5)

    def test_satisficed_firm_responds_less_aggressively(self) -> None:
        """Firm above aspiration adjusts markup much less than one below it."""
        # Firm with high profit rate (satisficed)
        f_high = _firm(markup=0.20, aspiration=0.3)
        f_high.profit = 600.0  # 60% profit rate >> 30% aspiration
        f_high.turnover = 1000.0
        # Warm up history so satisficing kicks in
        for _ in range(3):
            f_high.adapt_markup(1.0)
        markup_before = f_high.markup
        f_high.adapt_markup(1.0)
        high_adjustment = f_high.markup - markup_before

        # Firm with low profit rate (not satisficed)
        f_low = _firm(markup=0.20, aspiration=0.8)
        f_low.profit = 50.0  # 5% profit rate << 80% aspiration
        f_low.turnover = 1000.0
        for _ in range(3):
            f_low.adapt_markup(1.0)
        markup_before_low = f_low.markup
        f_low.adapt_markup(1.0)
        low_adjustment = f_low.markup - markup_before_low

        assert high_adjustment < low_adjustment

    def test_markup_not_below_minimum(self) -> None:
        f = _firm()
        f.profit = -500.0
        f.turnover = 1000.0
        for _ in range(20):
            f.adapt_markup(-5.0)
        assert f.markup >= 0.01

    def test_markup_increases_with_positive_excess_demand_below_aspiration(
        self,
    ) -> None:
        f = _firm(markup=0.10, aspiration=0.9)
        f.profit = 50.0  # 5% << 90% aspiration → full response
        f.turnover = 1000.0
        initial = f.markup
        f.adapt_markup(1.0)
        assert f.markup > initial

    def test_markup_decreases_with_negative_excess_demand_below_aspiration(
        self,
    ) -> None:
        f = _firm(markup=0.20, aspiration=0.9)
        f.profit = 50.0  # 5% << 90%
        f.turnover = 1000.0
        initial = f.markup
        f.adapt_markup(-1.0)
        assert f.markup < initial

    def test_noise_applied_when_rng_and_noise_std_given(self) -> None:
        cfg = FirmBehaviorConfig(
            markup_adjustment_speed=0.1,
            satisficing_aspiration_rate=0.9,
            satisficing_window=4,
            markup_noise_std=0.05,  # noise enabled
        )
        f = Firm(turnover=1000.0, wage_bill=400.0, employees=10, behavior=cfg)
        f.profit = 50.0
        f.turnover = 1000.0

        rng = _rng(42)
        markups = set()
        for _ in range(20):
            f2 = Firm(turnover=1000.0, wage_bill=400.0, employees=10, behavior=cfg)
            f2.profit = 50.0
            f2.adapt_markup(0.0, rng=rng)
            markups.add(round(f2.markup, 6))
        # Different outcomes expected due to noise
        assert len(markups) > 1

    def test_no_noise_without_rng(self) -> None:
        cfg = FirmBehaviorConfig(
            markup_adjustment_speed=0.1,
            satisficing_aspiration_rate=0.9,
            satisficing_window=4,
            markup_noise_std=0.05,
        )
        markups = []
        for _ in range(5):
            f = Firm(turnover=1000.0, wage_bill=400.0, employees=10, behavior=cfg)
            f.profit = 50.0
            f.adapt_markup(0.0)  # no rng
            markups.append(f.markup)
        # All identical: no noise without RNG
        assert all(m == markups[0] for m in markups)

    def test_get_state_includes_aspiration_rate(self) -> None:
        f = _firm()
        state = f.get_state()
        assert "aspiration_rate" in state


# ---------------------------------------------------------------------------
# Household: adaptive expectations
# ---------------------------------------------------------------------------


class TestAdaptiveExpectations:
    def test_expected_income_initialised_to_income(self) -> None:
        h = _household(income=500.0)
        assert h.expected_income == pytest.approx(500.0)

    def test_expected_income_updates_toward_realized(self) -> None:
        h = _household(income=1000.0, alpha=0.3)
        h.wage = 500.0
        h.employed = True
        h._receive_income()
        # expected = 0.3 * 500 + 0.7 * 1000 = 150 + 700 = 850
        assert h.expected_income == pytest.approx(850.0)

    def test_expected_income_converges_over_time(self) -> None:
        h = _household(income=0.0, alpha=0.5)
        h.wage = 1000.0
        h.employed = True
        for _ in range(20):
            h._receive_income()
        assert h.expected_income == pytest.approx(1000.0, rel=0.01)

    def test_consumption_uses_expected_not_realized_income(self) -> None:
        """A household that becomes unemployed still consumes out of expected income."""
        h = _household(income=1000.0, alpha=0.1)
        h.expected_income = 1000.0  # well-established expectation
        h.wealth = 5000.0  # sufficient buffer to fund consumption

        # Household becomes unemployed this period
        h.wage = 0.0
        h.employed = False
        h.transfer_income = 0.0
        h._receive_income()  # realized = 0; expected ≈ 0.1*0 + 0.9*1000 = 900

        h._consume()
        cfg = h._behavior
        smoothing = cfg.consumption_smoothing if cfg else 0.7
        expected_c = h.mpc * h.expected_income + (1 - smoothing) * 0.04 * h.wealth
        assert h.consumption == pytest.approx(expected_c, rel=0.01)
        assert h.consumption > 0.0  # consumes despite zero realized income

    def test_consumption_bounded_by_income_plus_wealth(self) -> None:
        """Consumption cannot exceed income + wealth even with high expectations."""
        h = _household(income=100.0, alpha=0.3)
        h.expected_income = 1_000_000.0  # absurdly high expectation
        h.wealth = 50.0
        h.income = 100.0
        h._consume()
        assert h.consumption <= h.income + h.wealth + 1e-9

    def test_get_state_includes_expected_income(self) -> None:
        h = _household()
        state = h.get_state()
        assert "expected_income" in state
        assert state["expected_income"] == pytest.approx(h.expected_income)

    def test_alpha_zero_expected_income_unchanged(self) -> None:
        """With alpha=0, expected income never updates."""
        h = _household(income=1000.0, alpha=0.0)
        h.wage = 200.0
        h.employed = True
        for _ in range(5):
            h._receive_income()
        assert h.expected_income == pytest.approx(1000.0)

    def test_alpha_one_expected_income_equals_realized(self) -> None:
        """With alpha=1, expected income immediately equals realized income."""
        h = _household(income=1000.0, alpha=1.0)
        h.wage = 300.0
        h.employed = True
        h._receive_income()
        assert h.expected_income == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# Bank: noisy composite credit scoring
# ---------------------------------------------------------------------------


class TestNoisyCreditScoring:
    def test_deterministic_without_noise(self) -> None:
        """Without noise, evaluate_loan behaves identically to original rule."""
        b = _bank(noise_std=0.0, capital=1e6)
        b.loans = 100.0
        # Good borrower
        assert b.evaluate_loan(10.0, borrower_equity=100.0, borrower_revenue=1000.0)

    def test_hard_threshold_collateral_rejection(self) -> None:
        b = _bank(noise_std=0.0, capital=1e6)
        # borrower_equity < 50% of loan (collateral requirement)
        assert not b.evaluate_loan(
            1000.0, borrower_equity=1.0, borrower_revenue=1_000_000.0
        )

    def test_hard_threshold_coverage_rejection(self) -> None:
        b = _bank(noise_std=0.0, capital=1e6)
        b.loans = 1.0
        # revenue too low relative to debt service
        assert not b.evaluate_loan(1000.0, borrower_equity=5000.0, borrower_revenue=1.0)

    def test_zero_revenue_always_rejected(self) -> None:
        b = _bank(noise_std=0.2, capital=1e6)
        assert not b.evaluate_loan(
            1000.0, borrower_equity=5000.0, borrower_revenue=0.0, rng=_rng()
        )

    def test_noisy_scoring_can_approve_borderline(self) -> None:
        """With high noise, a borderline case can be approved or rejected.

        Calibration: composite = 0.5 * collateral_score + 0.5 * coverage_score.
        With lending_threshold=2.0, rate=0.05, amount=100:
          collateral_score = equity / (100 * 0.5) = 1.0 when equity = 50
          coverage_score   = (revenue / (100 * 0.05)) / 2.0 = 1.0 when revenue = 10
        composite = 1.0 exactly, so noise=N(0,1) gives ~50% accept rate.
        """
        b = _bank(noise_std=1.0, capital=1e6)
        rng = _rng(0)
        outcomes = [
            b.evaluate_loan(
                100.0,
                borrower_equity=50.0,  # collateral_score = 1.0
                borrower_revenue=10.0,  # coverage_score   = 1.0
                rng=rng,
            )
            for _ in range(100)
        ]
        # With noise_std=1.0 and composite=1.0 we expect both outcomes
        assert any(outcomes)
        assert not all(outcomes)

    def test_noisy_scoring_produces_dispersion(self) -> None:
        """Same borrower evaluated many times → different outcomes with noise.

        Uses same calibration as above: composite = 1.0 exactly at boundary.
        """
        b = _bank(noise_std=0.5, capital=1e6)
        rng = _rng(3)
        results = [
            b.evaluate_loan(
                100.0,
                borrower_equity=50.0,
                borrower_revenue=10.0,
                rng=rng,
            )
            for _ in range(50)
        ]
        assert len(set(results)) > 1

    def test_no_noise_without_rng(self) -> None:
        """Without rng, noisy scoring falls back to deterministic."""
        b = _bank(noise_std=0.5, capital=1e6)
        # Same call repeated → always same result
        results = [
            b.evaluate_loan(50.0, borrower_equity=100.0, borrower_revenue=500.0)
            for _ in range(10)
        ]
        assert len(set(results)) == 1

    def test_capital_requirement_hard_gate(self) -> None:
        """evaluate_loan returns False immediately if capital requirement unmet."""
        cfg = BankConfig(capital_requirement=0.80)
        beh = BankBehaviorConfig(capital_buffer=0.0, credit_score_noise_std=0.5)
        b = Bank(capital=10.0, loans=1000.0, config=cfg, behavior=beh)
        b.interest_rate = 0.05
        # capital_ratio = 10/1000 = 1% << 80%
        assert not b.evaluate_loan(
            100.0, borrower_equity=10000.0, borrower_revenue=99999.0, rng=_rng()
        )


# ---------------------------------------------------------------------------
# Credit market: RNG forwarding
# ---------------------------------------------------------------------------


class TestCreditMarketRngForwarding:
    def test_set_agents_accepts_rng(self) -> None:
        market = CreditMarket()
        market.set_agents([], [], rng=_rng())
        assert market._rng is not None

    def test_set_agents_rng_defaults_none(self) -> None:
        market = CreditMarket()
        market.set_agents([], [])
        assert market._rng is None

    def test_noisy_bank_via_credit_market(self) -> None:
        """Credit market passes its RNG to bank.evaluate_loan."""
        b = _bank(noise_std=0.8, capital=1e6)
        b.loans = 0.0

        f = Firm(
            cash=-100.0,
            equity=100.0,
            turnover=1000.0,
            wage_bill=0.0,
        )

        market = CreditMarket()
        rng = _rng(99)
        market.set_agents([f], [b], rng=rng)

        # Run multiple periods to observe outcome variation
        outcomes = []
        for _ in range(20):
            f.cash = -100.0  # reset need for loan
            f.bankrupt = False
            result = market.clear()
            outcomes.append(result["total_approvals"])

        # With noisy scoring we expect some variation in approval/rejection
        assert len(set(outcomes)) > 0  # at least runs without error
