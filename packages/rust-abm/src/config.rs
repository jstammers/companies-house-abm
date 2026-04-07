/// Configuration parameters for the economy simulation.
///
/// Default values match the Python `ModelConfig` defaults.
#[derive(Clone, Debug)]
pub struct Config {
    // Firm behaviour
    pub price_markup: f64,
    pub inventory_target_ratio: f64,
    pub capacity_utilization_target: f64,
    pub markup_adjustment_speed: f64,

    // Household behaviour
    pub consumption_smoothing: f64,
    pub job_search_intensity: f64,
    pub income_mean: f64,
    pub income_std: f64,
    pub wealth_shape: f64,
    pub mpc_mean: f64,
    pub mpc_std: f64,

    // Bank behaviour
    pub capital_requirement: f64,
    pub capital_buffer: f64,
    pub base_interest_markup: f64,
    pub risk_premium_sensitivity: f64,
    pub lending_threshold: f64,
    pub risk_weight: f64,

    // Labour market
    pub separation_rate: f64,
    pub matching_efficiency: f64,
    pub wage_stickiness: f64,

    // Credit market
    pub default_rate_base: f64,
    pub rationing: bool,

    // Government
    pub tax_rate_corporate: f64,
    pub tax_rate_income: f64,
    pub spending_gdp_ratio: f64,
    pub unemployment_benefit_ratio: f64,
    pub deficit_target: f64,
    pub deficit_adjustment_speed: f64,

    // Central bank (Taylor rule)
    pub inflation_target: f64,
    pub inflation_coefficient: f64,
    pub output_gap_coefficient: f64,
    pub interest_rate_smoothing: f64,
    pub lower_bound: f64,

    // Sectors (for round-robin assignment)
    pub sectors: Vec<String>,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            price_markup: 0.15,
            inventory_target_ratio: 0.2,
            capacity_utilization_target: 0.85,
            markup_adjustment_speed: 0.1,

            consumption_smoothing: 0.7,
            job_search_intensity: 0.3,
            income_mean: 35_000.0,
            income_std: 15_000.0,
            wealth_shape: 2.0,
            mpc_mean: 0.8,
            mpc_std: 0.1,

            capital_requirement: 0.10,
            capital_buffer: 0.02,
            base_interest_markup: 0.02,
            risk_premium_sensitivity: 0.05,
            lending_threshold: 0.3,
            risk_weight: 1.0,

            separation_rate: 0.05,
            matching_efficiency: 0.3,
            wage_stickiness: 0.8,

            default_rate_base: 0.01,
            rationing: true,

            tax_rate_corporate: 0.19,
            tax_rate_income: 0.20,
            spending_gdp_ratio: 0.40,
            unemployment_benefit_ratio: 0.4,
            deficit_target: 0.03,
            deficit_adjustment_speed: 0.1,

            inflation_target: 0.02,
            inflation_coefficient: 1.5,
            output_gap_coefficient: 0.5,
            interest_rate_smoothing: 0.8,
            lower_bound: 0.001,

            sectors: vec![
                "manufacturing".to_string(),
                "construction".to_string(),
                "retail_trade".to_string(),
                "wholesale_trade".to_string(),
                "professional_services".to_string(),
                "financial_services".to_string(),
                "real_estate".to_string(),
                "information_technology".to_string(),
                "healthcare".to_string(),
                "accommodation_food".to_string(),
                "transportation".to_string(),
                "utilities".to_string(),
                "other_services".to_string(),
            ],
        }
    }
}
