use std::fmt;

use krabmaga::engine::{agent::Agent, state::State};

use crate::state::EconomyState;

// ─────────────────────────────────────────────────────────────────────────────
// Bank data
// ─────────────────────────────────────────────────────────────────────────────

/// All mutable state for a single bank.
#[derive(Clone, Debug)]
pub struct BankData {
    pub capital: f64,
    pub reserves: f64,
    pub loans: f64,
    pub deposits: f64,
    pub non_performing_loans: f64,
    pub interest_rate: f64,
    pub profit: f64,
    // Internal per-period income calculations
    pub interest_income: f64,
    pub interest_expense: f64,
}

impl BankData {
    pub fn new(capital: f64, reserves: f64) -> Self {
        BankData {
            capital,
            reserves,
            loans: 0.0,
            deposits: 0.0,
            non_performing_loans: 0.0,
            interest_rate: 0.05,
            profit: 0.0,
            interest_income: 0.0,
            interest_expense: 0.0,
        }
    }

    // ─── Regulatory ratios ──────────────────────────────────────────────────

    pub fn capital_ratio(&self, risk_weight: f64) -> f64 {
        let risk_weighted = self.loans * risk_weight;
        if risk_weighted <= 0.0 {
            1.0
        } else {
            self.capital / risk_weighted
        }
    }

    pub fn meets_capital_requirement(
        &self,
        capital_requirement: f64,
        capital_buffer: f64,
        risk_weight: f64,
    ) -> bool {
        self.capital_ratio(risk_weight) >= capital_requirement + capital_buffer
    }

    // ─── Step sub-methods ───────────────────────────────────────────────────

    pub fn set_lending_rate(&mut self, policy_rate: f64, base_markup: f64, risk: f64) {
        let npl_ratio = if self.loans > 0.0 {
            self.non_performing_loans / self.loans
        } else {
            0.0
        };
        self.interest_rate = policy_rate + base_markup + risk * npl_ratio;
    }

    pub fn calculate_income(&mut self) {
        self.interest_income = self.interest_rate * self.loans;
        let deposit_rate = (self.interest_rate - 0.02).max(0.0);
        self.interest_expense = deposit_rate * self.deposits;
    }

    pub fn update_capital(&mut self) {
        let provisions = self.non_performing_loans * 0.5;
        self.profit = self.interest_income - self.interest_expense - provisions;
        self.capital += self.profit;
    }

    pub fn step(&mut self, policy_rate: f64, base_markup: f64, risk: f64) {
        self.set_lending_rate(policy_rate, base_markup, risk);
        self.calculate_income();
        self.update_capital();
    }

    // ─── Lending interface ──────────────────────────────────────────────────

    pub fn evaluate_loan(
        &self,
        amount: f64,
        borrower_equity: f64,
        borrower_revenue: f64,
        capital_requirement: f64,
        capital_buffer: f64,
        risk_weight: f64,
        lending_threshold: f64,
    ) -> bool {
        if !self.meets_capital_requirement(capital_requirement, capital_buffer, risk_weight) {
            return false;
        }
        let collateral_req = 0.5;
        if borrower_equity < amount * collateral_req {
            return false;
        }
        if borrower_revenue <= 0.0 {
            return false;
        }
        let debt_service = borrower_revenue / (amount * self.interest_rate).max(1e-9);
        debt_service >= lending_threshold
    }

    pub fn extend_loan(&mut self, amount: f64) -> f64 {
        self.loans += amount;
        self.deposits += amount; // loan creates deposit
        self.interest_rate
    }

    pub fn record_default(&mut self, amount: f64) {
        self.non_performing_loans += amount;
    }

    pub fn record_repayment(&mut self, amount: f64) {
        self.loans = (self.loans - amount).max(0.0);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Central bank data
// ─────────────────────────────────────────────────────────────────────────────

/// All mutable state for the central bank (singleton).
#[derive(Clone, Debug)]
pub struct CentralBankData {
    pub policy_rate: f64,
    pub inflation_target: f64,
    pub current_inflation: f64,
    pub output_gap: f64,
    pub previous_rate: f64,
}

impl CentralBankData {
    pub fn new(inflation_target: f64) -> Self {
        CentralBankData {
            policy_rate: inflation_target,
            inflation_target,
            current_inflation: inflation_target,
            output_gap: 0.0,
            previous_rate: inflation_target,
        }
    }

    /// Apply Taylor rule and update the policy rate.
    pub fn step(
        &mut self,
        pi_coef: f64,
        y_coef: f64,
        smoothing: f64,
        lower: f64,
    ) {
        let target_rate = self.inflation_target
            + pi_coef * (self.current_inflation - self.inflation_target)
            + y_coef * self.output_gap;

        let smoothed = smoothing * self.previous_rate + (1.0 - smoothing) * target_rate;
        self.previous_rate = self.policy_rate;
        self.policy_rate = smoothed.max(lower);
    }

    pub fn update_observations(&mut self, inflation: f64, output_gap: f64) {
        self.current_inflation = inflation;
        self.output_gap = output_gap;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Government data
// ─────────────────────────────────────────────────────────────────────────────

/// All mutable state for the government (singleton).
#[derive(Clone, Debug)]
pub struct GovernmentData {
    pub tax_revenue: f64,
    pub expenditure: f64,
    pub transfer_spending: f64,
    pub deficit: f64,
    pub debt: f64,
    pub gdp_estimate: f64,
}

impl GovernmentData {
    pub fn new() -> Self {
        GovernmentData {
            tax_revenue: 0.0,
            expenditure: 0.0,
            transfer_spending: 0.0,
            deficit: 0.0,
            debt: 0.0,
            gdp_estimate: 0.0,
        }
    }

    pub fn begin_period(&mut self) {
        self.tax_revenue = 0.0;
        self.expenditure = 0.0;
        self.transfer_spending = 0.0;
    }

    pub fn collect_corporate_tax(&mut self, profits: f64, rate: f64) -> f64 {
        let tax = (profits * rate).max(0.0);
        self.tax_revenue += tax;
        tax
    }

    pub fn collect_income_tax(&mut self, income: f64, rate: f64) -> f64 {
        let tax = (income * rate).max(0.0);
        self.tax_revenue += tax;
        tax
    }

    pub fn calculate_spending(&mut self, spending_gdp_ratio: f64) -> f64 {
        self.expenditure = spending_gdp_ratio * self.gdp_estimate.max(0.0);
        self.expenditure
    }

    pub fn pay_unemployment_benefit(
        &mut self,
        average_wage: f64,
        unemployed_count: usize,
        replacement: f64,
    ) -> f64 {
        let total = replacement * average_wage * unemployed_count as f64;
        self.transfer_spending += total;
        total
    }

    pub fn apply_fiscal_rule(&mut self, deficit_target: f64, speed: f64) {
        if self.gdp_estimate <= 0.0 {
            return;
        }
        let current_deficit_ratio =
            self.deficit.abs() / self.gdp_estimate.max(1e-9);
        let gap = current_deficit_ratio - deficit_target;
        let adjustment = speed * gap * self.gdp_estimate;
        self.expenditure = (self.expenditure - adjustment).max(0.0);
    }

    pub fn end_period(&mut self) {
        self.deficit = self.tax_revenue - (self.expenditure + self.transfer_spending);
        self.debt -= self.deficit; // negative deficit → debt increases
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// krabmaga Agent proxy for Bank
// ─────────────────────────────────────────────────────────────────────────────

/// Proxy agent for a single bank.
#[derive(Clone)]
pub struct BankAgent {
    pub id: usize,
}

impl fmt::Display for BankAgent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "BankAgent({})", self.id)
    }
}

impl Agent for BankAgent {
    /// Execute one period of bank behaviour.
    fn step(&mut self, state: &mut dyn State) {
        let state = state
            .as_any_mut()
            .downcast_mut::<EconomyState>()
            .expect("state should be EconomyState");

        let policy_rate = state.central_bank.policy_rate;
        let markup = state.config.base_interest_markup;
        let risk = state.config.risk_premium_sensitivity;

        let bank = &mut state.banks[self.id];
        bank.step(policy_rate, markup, risk);
    }
}
