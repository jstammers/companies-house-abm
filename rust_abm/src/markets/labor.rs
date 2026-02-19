use rand::Rng;
use std::fmt;

use krabmaga::engine::{agent::Agent, state::State};

use crate::state::EconomyState;

/// Outcome of labour market clearing for one period.
#[derive(Clone, Debug, Default)]
pub struct LaborOutcome {
    pub total_employed: usize,
    pub total_unemployed: usize,
    pub unemployment_rate: f64,
    pub average_wage: f64,
    pub total_matches: usize,
    pub total_separations: usize,
}

/// Clear the labour market in-place on the simulation state.
///
/// Mirrors Python `LaborMarket.clear()`:
/// 1. Exogenous separations.
/// 2. Match unemployed job-seekers to firms with vacancies.
/// 3. Update household transfer income for unemployed.
/// 4. Compute aggregate statistics.
pub fn clear_labor_market(state: &mut EconomyState) {
    let sep_rate = state.config.separation_rate;
    let matching_eff = state.config.matching_efficiency;
    let wage_stickiness = state.config.wage_stickiness;
    let job_search_intensity = state.config.job_search_intensity;
    let unemployment_benefit_ratio = state.config.unemployment_benefit_ratio;

    // ── 1. Exogenous separations ─────────────────────────────────────────────
    let mut total_separations = 0usize;
    {
        let n_hh = state.households.len();
        for hh_idx in 0..n_hh {
            if !state.households[hh_idx].employed {
                continue;
            }
            let r: f64 = state.rng.gen();
            if r < sep_rate {
                // Separate: find employer firm and fire
                if let Some(employer_id) = state.households[hh_idx].employer_id {
                    state.firms[employer_id].fire(1);
                }
                state.households[hh_idx].become_unemployed();
                total_separations += 1;
            }
        }
    }

    // ── 2. Current average wage (before matching) ────────────────────────────
    let current_avg_wage = {
        let wages: Vec<f64> = state
            .households
            .iter()
            .filter(|h| h.employed && h.wage > 0.0)
            .map(|h| h.wage)
            .collect();
        if wages.is_empty() {
            0.0
        } else {
            wages.iter().sum::<f64>() / wages.len() as f64
        }
    };

    // ── 3. Matching ──────────────────────────────────────────────────────────
    // Collect firm indices with vacancies
    let hiring_firm_indices: Vec<usize> = (0..state.firms.len())
        .filter(|&i| state.firms[i].vacancies > 0 && !state.firms[i].bankrupt)
        .collect();

    // Collect seeking household indices
    let seeking_hh_indices: Vec<usize> = (0..state.households.len())
        .filter(|&i| {
            let r: f64 = state.rng.gen();
            state.households[i].is_searching(r, job_search_intensity)
        })
        .collect();

    let mut total_matches = 0usize;

    if !hiring_firm_indices.is_empty() && !seeking_hh_indices.is_empty() {
        let mut seeker_idx = 0usize;

        for &firm_idx in &hiring_firm_indices {
            while state.firms[firm_idx].vacancies > 0 && seeker_idx < seeking_hh_indices.len() {
                // Matching probability
                let r: f64 = state.rng.gen();
                if r > matching_eff {
                    seeker_idx += 1;
                    continue;
                }

                let hh_idx = seeking_hh_indices[seeker_idx];
                let offered_wage = state.firms[firm_idx].wage_rate;
                let wage = if current_avg_wage > 0.0 {
                    wage_stickiness * current_avg_wage + (1.0 - wage_stickiness) * offered_wage
                } else {
                    offered_wage
                };

                state.firms[firm_idx].hire(1, wage);
                state.households[hh_idx].become_employed(firm_idx, wage);
                total_matches += 1;
                seeker_idx += 1;
            }
        }
    }

    // ── 4. Statistics ────────────────────────────────────────────────────────
    let total_employed = state.households.iter().filter(|h| h.employed).count();
    let total_unemployed = state.households.len() - total_employed;
    let total = state.households.len();
    let unemployment_rate = if total > 0 {
        total_unemployed as f64 / total as f64
    } else {
        0.0
    };

    let wages: Vec<f64> = state
        .households
        .iter()
        .filter(|h| h.employed && h.wage > 0.0)
        .map(|h| h.wage)
        .collect();
    let average_wage = if wages.is_empty() {
        0.0
    } else {
        wages.iter().sum::<f64>() / wages.len() as f64
    };

    // ── 5. Unemployment benefit transfers ────────────────────────────────────
    let unemployed_count = total_unemployed;
    if unemployed_count > 0 && average_wage > 0.0 {
        let benefit = state.government.pay_unemployment_benefit(
            average_wage,
            unemployed_count,
            unemployment_benefit_ratio,
        );
        let per_hh = benefit / unemployed_count as f64;
        for hh in state.households.iter_mut() {
            if !hh.employed {
                hh.transfer_income = per_hh;
            }
        }
    }

    state.labor_last = LaborOutcome {
        total_employed,
        total_unemployed,
        unemployment_rate,
        average_wage,
        total_matches,
        total_separations,
    };
}

// ─────────────────────────────────────────────────────────────────────────────
// krabmaga Agent proxy for the labour market
// ─────────────────────────────────────────────────────────────────────────────

/// Proxy agent that clears the labour market within the krabmaga schedule.
///
/// Scheduled with ordering=2 (between firm agents at 3 and household agents at 1)
/// so it runs after all firms have stepped but before households step.
#[derive(Clone)]
pub struct LaborMarketAgent;

impl fmt::Display for LaborMarketAgent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "LaborMarketAgent")
    }
}

impl Agent for LaborMarketAgent {
    fn step(&mut self, state: &mut dyn State) {
        let state = state
            .as_any_mut()
            .downcast_mut::<EconomyState>()
            .expect("state should be EconomyState");
        clear_labor_market(state);
    }
}
