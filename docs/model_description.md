# UK Economy ABM: Model Description (ODD+D Protocol)

This document describes the Agent-Based Model of the UK Economy following the **ODD+D** (Overview, Design concepts, Details + Decision-making) protocol ([Müller et al., 2013](https://doi.org/10.18564/jasss.2259)).

## 1. Purpose and Scope

### 1.1 Purpose

The UK Economy ABM aims to:

1. **Explain** macro-economic phenomena (GDP growth, inflation, unemployment, business cycles) as **emergent outcomes** of micro-level agent interactions.
2. **Forecast** near-term economic trajectories under different scenarios (policy changes, external shocks).
3. **Evaluate** policy interventions (fiscal stimulus, interest rate changes, industrial policy) with distributional impact analysis.
4. **Understand** complex dynamics: financial instability, supply chain contagion, regional inequality, structural transformation.

### 1.2 Scope

- **Spatial scale**: United Kingdom, disaggregated by NUTS-2 regions.
- **Temporal scale**: Monthly time steps, typical simulation horizon 120–600 months (10–50 years).
- **Agent populations**:
  - ~5 million **Firm** agents (initialised from Companies House data)
  - ~30 million **Household** agents (synthetic population calibrated to ONS)
  - ~10 **Bank** agents
  - 1 **Central Bank** agent
  - 1 **Government** agent
  - ~100 **Investor Fund** agents
- **Key processes**: Production, consumption, employment, credit creation, firm entry/exit, price/wage setting, policy interventions.

## 2. Entities, State Variables, and Scales

### 2.1 Entities

#### 2.1.1 Firm Agent

| State Variable | Type | Description |
|---|---|---|
| `id` | u64 | Unique identifier |
| `company_number` | String | Companies House registration number |
| `sector` | SICCode | Primary SIC code (5-digit) |
| `region` | NUTSRegion | NUTS-2 region code |
| `age_months` | u32 | Age since incorporation |
| `legal_form` | String | Company category (Ltd, PLC, etc.) |
| `capital` | f64 | Physical capital stock (£) |
| `debt` | f64 | Outstanding bank loans (£) |
| `equity` | f64 | Net worth / shareholder funds (£) |
| `inventory` | f64 | Unsold goods (units) |
| `price` | f64 | Current output price (£/unit) |
| `wage` | f64 | Wage offered (£/month) |
| `production_plan` | f64 | Planned output (units) next period |
| `employees` | Vec<u64> | IDs of employed households |
| `suppliers` | Vec<u64> | IDs of supplier firms |
| `customers` | Vec<u64> | IDs of customer firms |
| `strategy` | FirmStrategy | Markup rule parameters, mutation state |
| `expectations` | Expectations | Adaptive forecast of demand, prices |
| `alive` | bool | False if exited market |
| `months_insolvent` | u32 | Counter for insolvency duration |

#### 2.1.2 Household Agent

| State Variable | Type | Description |
|---|---|---|
| `id` | u64 | Unique identifier |
| `region` | NUTSRegion | Residence region |
| `income_decile` | u8 | Income decile (1–10) |
| `wealth` | f64 | Liquid assets (£) |
| `employed_by` | Option<u64> | Employer firm ID (None if unemployed) |
| `reservation_wage` | f64 | Minimum acceptable wage (£/month) |
| `propensity_to_consume` | f64 | Marginal propensity to consume (0–1) |
| `consumption_basket` | HashMap<SICCode, f64> | Sector weights for spending |

#### 2.1.3 Bank Agent

| State Variable | Type | Description |
|---|---|---|
| `id` | u64 | Unique identifier |
| `loans` | HashMap<u64, Loan> | Outstanding loans to firms |
| `deposits` | f64 | Household deposits (£) |
| `reserves` | f64 | Central bank reserves (£) |
| `equity` | f64 | Bank capital (£) |
| `risk_appetite` | f64 | Lending threshold parameter |

#### 2.1.4 Central Bank Agent

| State Variable | Type | Description |
|---|---|---|
| `base_rate` | f64 | Policy interest rate (annual %) |
| `capital_buffer` | f64 | Counter-cyclical capital buffer (%) |
| `qe_stock` | f64 | Outstanding QE bond purchases (£bn) |

#### 2.1.5 Government Agent

| State Variable | Type | Description |
|---|---|---|
| `corporation_tax_rate` | f64 | % |
| `vat_rate` | f64 | % |
| `income_tax_brackets` | Vec<(f64, f64)> | (threshold, rate) |
| `unemployment_benefit` | f64 | Monthly payment (£) |
| `spending_budget` | f64 | Monthly government consumption (£) |
| `debt` | f64 | National debt (£) |

#### 2.1.6 Investor Fund Agent

| State Variable | Type | Description |
|---|---|---|
| `id` | u64 | Unique identifier |
| `holdings` | HashMap<u64, f64> | (firm_id, equity_stake) |
| `cash` | f64 | Uninvested cash (£) |

### 2.2 Spatial Scales

- **NUTS-2 regions** (41 UK regions): Firms and households are located in one region. Trade and labour mobility between regions are subject to friction costs.

### 2.3 Temporal Scales

- **Time step**: 1 month.
- **Typical run length**: 120–600 months (10–50 years).

## 3. Process Overview and Scheduling

Each monthly time step follows this sequence:

1. **Policy Setting**
   - Government updates tax rates, spending, transfers.
   - Central Bank updates base rate, capital buffer.

2. **Banking Sector**
   - Banks update lending rates based on base rate + risk spread.
   - Banks assess capital adequacy, adjust risk appetite.

3. **Firm Planning**
   - Update demand/price expectations (adaptive).
   - Plan production, set output price.
   - Determine labour demand, post vacancies + wage.
   - Calculate credit needs.

4. **Credit Market Clearing**
   - Firms apply to banks.
   - Banks screen, approve/reject, set loan terms.

5. **Labour Market Matching**
   - Unemployed households apply to random subset of vacancies.
   - Firms hire from applicants.
   - Unsuccessful applicants update reservation wage.

6. **Production**
   - Firms purchase intermediate inputs from supplier network.
   - Firms produce using capital, labour, intermediates (Leontief/CES).

7. **Intermediate Goods Market**
   - Firm-to-firm trade via input–output network.

8. **Household Consumption Decision**
   - Households receive wages + transfers.
   - Allocate budget across sectors, search for goods.

9. **Consumer Goods Market**
   - Households purchase from firms (with search friction).
   - Firms sell inventory, update revenue.

10. **Firm Accounting**
    - Compute profits, pay taxes, service debt, pay dividends.
    - Update equity.

11. **Investor Portfolio Rebalancing**
    - Funds adjust equity holdings based on momentum/mean-reversion.

12. **Financial Market Clearing**
    - Equity prices adjust via order book.

13. **Firm Entry/Exit**
    - Exit: Firms with `equity < 0` for `INSOLVENCY_THRESHOLD` months exit.
    - Entry: New firms spawn stochastically (rate calibrated to CH incorporation data).

14. **Statistics Collection**
    - Aggregate GDP, CPI, unemployment rate, Gini coefficient, credit-to-GDP, etc.

## 4. Design Concepts

### 4.1 Theoretical Foundations

The model is grounded in **complexity economics** ([Arthur, 2015](https://doi.org/10.1126/science.1243089)):

- **Emergence**: Macro patterns emerge from micro interactions, not imposed.
- **Non-equilibrium**: No assumption of convergence to equilibrium.
- **Bounded rationality**: Agents use heuristics, not optimisation.
- **Heterogeneity**: Agent diversity drives aggregate outcomes.
- **Networks**: Production and financial networks structure interactions.
- **Adaptation**: Agents learn, strategies evolve.

### 4.2 Emergence

The following phenomena **emerge** without being explicitly programmed:

- Business cycles (boom-bust dynamics)
- Phillips curve (inflation–unemployment trade-off)
- Beveridge curve (vacancy–unemployment relationship)
- Okun's law (output gap–unemployment correlation)
- Fat-tailed firm size distribution
- Wealth inequality dynamics
- Credit pro-cyclicality

### 4.3 Adaptation

- **Firms**: Adaptive expectations (demand, price), evolutionary strategy mutation (markup rules).
- **Households**: Reservation wage adjusts based on unemployment duration.
- **Banks**: Risk appetite adjusts pro-cyclically (herding).

### 4.4 Objectives

- **Firms**: Maximise profit (but via bounded-rational heuristics, not optimisation).
- **Households**: Satisfice consumption needs; supply labour when wage ≥ reservation wage.
- **Banks**: Maximise profit subject to capital constraint; avoid excessive risk.
- **Central Bank**: Stabilise inflation (2% target) and output gap (Taylor rule).
- **Government**: Balance fiscal rules (debt-to-GDP target) with countercyclical policy.

### 4.5 Learning

- **Adaptive expectations**: Agents form forecasts as weighted average of past observations.
- **Reinforcement learning**: Firms with successful pricing strategies mutate parameters less frequently.
- **Social learning**: Investor sentiment spreads via network (opinion dynamics).

### 4.6 Prediction

- Agents form **bounded-rational forecasts**:
  - Demand: exponential smoothing of recent sales.
  - Prices: adaptive expectations of competitor prices.
  - Wages: follow sectoral wage inflation with lag.

### 4.7 Sensing

- **Firms**: Observe own sales, inventory; local market prices (not global equilibrium).
- **Households**: Observe posted wages, goods prices (limited search).
- **Banks**: Observe firm balance sheets (debt, equity, revenue).

### 4.8 Interaction

- **Direct**: Firm–household (employment), firm–firm (supply chain), household–firm (consumption), firm–bank (credit).
- **Indirect**: Via markets (price signals), via networks (contagion).
- **Spatial**: Inter-regional trade/migration with friction costs.

### 4.9 Stochasticity

- Firm entry (Poisson process calibrated to CH data).
- Household job search (random matching).
- Strategy mutation (low-probability random perturbation).
- Demand shocks (sector-specific stochastic shocks).

### 4.10 Collectives

- **Sectors**: Firms grouped by SIC code for input–output calibration.
- **Regions**: Spatial aggregation for policy analysis.
- **Income deciles**: Household groups for distributional analysis.

### 4.11 Observation

**Time-series outputs** (monthly):
- GDP (sum of firm value-added)
- CPI (consumption-weighted price index)
- Unemployment rate
- Wage inflation
- Credit-to-GDP ratio
- Gini coefficient (wealth, income)
- Firm birth/death rates
- Sectoral output shares

**Micro-data outputs** (snapshots):
- Firm-level: size, age, profitability, debt ratio
- Household-level: income, wealth, employment status
- Network topology: supply-chain degree distribution, clustering

**Validation targets**:
- Stylised facts (e.g., Zipf's law for firm size, Laplace distribution for firm growth rates)
- Historical UK time-series (GDP growth, inflation, unemployment)

## 5. Initialisation

### 5.1 Firm Agents

- **Source**: Companies House BasicCompanyData snapshot (active companies only).
- **Direct mapping**: `company_number`, `sector` (SIC), `region` (postcode → NUTS-2), `age_months` (from incorporation date), `legal_form`.
- **Imputation**: Missing financial variables (capital, revenue, employees) are imputed using sector × size-band conditional distributions estimated from ONS Annual Business Survey + FAME database.
- **Initial state**:
  - `equity = capital * 0.3` (typical debt-to-equity ratio)
  - `debt = capital * 0.7`
  - `inventory = 0`
  - `price` = sector-average price
  - `wage` = sector-average wage
  - `production_plan = expected_demand` (from sector output data)

### 5.2 Household Agents

- **Synthetic population**: ~30 million agents generated to match:
  - Regional population (ONS mid-year estimates)
  - Income distribution (ONS Effects of Taxes and Benefits)
  - Wealth distribution (ONS Wealth and Assets Survey)
- **Initial state**:
  - 95% employed (matched randomly to firms in same region, weighted by firm size)
  - `reservation_wage = 0.8 * market_wage`
  - `wealth` drawn from empirical distribution
  - `consumption_basket` set to empirical sector spending shares

### 5.3 Banks

- 10 banks with market shares matching UK concentration (top 5 dominate).
- Initial `equity` calibrated to Basel III capital ratios.
- Initial `loans` and `deposits` match aggregate UK banking statistics.

### 5.4 Central Bank, Government, Investors

- Central Bank: `base_rate = 0.5%` (2024 baseline).
- Government: Tax rates set to current UK statutory rates; `debt = £2.5 trillion`.
- Investors: 100 funds with random initial holdings.

### 5.5 Network Initialisation

- **Input–output network**: Sector-level coefficients from ONS Supply-Use Tables. Firm-to-firm links created via preferential attachment within sector pairs.
- **Spatial network**: Regions fully connected, with trade costs proportional to geographic distance.

## 6. Input Data

| Dataset | Source | Use |
|---|---|---|
| Companies House BasicCompanyData | Companies House bulk download | Firm initialisation |
| Companies House XBRL Accounts | stream-read-xbrl API | Financial variables (revenue, assets, employees) |
| ONS Supply and Use Tables | ONS | Input–output coefficients |
| ONS Annual Business Survey | ONS | Sector productivity, wages |
| ONS Income Distribution | ONS | Household income calibration |
| ONS Wealth and Assets Survey | ONS | Household wealth calibration |
| Bank of England Statistics | BoE | Interest rates, credit aggregates |
| ONS Labour Force Survey | ONS | Employment, unemployment rates |

## 7. Submodels

### 7.1 Firm Production Function

Leontief (fixed coefficients) for most sectors; CES for some service sectors:

```
Q = min(K/a_K, L/a_L, I_1/a_1, ..., I_n/a_n)
```

where `a_j` are sector-specific coefficients from ONS SUTs.

### 7.2 Firm Pricing

Adaptive markup rule:

```
price(t) = (1 + markup(t)) * unit_cost(t)
markup(t) = markup(t-1) * (1 + delta * demand_signal(t))
```

where `demand_signal = (sales(t) - expected_sales) / expected_sales`.

### 7.3 Labour Market Matching

- Firms post `(vacancies, wage)`.
- Unemployed households apply to `N_SEARCH` random vacancies in their region.
- Firms select from applicants (random if multiple).
- Unmatched households lower `reservation_wage` by `WAGE_ADJUSTMENT_RATE`.

### 7.4 Credit Supply

Banks approve loans if:

```
debt / equity < LEVERAGE_THRESHOLD(sector, bank_risk_appetite)
interest_coverage_ratio > MIN_COVERAGE
```

Approved loan rate:

```
rate = base_rate + sector_risk_premium + size_premium + bank_markup
```

### 7.5 Household Consumption

Budget:

```
disposable_income = wage + transfers - income_tax
consumption = disposable_income * propensity_to_consume
saving = disposable_income - consumption
```

Sector allocation: `consumption_basket` weights adjusted slowly toward observed relative prices (satisficing, not optimisation).

### 7.6 Firm Entry

New firms spawn in sector `s`, region `r` at rate:

```
entry_rate(s, r) = baseline_rate * (profitability(s, r) / avg_profitability)
```

where `baseline_rate` is calibrated to CH incorporation statistics.

New firms initialised with:
- Small size (bottom 10th percentile of sector)
- High debt ratio (startups are credit-constrained)
- Random strategy parameters

### 7.7 Firm Exit

Firms exit if `equity < 0` for `INSOLVENCY_THRESHOLD` consecutive months.

Exit triggers:
- Employees become unemployed.
- Loans default (bank losses).
- Supply-chain links break (customers/suppliers search for replacements).

### 7.8 Central Bank Policy Rule (Taylor Rule)

```
base_rate(t) = base_rate(t-1) * INERTIA
             + (1 - INERTIA) * [r_star + pi(t) + 0.5 * (pi(t) - pi_target) + 0.5 * output_gap(t)]
```

subject to zero lower bound.

### 7.9 Government Fiscal Policy

Tax revenue:

```
tax_revenue = corporation_tax + income_tax + VAT
```

Spending:

```
spending = government_consumption + unemployment_benefits + public_sector_wages
```

Deficit:

```
deficit = spending - tax_revenue
```

If `debt / GDP > target`, reduce `spending` or raise taxes (adjustment speed parameter).

## 8. Calibration and Validation

### 8.1 Calibration Strategy

Three-tier approach:

1. **Micro (direct)**: Firm-level parameters from Companies House + ONS data.
2. **Meso (network)**: Input–output coefficients from SUTs.
3. **Macro (indirect)**: Behavioural parameters (e.g., `MUTATION_RATE`, `WAGE_ADJUSTMENT_RATE`) estimated via Approximate Bayesian Computation (ABC) to match aggregate time-series.

### 8.2 Validation Targets

**Stylised facts** (model should reproduce without tuning):

- Firm size distribution: power law (Zipf exponent ~ 1.06)
- Firm growth rate distribution: Laplace (tent-shaped)
- GDP growth: autocorrelation, spectral density matching UK data
- Phillips curve: negative inflation–unemployment correlation
- Beveridge curve: negative vacancy–unemployment correlation
- Credit pro-cyclicality: credit growth leads GDP growth

**Historical matching** (ABC calibration target):

- UK GDP growth 2010–2025: mean, variance, autocorrelation
- UK inflation 2010–2025: mean, variance
- UK unemployment 2010–2025: mean, variance

**Out-of-sample tests**:

- Simulate COVID-19 shock (demand collapse + furlough scheme); compare to 2020 data.
- Simulate Brexit trade friction; compare to 2021–2023 sectoral output changes.

## 9. Implementation Notes

### 9.1 Performance Considerations

- **Rust core**: Millions of agents require efficient memory layout (ECS pattern via `krabmaga`), parallelised stepping (`rayon`), and zero-copy data transfer to Python (`arrow`).
- **Python layer**: Data wrangling (Polars), calibration (pyABC), visualisation (Plotly).

### 9.2 Reproducibility

- Random seed control for all stochastic processes.
- Version-controlled parameter files.
- Automated testing of stylised fact reproduction.

## 10. References

- Arthur, W. B. (2015). Complexity and the economy. *Science*, 349(6245), 284.
- Müller, B., Bohn, F., Dreßler, G., Groeneveld, J., Klassert, C., Martin, R., ... & Schwarz, N. (2013). Describing human decisions in agent-based models–ODD+ D, an extension of the ODD protocol. *Environmental Modelling & Software*, 48, 37-48.
