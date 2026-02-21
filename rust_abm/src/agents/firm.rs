use std::fmt;

use krabmaga::engine::{agent::Agent, state::State};

use crate::state::EconomyState;

// ─────────────────────────────────────────────────────────────────────────────
// Data stored in EconomyState::firms
// ─────────────────────────────────────────────────────────────────────────────

/// All mutable state for a single firm.
///
/// This struct lives inside `EconomyState::firms` so that it can be accessed
/// by any agent (or market) that holds a reference to the state.
#[derive(Clone, Debug)]
pub struct FirmData {
    pub sector: String,
    pub employees: u32,
    pub wage_bill: f64,
    pub turnover: f64,
    pub capital: f64,
    pub cash: f64,
    pub debt: f64,
    pub equity: f64,

    // Derived / mutable state
    pub price: f64,
    pub output: f64,
    pub inventory: f64,
    pub profit: f64,
    pub markup: f64,
    pub vacancies: u32,
    pub wage_rate: f64,
    pub desired_production: f64,
    pub bankrupt: bool,
}

impl FirmData {
    pub fn new(
        sector: String,
        employees: u32,
        wage_rate: f64,
        turnover: f64,
        capital: f64,
        cash: f64,
        markup: f64,
    ) -> Self {
        let wage_bill = employees as f64 * wage_rate;
        FirmData {
            sector,
            employees,
            wage_bill,
            turnover,
            capital,
            cash,
            debt: 0.0,
            equity: capital + cash,
            price: 1.0,
            output: turnover, // initial output ≈ revenue at p=1
            inventory: 0.0,
            profit: 0.0,
            markup,
            vacancies: 0,
            wage_rate,
            desired_production: turnover,
            bankrupt: false,
        }
    }

    // ─── Step sub-methods ───────────────────────────────────────────────────

    pub fn plan_production(&mut self, inventory_target_ratio: f64) {
        let expected_sales = self.turnover / self.price.max(1e-9);
        let desired = expected_sales + inventory_target_ratio * expected_sales - self.inventory;
        self.desired_production = desired.max(0.0);
    }

    pub fn set_price(&mut self) {
        if self.output > 0.0 {
            let unit_cost = self.wage_bill / self.output.max(1e-9);
            self.price = unit_cost * (1.0 + self.markup);
        }
    }

    pub fn determine_labour_demand(&mut self) {
        let labour_productivity = if self.employees > 0 {
            self.output / self.employees as f64
        } else {
            1.0
        };
        let desired_employees =
            (self.desired_production / labour_productivity.max(1e-9)) as u32;
        self.vacancies = desired_employees.saturating_sub(self.employees);
    }

    pub fn produce(&mut self, capacity_utilization_target: f64) {
        let labour_productivity = if self.employees > 0 {
            self.output / (self.employees as f64).max(1.0)
        } else {
            1.0
        };
        let capacity = self.capital * capacity_utilization_target;
        let labour_output = self.employees as f64 * labour_productivity;
        self.output = self.desired_production.min(labour_output).min(capacity);
        self.inventory += self.output;
    }

    pub fn update_financials(&mut self, capacity_utilization_target: f64) {
        let sales_quantity =
            self.inventory.min(self.turnover / self.price.max(1e-9));
        let revenue = sales_quantity * self.price;
        self.inventory = (self.inventory - sales_quantity).max(0.0);
        self.turnover = revenue;
        self.wage_bill = self.employees as f64 * self.wage_rate;
        self.profit = revenue - self.wage_bill;
        self.cash += self.profit;
        self.equity += self.profit;

        // Bankruptcy check
        if self.equity < 0.0 && self.capital > 0.0 {
            let ratio = self.equity / self.capital;
            let threshold = -capacity_utilization_target;
            if ratio < threshold {
                self.bankrupt = true;
            }
        }
    }

    // ─── Market interfaces ──────────────────────────────────────────────────

    pub fn adapt_markup(&mut self, excess_demand: f64, speed: f64) {
        if excess_demand > 0.0 {
            self.markup += speed * excess_demand;
        } else {
            self.markup = (self.markup + speed * excess_demand).max(0.01);
        }
    }

    pub fn hire(&mut self, count: u32, wage: f64) {
        self.employees += count;
        self.wage_rate = wage;
        self.wage_bill = self.employees as f64 * self.wage_rate;
        self.vacancies = self.vacancies.saturating_sub(count);
    }

    pub fn fire(&mut self, count: u32) {
        self.employees = self.employees.saturating_sub(count);
        self.wage_bill = self.employees as f64 * self.wage_rate;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// krabmaga Agent proxy (stored in Schedule)
// ─────────────────────────────────────────────────────────────────────────────

/// Proxy agent for a single firm.
///
/// Only holds the firm's index into `EconomyState::firms`.
/// All mutable data lives in the state.
#[derive(Clone)]
pub struct FirmAgent {
    pub id: usize,
}

impl fmt::Display for FirmAgent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "FirmAgent({})", self.id)
    }
}

impl Agent for FirmAgent {
    /// Execute one period of firm behaviour, mirroring Python `Firm.step()`.
    fn step(&mut self, state: &mut dyn State) {
        let state = state
            .as_any_mut()
            .downcast_mut::<EconomyState>()
            .expect("state should be EconomyState");

        // Extract config values to avoid simultaneous borrows
        let inv_ratio = state.config.inventory_target_ratio;
        let cap_util = state.config.capacity_utilization_target;

        let firm = &mut state.firms[self.id];
        if firm.bankrupt {
            return;
        }

        firm.plan_production(inv_ratio);
        firm.set_price();
        firm.determine_labour_demand();
        firm.produce(cap_util);
        firm.update_financials(cap_util);
    }
}
