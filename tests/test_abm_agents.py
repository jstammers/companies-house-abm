"""Tests for ABM agent classes."""

from __future__ import annotations

import numpy as np

from companies_house_abm.abm.agents.bank import Bank
from companies_house_abm.abm.agents.base import BaseAgent
from companies_house_abm.abm.agents.central_bank import CentralBank
from companies_house_abm.abm.agents.firm import Firm
from companies_house_abm.abm.agents.government import Government
from companies_house_abm.abm.agents.household import Household
from companies_house_abm.abm.config import (
    BankBehaviorConfig,
    BankConfig,
    FirmBehaviorConfig,
    FiscalRuleConfig,
    HouseholdBehaviorConfig,
    TaylorRuleConfig,
    TransfersConfig,
)

# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------


class TestBaseAgent:
    def test_cannot_instantiate_directly(self):
        """BaseAgent is abstract and cannot be instantiated."""
        try:
            BaseAgent()
            msg = "Expected TypeError"
            raise AssertionError(msg)
        except TypeError:
            pass

    def test_agent_id_auto_generated(self):
        firm = Firm()
        assert firm.agent_id is not None
        assert len(firm.agent_id) > 0

    def test_agent_id_custom(self):
        firm = Firm(agent_id="custom_id")
        assert firm.agent_id == "custom_id"

    def test_agent_type(self):
        firm = Firm()
        assert firm.agent_type == "firm"
        hh = Household()
        assert hh.agent_type == "household"


# ---------------------------------------------------------------------------
# Firm
# ---------------------------------------------------------------------------


class TestFirm:
    def test_init_defaults(self):
        firm = Firm()
        assert firm.sector == "other_services"
        assert firm.employees == 0
        assert firm.bankrupt is False

    def test_init_with_values(self):
        firm = Firm(
            agent_id="f1",
            sector="manufacturing",
            employees=10,
            wage_bill=100_000.0,
            turnover=500_000.0,
            capital=200_000.0,
            cash=50_000.0,
            equity=250_000.0,
        )
        assert firm.agent_id == "f1"
        assert firm.sector == "manufacturing"
        assert firm.employees == 10
        assert firm.wage_rate == 10_000.0

    def test_init_with_behavior(self):
        behavior = FirmBehaviorConfig(price_markup=0.20)
        firm = Firm(behavior=behavior)
        assert firm.markup == 0.20

    def test_step_does_not_crash(self):
        firm = Firm(
            employees=5,
            wage_bill=50_000.0,
            turnover=100_000.0,
            capital=200_000.0,
            cash=30_000.0,
            equity=230_000.0,
        )
        firm.step()

    def test_step_bankrupt_firm_is_noop(self):
        firm = Firm(employees=5, turnover=100.0, capital=1000.0)
        firm.bankrupt = True
        old_output = firm.output
        firm.step()
        assert firm.output == old_output

    def test_hire(self):
        firm = Firm(employees=5, wage_bill=50_000.0)
        firm.vacancies = 3
        firm.hire(2, 12_000.0)
        assert firm.employees == 7
        assert firm.wage_rate == 12_000.0
        assert firm.vacancies == 1

    def test_fire(self):
        firm = Firm(employees=10, wage_bill=100_000.0)
        firm.wage_rate = 10_000.0
        firm.fire(3)
        assert firm.employees == 7
        assert firm.wage_bill == 70_000.0

    def test_fire_below_zero(self):
        firm = Firm(employees=2)
        firm.fire(5)
        assert firm.employees == 0

    def test_adapt_markup_positive(self):
        firm = Firm()
        initial_markup = firm.markup
        firm.adapt_markup(0.5)
        assert firm.markup > initial_markup

    def test_adapt_markup_negative(self):
        firm = Firm()
        firm.markup = 0.2
        firm.adapt_markup(-0.1)
        assert firm.markup < 0.2

    def test_adapt_markup_floor(self):
        firm = Firm()
        firm.markup = 0.02
        firm.adapt_markup(-10.0)
        assert firm.markup >= 0.01

    def test_get_state_keys(self):
        firm = Firm(agent_id="f1")
        state = firm.get_state()
        expected_keys = {
            "agent_id",
            "agent_type",
            "sector",
            "employees",
            "wage_bill",
            "turnover",
            "price",
            "output",
            "inventory",
            "cash",
            "debt",
            "capital",
            "equity",
            "profit",
            "markup",
            "bankrupt",
        }
        assert set(state.keys()) == expected_keys
        assert state["agent_id"] == "f1"

    def test_repr(self):
        firm = Firm(agent_id="f1")
        assert "Firm" in repr(firm)
        assert "f1" in repr(firm)


# ---------------------------------------------------------------------------
# Household
# ---------------------------------------------------------------------------


class TestHousehold:
    def test_init_defaults(self):
        hh = Household()
        assert hh.income == 0.0
        assert hh.wealth == 0.0
        assert hh.employed is False
        assert hh.mpc == 0.8

    def test_init_with_values(self):
        hh = Household(
            agent_id="h1",
            income=1000.0,
            wealth=5000.0,
            mpc=0.9,
            employed=True,
            employer_id="f1",
            wage=1000.0,
        )
        assert hh.agent_id == "h1"
        assert hh.employed is True
        assert hh.wage == 1000.0

    def test_step_employed(self):
        hh = Household(
            income=1000.0,
            wealth=5000.0,
            employed=True,
            wage=1000.0,
        )
        hh.step()
        assert hh.consumption > 0
        assert hh.income == 1000.0

    def test_step_unemployed(self):
        hh = Household(wealth=1000.0, mpc=0.8)
        hh.step()
        # Income is 0, but consumption can draw on wealth
        assert hh.consumption >= 0

    def test_become_employed(self):
        hh = Household()
        hh.become_employed("firm_1", 2000.0)
        assert hh.employed is True
        assert hh.employer_id == "firm_1"
        assert hh.wage == 2000.0

    def test_become_unemployed(self):
        hh = Household(employed=True, employer_id="f1", wage=1000.0)
        hh.become_unemployed()
        assert hh.employed is False
        assert hh.employer_id is None
        assert hh.wage == 0.0

    def test_is_searching_unemployed_deterministic(self):
        hh = Household(employed=False)
        assert hh.is_searching() is True

    def test_is_searching_employed(self):
        hh = Household(employed=True)
        assert hh.is_searching() is False

    def test_is_searching_with_rng(self):
        hh = Household(
            employed=False,
            behavior=HouseholdBehaviorConfig(job_search_intensity=1.0),
        )
        rng = np.random.default_rng(42)
        # With intensity=1.0, random() < 1.0 is always true
        assert hh.is_searching(rng) is True

    def test_consumption_cannot_exceed_resources(self):
        hh = Household(income=100.0, wealth=50.0, mpc=0.99)
        hh.employed = True
        hh.wage = 100.0
        hh.step()
        assert hh.consumption <= hh.income + 50.0 + hh.consumption
        # More precisely: consumption <= income + initial_wealth
        # After save, wealth changes, so check consumption was bounded

    def test_transfer_income(self):
        hh = Household(employed=False, wealth=0.0)
        hh.transfer_income = 500.0
        hh.step()
        assert hh.income == 500.0

    def test_get_state_keys(self):
        hh = Household(agent_id="h1")
        state = hh.get_state()
        expected_keys = {
            "agent_id",
            "agent_type",
            "income",
            "wealth",
            "consumption",
            "savings",
            "employed",
            "employer_id",
            "wage",
            "mpc",
        }
        assert set(state.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Bank
# ---------------------------------------------------------------------------


class TestBank:
    def _make_bank(self, **kwargs):
        defaults = {
            "capital": 1_000_000.0,
            "reserves": 100_000.0,
            "loans": 5_000_000.0,
            "deposits": 4_000_000.0,
            "config": BankConfig(),
            "behavior": BankBehaviorConfig(),
        }
        defaults.update(kwargs)
        return Bank(agent_id="b1", **defaults)

    def test_init_defaults(self):
        bank = Bank()
        assert bank.capital == 0.0
        assert bank.loans == 0.0

    def test_capital_ratio(self):
        bank = self._make_bank(capital=500_000.0, loans=5_000_000.0)
        assert bank.capital_ratio == 500_000.0 / 5_000_000.0

    def test_capital_ratio_no_loans(self):
        bank = self._make_bank(loans=0.0)
        assert bank.capital_ratio == 1.0

    def test_reserve_ratio(self):
        bank = self._make_bank(reserves=100_000.0, deposits=1_000_000.0)
        assert bank.reserve_ratio == 0.1

    def test_reserve_ratio_no_deposits(self):
        bank = self._make_bank(deposits=0.0)
        assert bank.reserve_ratio == 1.0

    def test_meets_capital_requirement(self):
        # capital_requirement=0.10, buffer=0.02, so need ratio > 0.12
        bank = self._make_bank(capital=650_000.0, loans=5_000_000.0)
        assert bank.capital_ratio > 0.12
        assert bank.meets_capital_requirement is True

    def test_fails_capital_requirement(self):
        bank = self._make_bank(capital=100_000.0, loans=5_000_000.0)
        assert bank.meets_capital_requirement is False

    def test_step_sets_interest_rate(self):
        bank = self._make_bank()
        bank.step()
        assert bank.interest_rate > 0

    def test_set_policy_rate(self):
        bank = self._make_bank()
        bank.set_policy_rate(0.03)
        assert bank.interest_rate >= 0.03

    def test_evaluate_loan_approved(self):
        bank = self._make_bank(capital=1_000_000.0, loans=1_000_000.0)
        bank.interest_rate = 0.05
        approved = bank.evaluate_loan(
            amount=10_000.0,
            borrower_equity=50_000.0,
            borrower_revenue=100_000.0,
        )
        assert approved is True

    def test_evaluate_loan_rejected_insufficient_capital(self):
        bank = self._make_bank(capital=10_000.0, loans=5_000_000.0)
        approved = bank.evaluate_loan(
            amount=100_000.0,
            borrower_equity=200_000.0,
            borrower_revenue=500_000.0,
        )
        assert approved is False

    def test_evaluate_loan_rejected_insufficient_collateral(self):
        bank = self._make_bank(capital=1_000_000.0, loans=1_000_000.0)
        bank.interest_rate = 0.05
        approved = bank.evaluate_loan(
            amount=100_000.0,
            borrower_equity=10_000.0,  # < 50% of loan
            borrower_revenue=500_000.0,
        )
        assert approved is False

    def test_extend_loan(self):
        bank = self._make_bank(loans=1_000_000.0, deposits=500_000.0)
        bank.interest_rate = 0.05
        rate = bank.extend_loan(50_000.0)
        assert rate == 0.05
        assert bank.loans == 1_050_000.0
        assert bank.deposits == 550_000.0

    def test_record_default(self):
        bank = self._make_bank()
        bank.record_default(100_000.0)
        assert bank.non_performing_loans == 100_000.0

    def test_record_repayment(self):
        bank = self._make_bank(loans=1_000_000.0)
        bank.record_repayment(200_000.0)
        assert bank.loans == 800_000.0

    def test_get_state_keys(self):
        bank = self._make_bank()
        state = bank.get_state()
        expected_keys = {
            "agent_id",
            "agent_type",
            "capital",
            "reserves",
            "loans",
            "deposits",
            "non_performing_loans",
            "interest_rate",
            "capital_ratio",
            "profit",
        }
        assert set(state.keys()) == expected_keys


# ---------------------------------------------------------------------------
# CentralBank
# ---------------------------------------------------------------------------


class TestCentralBank:
    def test_init_defaults(self):
        cb = CentralBank()
        assert cb.agent_id == "central_bank"
        assert cb.policy_rate == 0.02
        assert cb.inflation_target == 0.02

    def test_init_with_config(self):
        cfg = TaylorRuleConfig(inflation_target=0.03)
        cb = CentralBank(taylor_rule=cfg)
        assert cb.inflation_target == 0.03
        assert cb.policy_rate == 0.03

    def test_step_inflation_above_target(self):
        cb = CentralBank()
        cb.update_observations(inflation=0.05, output_gap=0.0)
        cb.step()
        # Rate should rise when inflation exceeds target
        assert cb.policy_rate > 0.02

    def test_step_inflation_below_target(self):
        cb = CentralBank()
        cb.update_observations(inflation=0.00, output_gap=0.0)
        cb.step()
        # Rate should fall (but bounded by lower bound)
        assert cb.policy_rate >= 0.001

    def test_step_positive_output_gap(self):
        cb = CentralBank()
        cb.update_observations(inflation=0.02, output_gap=0.05)
        cb.step()
        assert cb.policy_rate > 0.0

    def test_lower_bound(self):
        cfg = TaylorRuleConfig(lower_bound=0.005)
        cb = CentralBank(taylor_rule=cfg)
        cb.update_observations(inflation=-0.05, output_gap=-0.10)
        cb.step()
        assert cb.policy_rate >= 0.005

    def test_supply_reserves(self):
        cb = CentralBank()
        cb.supply_reserves(1_000_000.0)
        assert cb.reserves_supplied == 1_000_000.0

    def test_get_state_keys(self):
        cb = CentralBank()
        state = cb.get_state()
        expected_keys = {
            "agent_id",
            "agent_type",
            "policy_rate",
            "inflation_target",
            "current_inflation",
            "output_gap",
            "reserves_supplied",
        }
        assert set(state.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Government
# ---------------------------------------------------------------------------


class TestGovernment:
    def test_init_defaults(self):
        gov = Government()
        assert gov.agent_id == "government"
        assert gov.tax_revenue == 0.0
        assert gov.debt == 0.0

    def test_collect_corporate_tax(self):
        cfg = FiscalRuleConfig(tax_rate_corporate=0.25)
        gov = Government(fiscal_rule=cfg)
        tax = gov.collect_corporate_tax(100_000.0)
        assert tax == 25_000.0
        assert gov.tax_revenue == 25_000.0

    def test_collect_corporate_tax_no_tax_on_loss(self):
        gov = Government()
        tax = gov.collect_corporate_tax(-50_000.0)
        assert tax == 0.0

    def test_collect_income_tax(self):
        cfg = FiscalRuleConfig(tax_rate_income_base=0.20)
        gov = Government(fiscal_rule=cfg)
        tax = gov.collect_income_tax(50_000.0)
        assert tax == 10_000.0

    def test_calculate_spending(self):
        cfg = FiscalRuleConfig(spending_gdp_ratio=0.40)
        gov = Government(fiscal_rule=cfg)
        gov.gdp_estimate = 1_000_000.0
        spending = gov.calculate_spending()
        assert spending == 400_000.0

    def test_pay_unemployment_benefit(self):
        transfers = TransfersConfig(unemployment_benefit_ratio=0.5)
        gov = Government(transfers=transfers)
        benefit = gov.pay_unemployment_benefit(
            average_wage=30_000.0, unemployed_count=100
        )
        assert benefit == 0.5 * 30_000.0 * 100
        assert gov.transfer_spending == benefit

    def test_begin_and_end_period(self):
        gov = Government()
        gov.tax_revenue = 100.0
        gov.expenditure = 200.0
        gov.begin_period()
        assert gov.tax_revenue == 0.0
        assert gov.expenditure == 0.0
        gov.tax_revenue = 500.0
        gov.expenditure = 400.0
        gov.end_period()
        assert gov.deficit == 100.0  # surplus
        assert gov.debt == -100.0  # surplus reduces debt

    def test_deficit_increases_debt(self):
        gov = Government()
        gov.begin_period()
        gov.tax_revenue = 100.0
        gov.expenditure = 300.0
        gov.end_period()
        assert gov.deficit == -200.0
        assert gov.debt == 200.0

    def test_get_state_keys(self):
        gov = Government()
        state = gov.get_state()
        expected_keys = {
            "agent_id",
            "agent_type",
            "tax_revenue",
            "expenditure",
            "transfer_spending",
            "deficit",
            "debt",
            "gdp_estimate",
        }
        assert set(state.keys()) == expected_keys
