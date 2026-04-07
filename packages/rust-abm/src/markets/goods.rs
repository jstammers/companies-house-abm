use crate::state::EconomyState;

/// Outcome of goods market clearing for one period.
#[derive(Clone, Debug, Default)]
pub struct GoodsOutcome {
    pub total_sales: f64,
    pub average_price: f64,
    pub excess_demand: f64,
    pub inflation: f64,
}

/// Clear the goods market in-place on the simulation state.
///
/// Mirrors the Python `GoodsMarket.clear()` logic exactly:
/// 1. Compute total demand (households + government).
/// 2. Compute total supply (firm inventory × price).
/// 3. Allocate demand across firms proportionally to price-competitiveness.
/// 4. Update firm turnover / inventory and compute inflation.
pub fn clear_goods_market(state: &mut EconomyState) {
    let previous_average_price = state.goods_average_price;

    let active_indices: Vec<usize> = (0..state.firms.len())
        .filter(|&i| !state.firms[i].bankrupt)
        .collect();

    // ── Demand side ──────────────────────────────────────────────────────────
    let total_demand: f64 = state.households.iter().map(|h| h.consumption).sum::<f64>()
        + state.government.expenditure;

    // ── Supply side ──────────────────────────────────────────────────────────
    let total_supply: f64 = active_indices
        .iter()
        .map(|&i| state.firms[i].inventory * state.firms[i].price)
        .sum();

    let excess_demand = total_demand - total_supply;

    if active_indices.is_empty() {
        state.goods_average_price = previous_average_price;
        state.goods_last = GoodsOutcome {
            total_sales: 0.0,
            average_price: previous_average_price,
            excess_demand,
            inflation: 0.0,
        };
        return;
    }

    // ── Matching: allocate demand proportional to competitiveness ────────────
    let max_price = active_indices
        .iter()
        .map(|&i| state.firms[i].price)
        .fold(f64::NEG_INFINITY, f64::max);

    let weights: Vec<f64> = active_indices
        .iter()
        .map(|&i| (max_price - state.firms[i].price + 1e-9).max(1e-9))
        .collect();
    let weight_sum: f64 = weights.iter().sum();

    let mut total_sales = 0.0f64;
    let markup_speed = state.config.markup_adjustment_speed;

    for (weight, &firm_idx) in weights.iter().zip(active_indices.iter()) {
        let share = weight / weight_sum;
        let demand_for_firm = total_demand * share;
        let available = state.firms[firm_idx].inventory * state.firms[firm_idx].price;
        let actual_sales = demand_for_firm.min(available);

        let quantity_sold = actual_sales / state.firms[firm_idx].price.max(1e-9);
        state.firms[firm_idx].inventory = (state.firms[firm_idx].inventory - quantity_sold).max(0.0);
        state.firms[firm_idx].turnover = actual_sales;
        total_sales += actual_sales;

        // Markup adaptation
        let firm_excess = (demand_for_firm - available) / available.max(1e-9);
        state.firms[firm_idx].adapt_markup(firm_excess, markup_speed);
    }

    // ── Average price and inflation ──────────────────────────────────────────
    let avg_price: f64 = active_indices
        .iter()
        .map(|&i| state.firms[i].price)
        .sum::<f64>()
        / active_indices.len() as f64;

    let inflation = if previous_average_price > 0.0 {
        (avg_price - previous_average_price) / previous_average_price
    } else {
        0.0
    };

    state.goods_average_price = avg_price;
    state.goods_last = GoodsOutcome {
        total_sales,
        average_price: avg_price,
        excess_demand,
        inflation,
    };
}
