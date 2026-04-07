use crate::state::EconomyState;

/// Outcome of credit market clearing for one period.
#[derive(Clone, Debug, Default)]
pub struct CreditOutcome {
    pub total_lending: f64,
    pub total_applications: usize,
    pub total_approvals: usize,
    pub total_rejections: usize,
    pub average_rate: f64,
    pub total_defaults: usize,
}

/// Clear the credit market in-place on the simulation state.
///
/// Mirrors Python `CreditMarket.clear()`:
/// 1. Process defaults from bankrupt firms.
/// 2. Identify firms with negative cash (credit demand).
/// 3. Match firms to banks (round-robin).
/// 4. Banks evaluate and extend or reject loans.
pub fn clear_credit_market(state: &mut EconomyState) {
    let default_base = state.config.default_rate_base;
    let rationing = state.config.rationing;
    let cap_req = state.config.capital_requirement;
    let cap_buf = state.config.capital_buffer;
    let risk_w = state.config.risk_weight;
    let lend_thresh = state.config.lending_threshold;

    let mut total_lending = 0.0f64;
    let mut total_applications = 0usize;
    let mut total_approvals = 0usize;
    let mut total_rejections = 0usize;
    let mut total_defaults = 0usize;
    let mut rates: Vec<f64> = Vec::new();

    let n_banks = state.banks.len();
    if n_banks == 0 {
        state.credit_last = CreditOutcome::default();
        return;
    }

    // ── 1. Process defaults ──────────────────────────────────────────────────
    for firm_idx in 0..state.firms.len() {
        if state.firms[firm_idx].bankrupt && state.firms[firm_idx].debt > 0.0 {
            let firm_debt = state.firms[firm_idx].debt;
            for bank in state.banks.iter_mut() {
                if bank.loans > 0.0 {
                    let share = firm_debt.min(bank.loans);
                    bank.record_default(share * default_base);
                    total_defaults += 1;
                }
            }
        }
    }

    // ── 2. Process applications ──────────────────────────────────────────────
    let mut bank_idx = 0usize;

    for firm_idx in 0..state.firms.len() {
        if state.firms[firm_idx].bankrupt {
            continue;
        }
        if state.firms[firm_idx].cash >= 0.0 {
            continue;
        }

        let amount = (-state.firms[firm_idx].cash).abs();
        total_applications += 1;

        let b_idx = bank_idx % n_banks;
        bank_idx += 1;

        let approved = state.banks[b_idx].evaluate_loan(
            amount,
            state.firms[firm_idx].equity,
            state.firms[firm_idx].turnover,
            cap_req,
            cap_buf,
            risk_w,
            lend_thresh,
        );

        if approved || !rationing {
            let rate = state.banks[b_idx].extend_loan(amount);
            state.firms[firm_idx].cash += amount;
            state.firms[firm_idx].debt += amount;
            total_approvals += 1;
            total_lending += amount;
            rates.push(rate);
        } else {
            total_rejections += 1;
        }
    }

    let average_rate = if rates.is_empty() {
        0.0
    } else {
        rates.iter().sum::<f64>() / rates.len() as f64
    };

    state.credit_last = CreditOutcome {
        total_lending,
        total_applications,
        total_approvals,
        total_rejections,
        average_rate,
        total_defaults,
    };
}
