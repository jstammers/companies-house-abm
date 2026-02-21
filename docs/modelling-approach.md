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

Households supply labour and consume goods.  Each period:

1. **Receive income** — wages if employed, transfer income if not.
2. **Consume** — a consumption function combining a fraction of income (MPC) and a small draw on wealth.
3. **Save** — unspent income accumulates as deposits/wealth.

Key attributes: `income`, `wealth`, `mpc`, `employed`, `wage`.

### Bank

Banks accept deposits, extend credit and must satisfy regulatory constraints.  Each period:

1. **Set lending rate** — policy rate plus a markup, with a risk premium that rises with non-performing loans (NPLs).
2. **Evaluate loans** — check collateral coverage and debt-service coverage ratios.
3. **Record income/expense** — interest income on loans, interest expense on deposits, provisions for NPLs.
4. **Update capital** — profit added to equity.

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

## Within-Period Sequence

Each simulation period follows this sequence:

1. Government resets period flows.
2. Central bank sets the policy rate (Taylor rule).
3. Banks update lending rates from the new policy rate.
4. Credit market clears (firms borrow, defaults processed).
5. Firms step (plan, price, labour demand, produce, financials).
6. Labour market clears (separations, matching).
7. Households step (income, consumption, saving).
8. Government calculates spending.
9. Goods market clears (demand allocated, markup adaptation).
10. Taxes collected (corporate and income).
11. Government ends period (deficit, debt).
12. Central bank observes inflation and output gap.
13. Banks step (income calculation, capital update).

## Configuration

All parameters are stored in `config/model_parameters.yml` and loaded into frozen dataclass objects via `companies_house_abm.abm.config.load_config()`.  Parameters are organised by component:

| Section | Examples |
|---------|----------|
| `simulation` | `periods`, `seed`, `warm_up_periods` |
| `agents.firms` | `sample_size`, `sectors`, `entry_rate` |
| `Behaviour.firms` | `price_markup`, `inventory_target_ratio` |
| `agents.households` | `count`, `mpc_mean`, `income_mean` |
| `agents.banks` | `count`, `capital_requirement` |
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
