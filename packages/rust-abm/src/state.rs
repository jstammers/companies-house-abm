use std::any::Any;

use krabmaga::engine::{schedule::Schedule, state::State};
use rand::{Rng, SeedableRng};
use rand::rngs::StdRng;
use rand_distr::{Distribution, LogNormal, Normal, Pareto};

use crate::agents::{BankData, CentralBankData, FirmAgent, FirmData, GovernmentData, HouseholdAgent, HouseholdData};
use crate::config::Config;
use crate::markets::{
    clear_credit_market, clear_goods_market, CreditOutcome, GoodsOutcome, LaborMarketAgent,
    LaborOutcome,
};

// ─────────────────────────────────────────────────────────────────────────────
// Period record
// ─────────────────────────────────────────────────────────────────────────────

/// Aggregate statistics recorded for a single simulation period.
#[derive(Clone, Debug, Default)]
pub struct PeriodRecord {
    pub period: u64,
    pub gdp: f64,
    pub inflation: f64,
    pub unemployment_rate: f64,
    pub average_wage: f64,
    pub policy_rate: f64,
    pub government_deficit: f64,
    pub government_debt: f64,
    pub total_lending: f64,
    pub firm_bankruptcies: usize,
    pub total_employment: usize,
}

// ─────────────────────────────────────────────────────────────────────────────
// Economy state (implements krabmaga State)
// ─────────────────────────────────────────────────────────────────────────────

/// Central state struct holding all agent data and simulation outcomes.
///
/// This implements the krabmaga `State` trait.  Agent *proxy* structs
/// (FirmAgent, HouseholdAgent, …) are stored in the krabmaga Schedule;
/// the actual mutable data for every agent lives here.
pub struct EconomyState {
    // Agent data
    pub firms: Vec<FirmData>,
    pub households: Vec<HouseholdData>,
    pub banks: Vec<BankData>,
    pub central_bank: CentralBankData,
    pub government: GovernmentData,

    // Market outcomes (updated each period)
    pub goods_average_price: f64,
    pub goods_last: GoodsOutcome,
    pub labor_last: LaborOutcome,
    pub credit_last: CreditOutcome,

    // Configuration
    pub config: Config,

    // Random number generator
    pub rng: StdRng,

    // Simulation records
    pub records: Vec<PeriodRecord>,
    pub current_period: u64,

    // How many agents of each type were requested
    n_firms: usize,
    n_households: usize,
    n_banks: usize,
}

impl EconomyState {
    /// Create a new economy state and immediately initialise agent data.
    pub fn new(n_firms: usize, n_households: usize, n_banks: usize, seed: u64, config: Config) -> Self {
        let mut rng = StdRng::seed_from_u64(seed);
        let firms = Self::create_firms(n_firms, &config, &mut rng);
        let households = Self::create_households(n_households, &config, &mut rng);
        let banks = Self::create_banks(n_banks, &mut rng);
        let central_bank = CentralBankData::new(config.inflation_target);
        let government = GovernmentData::new();

        let mut state = EconomyState {
            firms,
            households,
            banks,
            central_bank,
            government,
            goods_average_price: 1.0,
            goods_last: GoodsOutcome::default(),
            labor_last: LaborOutcome::default(),
            credit_last: CreditOutcome::default(),
            config,
            rng,
            records: Vec::new(),
            current_period: 0,
            n_firms,
            n_households,
            n_banks,
        };
        state.initial_employment();
        state
    }

    // ─── Agent initialisation (mirrors Python Simulation.initialize_agents) ──

    fn create_firms(n: usize, cfg: &Config, rng: &mut StdRng) -> Vec<FirmData> {
        let mut firms = Vec::with_capacity(n);
        let wage_ln = LogNormal::new((35_000.0_f64 / 4.0).ln(), 0.3).unwrap();
        let turnover_ln = LogNormal::new((100_000.0_f64).ln(), 1.0).unwrap();
        let capital_ln = LogNormal::new((50_000.0_f64).ln(), 1.0).unwrap();
        let cash_ln = LogNormal::new((10_000.0_f64).ln(), 0.8).unwrap();

        for i in 0..n {
            let sector = cfg.sectors[i % cfg.sectors.len()].clone();
            let employees: u32 = rng.gen_range(1..50);
            let wage_rate = wage_ln.sample(rng);
            let turnover = turnover_ln.sample(rng);
            let capital = capital_ln.sample(rng);
            let cash = cash_ln.sample(rng);

            firms.push(FirmData::new(
                sector,
                employees,
                wage_rate,
                turnover,
                capital,
                cash,
                cfg.price_markup,
            ));
        }
        firms
    }

    fn create_households(n: usize, cfg: &Config, rng: &mut StdRng) -> Vec<HouseholdData> {
        let mut households = Vec::with_capacity(n);
        let income_ln =
            LogNormal::new(cfg.income_mean.ln(), cfg.income_std / cfg.income_mean).unwrap();
        let mpc_normal = Normal::new(cfg.mpc_mean, cfg.mpc_std).unwrap();

        for _ in 0..n {
            let income = income_ln.sample(rng) / 4.0; // quarterly
            let wealth_pareto = Pareto::new(1.0, cfg.wealth_shape).unwrap();
            let wealth = (wealth_pareto.sample(rng) - 1.0) * income; // pareto gives >= 1
            let mpc = mpc_normal.sample(rng).clamp(0.1, 0.99);
            households.push(HouseholdData::new(income, wealth.max(0.0), mpc));
        }
        households
    }

    fn create_banks(n: usize, rng: &mut StdRng) -> Vec<BankData> {
        let mut banks = Vec::with_capacity(n);
        let capital_ln = LogNormal::new((1e9_f64).ln(), 0.5).unwrap();

        for _ in 0..n {
            let capital = capital_ln.sample(rng);
            let reserves = capital * 0.1;
            banks.push(BankData::new(capital, reserves));
        }
        banks
    }

    /// Assign households to firms for the initial employment state.
    fn initial_employment(&mut self) {
        let mut hh_idx = 0usize;
        for firm_idx in 0..self.firms.len() {
            let n_workers = self.firms[firm_idx].employees as usize;
            let wage_rate = self.firms[firm_idx].wage_rate;
            for _ in 0..n_workers {
                if hh_idx >= self.households.len() {
                    return;
                }
                self.households[hh_idx].become_employed(firm_idx, wage_rate);
                hh_idx += 1;
            }
        }
    }

    // ─── Per-period step helpers ─────────────────────────────────────────────

    /// Run the pre-agent-step sequence (government begin → credit market).
    pub fn run_pre_step(&mut self) {
        // 1. Government begins period
        self.government.begin_period();

        // 2. Central bank sets policy rate (Taylor rule)
        self.central_bank.step(
            self.config.inflation_coefficient,
            self.config.output_gap_coefficient,
            self.config.interest_rate_smoothing,
            self.config.lower_bound,
        );

        // 3. Banks update lending rates based on new policy rate
        let policy_rate = self.central_bank.policy_rate;
        let base_markup = self.config.base_interest_markup;
        let risk = self.config.risk_premium_sensitivity;
        for bank in self.banks.iter_mut() {
            bank.set_lending_rate(policy_rate, base_markup, risk);
        }

        // 4. Credit market clears
        clear_credit_market(self);
    }

    /// Run the post-agent-step sequence (government spending → CB observes).
    pub fn run_post_step(&mut self) {
        // 5. GDP estimation (sum non-bankrupt firm turnover)
        let gdp: f64 = self
            .firms
            .iter()
            .filter(|f| !f.bankrupt)
            .map(|f| f.turnover)
            .sum();
        self.government.gdp_estimate = gdp;

        // 6. Government calculates spending
        self.government
            .calculate_spending(self.config.spending_gdp_ratio);

        // 7. Goods market clears
        clear_goods_market(self);

        // 8. Tax collection
        let corp_rate = self.config.tax_rate_corporate;
        let income_rate = self.config.tax_rate_income;
        for firm in self.firms.iter_mut() {
            if firm.profit > 0.0 && !firm.bankrupt {
                let tax = (firm.profit * corp_rate).max(0.0);
                self.government.tax_revenue += tax;
                firm.cash -= tax;
            }
        }
        for hh in self.households.iter_mut() {
            if hh.income > 0.0 {
                let tax = (hh.income * income_rate).max(0.0);
                self.government.tax_revenue += tax;
                hh.wealth -= tax;
            }
        }

        // 9. Government step (fiscal rule) + end period
        self.government
            .apply_fiscal_rule(self.config.deficit_target, self.config.deficit_adjustment_speed);
        self.government.end_period();

        // 10. Central bank observes inflation and output gap
        self.central_bank
            .update_observations(self.goods_last.inflation, 0.0);

        // 11. Banks do their full period step (update income and capital)
        let policy_rate = self.central_bank.policy_rate;
        let base_markup = self.config.base_interest_markup;
        let risk = self.config.risk_premium_sensitivity;
        for bank in self.banks.iter_mut() {
            bank.step(policy_rate, base_markup, risk);
        }
    }

    /// Record aggregate statistics for the completed period.
    pub fn record(&mut self) {
        self.current_period += 1;
        let bankruptcies = self.firms.iter().filter(|f| f.bankrupt).count();
        self.records.push(PeriodRecord {
            period: self.current_period,
            gdp: self.government.gdp_estimate,
            inflation: self.goods_last.inflation,
            unemployment_rate: self.labor_last.unemployment_rate,
            average_wage: self.labor_last.average_wage,
            policy_rate: self.central_bank.policy_rate,
            government_deficit: self.government.deficit,
            government_debt: self.government.debt,
            total_lending: self.credit_last.total_lending,
            firm_bankruptcies: bankruptcies,
            total_employment: self.labor_last.total_employed,
        });
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// krabmaga State implementation
// ─────────────────────────────────────────────────────────────────────────────

impl State for EconomyState {
    /// Schedule all agent proxies when the simulation starts.
    ///
    /// Execution order per krabmaga period (lower ordering = runs first):
    ///   0 → FirmAgent          (firms plan, price, produce)
    ///   1 → LaborMarketAgent   (labour market clears + transfers set)
    ///   2 → HouseholdAgent     (households receive income, consume, save)
    fn init(&mut self, schedule: &mut Schedule) {
        // Schedule firm proxies (ordering=0 → run first)
        for i in 0..self.n_firms {
            schedule.schedule_repeating(Box::new(FirmAgent { id: i }), 0.0, 0);
        }

        // Schedule labor market proxy (ordering=1 → run after firms)
        schedule.schedule_repeating(Box::new(LaborMarketAgent), 0.0, 1);

        // Schedule household proxies (ordering=2 → run after labor market)
        for i in 0..self.n_households {
            schedule.schedule_repeating(Box::new(HouseholdAgent { id: i }), 0.0, 2);
        }

        // Banks are stepped directly in after_step() to preserve the Python
        // model's ordering (banks update after goods market and tax collection).
    }

    fn as_any_mut(&mut self) -> &mut dyn Any {
        self
    }

    fn as_any(&self) -> &dyn Any {
        self
    }

    fn as_state_mut(&mut self) -> &mut dyn State {
        self
    }

    fn as_state(&self) -> &dyn State {
        self
    }

    fn reset(&mut self) {
        // Re-initialise from scratch (used by simulate! macro for repetitions)
        let mut rng = StdRng::seed_from_u64(42);
        self.firms = Self::create_firms(self.n_firms, &self.config.clone(), &mut rng);
        self.households =
            Self::create_households(self.n_households, &self.config.clone(), &mut rng);
        self.banks = Self::create_banks(self.n_banks, &mut rng);
        self.central_bank = CentralBankData::new(self.config.inflation_target);
        self.government = GovernmentData::new();
        self.goods_average_price = 1.0;
        self.goods_last = GoodsOutcome::default();
        self.labor_last = LaborOutcome::default();
        self.credit_last = CreditOutcome::default();
        self.rng = rng;
        self.records.clear();
        self.current_period = 0;
        self.initial_employment();
    }

    /// Run the pre-agent step (government, CB, banks, credit market).
    fn before_step(&mut self, _schedule: &mut Schedule) {
        self.run_pre_step();
    }

    /// Run the post-agent step (goods market, taxes, government end, CB observe, banks).
    fn after_step(&mut self, _schedule: &mut Schedule) {
        self.run_post_step();
    }

    /// Record aggregate statistics after each completed period.
    fn update(&mut self, step: u64) {
        if step > 0 {
            self.record();
        }
    }
}
