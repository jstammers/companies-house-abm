use std::fmt;

use krabmaga::engine::{agent::Agent, state::State};

use crate::state::EconomyState;

// ─────────────────────────────────────────────────────────────────────────────
// Data stored in EconomyState::households
// ─────────────────────────────────────────────────────────────────────────────

/// All mutable state for a single household.
#[derive(Clone, Debug)]
pub struct HouseholdData {
    pub income: f64,
    pub wealth: f64,
    pub consumption: f64,
    pub savings: f64,
    pub mpc: f64,
    pub employed: bool,
    pub employer_id: Option<usize>,
    pub wage: f64,
    pub transfer_income: f64,
}

impl HouseholdData {
    pub fn new(income: f64, wealth: f64, mpc: f64) -> Self {
        HouseholdData {
            income,
            wealth,
            consumption: 0.0,
            savings: 0.0,
            mpc,
            employed: false,
            employer_id: None,
            wage: 0.0,
            transfer_income: 0.0,
        }
    }

    // ─── Step sub-methods ───────────────────────────────────────────────────

    fn receive_income(&mut self) {
        let wage_income = if self.employed { self.wage } else { 0.0 };
        self.income = wage_income + self.transfer_income;
    }

    fn consume(&mut self, smoothing: f64) {
        let c_income = self.mpc * self.income;
        let c_wealth = (1.0 - smoothing) * 0.04 * self.wealth;
        let desired = c_income + c_wealth;
        self.consumption = desired.max(0.0).min(self.income + self.wealth);
    }

    fn save(&mut self) {
        self.savings = self.income - self.consumption;
        self.wealth += self.savings;
    }

    pub fn step(&mut self, consumption_smoothing: f64) {
        self.receive_income();
        self.consume(consumption_smoothing);
        self.save();
        // Reset transfers after stepping (mirrors Python model)
        self.transfer_income = 0.0;
    }

    // ─── Employment interface ───────────────────────────────────────────────

    pub fn become_employed(&mut self, employer_id: usize, wage: f64) {
        self.employed = true;
        self.employer_id = Some(employer_id);
        self.wage = wage;
    }

    pub fn become_unemployed(&mut self) {
        self.employed = false;
        self.employer_id = None;
        self.wage = 0.0;
    }

    pub fn is_searching(&self, random_val: f64, job_search_intensity: f64) -> bool {
        if self.employed {
            return false;
        }
        random_val < job_search_intensity
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// krabmaga Agent proxy
// ─────────────────────────────────────────────────────────────────────────────

/// Proxy agent for a single household.
#[derive(Clone)]
pub struct HouseholdAgent {
    pub id: usize,
}

impl fmt::Display for HouseholdAgent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "HouseholdAgent({})", self.id)
    }
}

impl Agent for HouseholdAgent {
    /// Execute one period of household behaviour, mirroring Python `Household.step()`.
    fn step(&mut self, state: &mut dyn State) {
        let state = state
            .as_any_mut()
            .downcast_mut::<EconomyState>()
            .expect("state should be EconomyState");

        let smoothing = state.config.consumption_smoothing;
        let hh = &mut state.households[self.id];
        hh.step(smoothing);
    }
}
