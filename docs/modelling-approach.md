# Modelling Approach

This page documents the modelling approach implemented in the Companies House ABM.  The model simulates the UK economy as a complex adaptive system where heterogeneous agents interact through decentralised markets.

## Theoretical Foundations

The model draws on four streams of economic thought:

1. **Stock-Flow Consistent (SFC) modelling** — Every financial flow results in a consistent change in stocks.  Money is conserved; there are no "black holes" in the accounting.
2. **Post-Keynesian economics** — Demand-driven dynamics, financial constraints and persistent unemployment are central features.
3. **Complexity economics** — Macro outcomes emerge from micro interactions among heterogeneous, boundedly rational agents.
4. **Input-Output analysis** — Sectoral interdependencies shape how shocks propagate through the economy.

## Agents

### Firm

Firms are the core productive agents.  Each holds a balance sheet initialised from Companies House XBRL data and executes the following steps each period:

1. **Plan production** — target output equals expected sales plus an inventory replenishment buffer.
2. **Set price** — a markup over unit labour cost, adapted in response to excess demand.
3. **Determine labour demand** — vacancies are posted if more workers are needed.
4. **Produce** — output is the minimum of desired production, labour capacity and physical capital.
5. **Update financials** — revenue is recorded, wages paid, profit and equity updated.  Firms whose equity-to-capital ratio falls below a threshold go bankrupt.

Key attributes: `sector`, `employees`, `turnover`, `capital`, `cash`, `debt`, `equity`, `markup`, `inventory`.

### Household

Households supply labour, consume goods, and participate in the housing market.  Each period:

1. **Receive income** — wages if employed, transfer income if not.
2. **Make housing payment** — mortgage amortisation (if owner) or rent payment (if renter).
3. **Consume** — a consumption function combining a fraction of remaining income (MPC) and a small draw on wealth.
4. **Save** — unspent income accumulates as deposits/wealth.
5. **Decide buy or rent** — compare expected cost of owning vs renting using backward/forward-looking price expectations (Farmer 2025).

Key attributes: `income`, `wealth`, `mpc`, `employed`, `wage`, `tenure`, `property_id`, `mortgage`, `rent`, `housing_wealth`, `wants_to_buy`.

### Bank

Banks accept deposits, extend credit, originate mortgages, and must satisfy regulatory constraints.  Each period:

1. **Set lending rate** — policy rate plus a markup, with a risk premium that rises with non-performing loans (NPLs).
2. **Set mortgage rate** — policy rate plus a spread and risk premium.
3. **Evaluate loans** — check collateral coverage and debt-service coverage ratios.
4. **Evaluate mortgages** — apply FPC macroprudential checks (LTV, DTI, affordability stress test).
5. **Originate mortgages** — create mortgage contracts for approved applications.
6. **Assess foreclosures** — foreclose on mortgages with 3+ months of arrears.
7. **Record income/expense** — interest income on loans, interest expense on deposits, provisions for NPLs.
8. **Update capital** — profit added to equity.  Mortgage book included in risk-weighted assets at 0.35 weight.

Regulatory constraints follow Basel III: a minimum capital-adequacy ratio and a capital buffer above that minimum.

### Central Bank

The central bank sets the policy interest rate using a **Taylor rule**:

$$
i_t = \rho \, i_{t-1} + (1-\rho) \left[ \pi^* + \phi_\pi (\pi_t - \pi^*) + \phi_y \hat{y}_t \right]
$$

where $\rho$ is the smoothing parameter, $\pi^*$ the inflation target, $\pi_t$ observed inflation, and $\hat{y}_t$ the output gap.  A lower bound prevents the rate from falling below a floor.

### Government

The government collects corporate and income taxes, spends a fraction of GDP, and pays unemployment benefits.  A fiscal rule adjusts spending when the deficit-to-GDP ratio deviates from a target.

## Markets

### Goods Market

Firms post prices and supply goods from inventory.  Demand comes from household consumption and government spending.  Demand is allocated across firms in proportion to **price competitiveness** (lower-priced firms attract a larger share).  After clearing, firms observe their individual excess-demand signal and adjust their markup accordingly.

### Labour Market

Matching occurs with frictions:

1. **Exogenous separations** — each period a fraction of employed workers lose their jobs.
2. **Vacancy posting** — firms post vacancies based on production plans.
3. **Job search** — unemployed households search with a configurable intensity.
4. **Matching** — seekers are matched to vacancies with a probability controlled by matching efficiency.  Wages are a sticky blend of the firm's offered wage and the economy-wide average.

### Credit Market

Firms with negative cash balances apply for loans.  Applications are distributed across banks in round-robin fashion.  Each bank evaluates the application against collateral and debt-service-coverage thresholds.  When credit rationing is enabled, applications that fail the evaluation are rejected outright.

### Housing Market

The housing market uses **bilateral matching with aspiration-level pricing** (Farmer 2025), fundamentally different from the equilibrium-clearing approach used for goods and labour.  Each period:

1. **Sellers update asking prices** — unsold listings are reduced by 10% per period; after 6 months they are delisted (aspiration-level adaptation).
2. **Buyers search** — each buyer visits up to 10 listed properties within their budget and selects the best value.
3. **Mortgage evaluation** — banks apply FPC macroprudential checks: LTV cap (90%), DTI limit (4.5x), and an affordability stress test (+3% rate buffer).
4. **Transactions** — if the mortgage is approved, ownership transfers, the bank creates a mortgage, and aggregate statistics are updated.

Properties are passive assets (not agents) with region, type, quality, and price attributes.  Mortgages are shared reference objects between banks and households.

See [Housing Market](housing-market.md) for full documentation.

## Within-Period Sequence

Each simulation period follows this 16-step sequence:

1. Government resets period flows.
2. Central bank sets the policy rate (Taylor rule).
3. Banks update lending rates **and mortgage rates** from the new policy rate.
4. Credit market clears (firms borrow, defaults processed).
5. Firms step (plan, price, labour demand, produce, financials).
6. Labour market clears (separations, matching).
7. **Banks assess foreclosures** (mortgages in arrears).
8. Households step (income, **housing payment**, consumption, saving).
9. **Households make buy/sell decisions** (buy-vs-rent comparison, owner sell probability).
10. **Housing market clears** (bilateral matching, mortgage origination).
11. Government calculates spending.
12. Goods market clears (demand allocated, markup adaptation).
13. Taxes collected (corporate and income).
14. Government ends period (deficit, debt).
15. Central bank observes inflation and output gap.
16. Banks step (income calculation, capital update).

## Configuration

All parameters are stored in `config/model_parameters.yml` and loaded into frozen dataclass objects via `companies_house_abm.abm.config.load_config()`.  Parameters are organised by component:

| Section | Examples |
|---------|----------|
| `simulation` | `periods`, `seed`, `warm_up_periods` |
| `agents.firms` | `sample_size`, `sectors`, `entry_rate` |
| `behavior.firms` | `price_markup`, `inventory_target_ratio` |
| `agents.households` | `count`, `mpc_mean`, `income_mean` |
| `agents.banks` | `count`, `capital_requirement` |
| `agents.properties` | `count`, `regions`, `types`, `average_price` |
| `behavior.banks.mortgage` | `max_ltv`, `max_dti`, `stress_test_buffer` |
| `markets.housing` | `search_intensity`, `price_reduction_rate`, `rental_yield` |
| `policy.central_bank` | Taylor rule coefficients |
| `policy.government` | Tax rates, spending ratio, transfers |
| `markets.*` | Price adjustment speed, matching efficiency |

## Validation Targets

The model aims to reproduce the following UK stylised facts:

| Fact | Target |
|------|--------|
| Firm size distribution | Power law, Pareto $\alpha \approx 1.06$ |
| GDP growth (quarterly) | Mean $\approx 0.5\%$, std $\approx 1\%$ |
| Unemployment rate | Mean $\approx 4.5\%$ |
| Inflation | Mean $\approx 2\%$ |
| Wage share of income | $\approx 55\%$ |
| Investment / GDP | $\approx 17\%$ |
| Homeownership rate | $\approx 64\%$ |
| Average house price | $\approx$ £285,000 |
| Price-to-income ratio | $\approx 8.3$ |
| Gross rental yield | $4{-}5\%$ |

## Interactive Exploration

Marimo notebooks in `notebooks/` allow interactive parameter exploration:

| Notebook | Description |
|----------|-------------|
| `firm_agent.py` | Single-firm dynamics and parameter sensitivity |
| `household_agent.py` | Consumption function and wealth distribution |
| `bank_agent.py` | Lending decisions and NPL impact |
| `policy_agents.py` | Taylor rule response and fiscal dynamics |
| `ecosystem.py` | Full multi-agent simulation |

Run any notebook with `uv run marimo edit notebooks/<name>.py`.
