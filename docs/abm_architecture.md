# Agent-Based Model of the UK Economy: Architecture

## 1. Overview & Vision

This project builds a large-scale **Agent-Based Model (ABM)** of the UK economy, grounded in **complexity economics** principles. Rather than assuming equilibrium, the model treats the economy as an evolving complex adaptive system where macro-level phenomena (GDP, inflation, unemployment, business cycles) **emerge** from micro-level interactions among heterogeneous agents.

**Core data source:** Companies House bulk data provides the foundation for ~5 million real firm agents, each with sector (SIC code), size, age, geography, and ownership structure.

## 2. Architecture Decision: Rust Core + Python Bindings

### Rationale

| Concern | Choice | Why |
|---|---|---|
| **Simulation engine** | Rust (using `krabmaga`) | Millions of agents require high-throughput, parallel stepping. Rust's zero-cost abstractions and `krabmaga`'s ECS-inspired architecture are ideal. |
| **Data pipeline & analysis** | Python | Companies House data wrangling (pandas/polars), calibration (scipy), visualisation (matplotlib/plotly), econometric validation (statsmodels). |
| **Glue layer** | PyO3 + Maturin | Exposes the Rust simulation as a native Python module (`uk_econ_abm`) so researchers can configure, run, and analyse from Jupyter notebooks. |

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                   Python Layer                       │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Data     │  │ Calibration  │  │ Analysis &    │  │
│  │ Pipeline │  │ & Scenarios  │  │ Visualisation │  │
│  └────┬─────┘  └──────┬───────┘  └───────▲───────┘  │
│       │               │                  │           │
│       ▼               ▼                  │           │
│  ┌────────────────────────────────────────┐          │
│  │      PyO3 Binding: uk_econ_abm        │          │
│  └────────────────┬───────────────────────┘          │
└───────────────────┼──────────────────────────────────┘
                    │ FFI (zero-copy where possible)
┌───────────────────▼──────────────────────────────────┐
│                  Rust Core Engine                     │
│  ┌────────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ krabmaga   │ │ Agent    │ │ Market / Network    │ │
│  │ Scheduler  │ │ Systems  │ │ Topology (petgraph) │ │
│  └────────────┘ └──────────┘ └─────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## 3. Agent Taxonomy & Behaviours

### 3.1 Firms (seeded from Companies House)

Each firm is initialised from real Companies House records:

| CH Field | Agent Property | Use |
|---|---|---|
| `CompanyName` / `CompanyNumber` | `id` | Unique identifier |
| `SICCode.SicText_1..4` | `sector: SICCode` | Determines production function, input–output linkages |
| `CompanyCategory` | `legal_form` | Affects taxation, liability, investment behaviour |
| `IncorporationDate` | `age` | Firm survival/hazard rates |
| `RegAddress.PostCode` | `region: NUTSRegion` | Spatial interactions, regional policy effects |
| `Accounts.AccountCategory` | `size_proxy` | Micro/small/medium/large — scales production capacity |
| `Returns.NumGenPartners` / `NumLimPartners` | `ownership_structure` | Links to Investor agents |

**Firm behaviour (per tick = 1 month):**

```
1. PERCEIVE  → Observe: input prices, demand signals, interest rate, tax regime, competitor prices
2. DECIDE    → Adaptive pricing (markup rule with evolutionary learning)
               Production planning (inventory-target model)
               Labour demand (based on production plan & wage)
               Investment decision (accelerator + financial constraint)
               Credit demand (if internal funds insufficient)
3. ACT       → Purchase inputs on intermediate goods market
               Produce output (Leontief or CES with sector-specific coefficients)
               Post goods on consumer/intermediate market
               Hire/fire workers on labour market
               Service debt / pay dividends
4. ADAPT     → Update expectations (adaptive expectations / reinforcement learning)
               Entry/exit: firms with negative net worth for N periods exit;
               new firms enter stochastically (calibrated to CH incorporation rates)
```

**Complexity economics mechanisms embedded:**
- **Bounded rationality**: Firms use simple heuristics, not optimisation.
- **Increasing returns**: Firms that grow can access cheaper credit (size-dependent interest rate spread).
- **Path dependence**: A firm's history (debt, reputation, network position) shapes future options.
- **Evolutionary selection**: Profitable strategies spread; unprofitable firms exit.

### 3.2 Households

Households are **not** individually modelled from data (privacy constraints) but are generated as a synthetic population calibrated to ONS statistics:

| Property | Calibration Source |
|---|---|
| `income_decile` | ONS income distribution |
| `region` | ONS population by NUTS region |
| `propensity_to_consume` | Varies by income — from Family Expenditure Survey |
| `wealth` | ONS Wealth & Assets Survey |
| `employed_by: Option<FirmId>` | Matched in labour market |

**Behaviour:**
- Supply labour on the labour market (reservation wage adapts to employment history).
- Consume goods: budget allocation across sectors follows an evolving preference vector (not fixed utility maximisation — **satisficing** à la Simon).
- Save residual income; wealth earns returns via Investment Funds.
- Respond to government transfers (benefits, tax changes) with heterogeneous marginal propensities to consume — this is critical for fiscal multiplier analysis.

### 3.3 Banks (Commercial)

A small number (~5–10) of heterogeneous bank agents, calibrated to UK banking sector concentration:

| Behaviour | Mechanism |
|---|---|
| Credit supply | Screen firms (debt-to-equity ratio, sector risk); set loan rate = base rate + risk spread + markup |
| Balance sheet | Assets (loans), Liabilities (deposits, central bank funding), Equity |
| Capital adequacy | Basel-style constraint: lending limited by capital ratio |
| Interbank market | Banks with excess reserves lend to those in deficit |
| **Pro-cyclicality** | In booms, risk spreads compress (herding); in busts, credit rationing amplifies downturn — **endogenous money creation** |

### 3.4 Central Bank (Bank of England)

A single institutional agent implementing:

| Policy Tool | Implementation |
|---|---|
| **Base rate** | Taylor-rule variant: responds to inflation gap and output gap, but with inertia and an occasionally-binding zero lower bound |
| **Quantitative easing/tightening** | Purchases/sells government bonds, affecting long-term rates and bank reserves |
| **Macroprudential policy** | Counter-cyclical capital buffer: tightens bank capital requirements when credit growth exceeds threshold |
| **Forward guidance** | Signals future rate path; affects firm/household expectations with partial credibility |

### 3.5 Government (HM Treasury + Fiscal Apparatus)

| Component | Mechanism |
|---|---|
| **Taxation** | Corporation tax (on firm profits), income tax (on household wages, progressive brackets), VAT (on consumption) — all parameterised to current UK rates but adjustable for scenario analysis |
| **Spending** | Government consumption (exogenous demand to firms), public sector wages, transfers (unemployment benefits, universal credit) |
| **Fiscal rules** | Debt-to-GDP targeting with adjustment speed parameter |
| **Industrial policy** | Sector-specific subsidies, R&D tax credits, regional levelling-up funds — modelled as parameter shocks to specific firm subsets |

### 3.6 Private Investors / Investment Funds

Bridge between household savings and firm equity/debt:

- Aggregate household savings into fund pools.
- Allocate across firms (equity stakes, corporate bonds) using simple portfolio heuristics (momentum + mean-reversion blend — **not** CAPM).
- Returns flow back to households, closing the financial circuit.
- Investor **herding** and **sentiment** modelled via opinion dynamics on a social network.

## 4. Interaction Topology & Markets

### 4.1 Markets as Matching Mechanisms

Markets are **not** Walrasian auctioneers. They are decentralised matching processes — a key complexity economics departure:

| Market | Mechanism | Library |
|---|---|---|
| **Goods (consumer)** | Firms post price+quantity; households visit a subset (search friction); purchase if price ≤ reservation price. Rationing if demand > supply. | Custom order-book in Rust |
| **Goods (intermediate)** | Input–output network; firms order from suppliers with switching costs | `petgraph` for supply network |
| **Labour** | Firms post vacancies + wage; unemployed households apply to a subset; matching with skill proxy. Phillips curve **emerges** rather than being imposed. | Matching engine in Rust |
| **Credit** | Firms apply to banks; banks screen and ration. Quantity rationing, not just price clearing. | Custom |
| **Financial assets** | Investors bid for firm equity/bonds; prices adjust via a continuous double auction or zero-intelligence trader model | Order book in Rust |

### 4.2 Input–Output Network

The inter-firm production network is the backbone of the model:

1. **Initialisation**: Use the ONS Supply and Use Tables (SUTs) to define sector-level input–output coefficients. Each firm's sector (from SIC code) determines what fraction of its inputs come from which other sectors.
2. **Firm-to-firm links**: Within each sector pair, specific supplier–buyer links are formed using a **preferential attachment** process (firms with more connections attract more), creating a realistic scale-free network.
3. **Shock propagation**: A shock to one firm/sector propagates through the network — modelling supply chain disruptions, cascading failures, and sectoral contagion. This is directly inspired by **Acemoglu et al. (2012)** on network origins of aggregate fluctuations.

### 4.3 Spatial Structure

Firms and households are located in NUTS-2 regions. Transport/trade costs between regions dampen but don't eliminate inter-regional trade. This allows analysis of:
- Regional inequality dynamics
- "Levelling up" policy effectiveness
- Spatial concentration and agglomeration effects

## 5. Complexity Economics Processes

The model explicitly incorporates these complexity economics mechanisms:

| Mechanism | How It Appears | Key Reference |
|---|---|---|
| **Emergence** | Macro aggregates (GDP, inflation, unemployment) are not imposed but emerge from agent interactions | Arthur (2015) |
| **Non-equilibrium dynamics** | The economy is perpetually adapting; no convergence to steady state is assumed | Arthur (2015) |
| **Radical uncertainty / bounded rationality** | Agents use heuristics, not rational expectations; expectations are adaptive or formed via simple rules | Simon (1955), Gigerenzer (2008) |
| **Evolutionary dynamics** | Firm strategies mutate and are selected by market competition; entry/exit creates variation-selection-retention cycle | Nelson & Winter (1982) |
| **Network effects & contagion** | Supply-chain network topology determines shock amplification; financial contagion through interbank/credit networks | Acemoglu et al. (2012), Battiston et al. (2012) |
| **Increasing returns & lock-in** | Larger firms get cheaper credit, more network connections → rich-get-richer dynamics; path-dependent industry structure | Arthur (1994) |
| **Endogenous money & credit cycles** | Bank lending creates deposits; credit expansion/contraction drives business cycles endogenously | Minsky (1986), Keen (2011) |
| **Self-organised criticality** | Firm size/bankruptcy distributions may exhibit power-law tails; the system self-organises near critical points | Bak et al. (1993) |
| **Heterogeneity matters** | Distributional effects of policy are first-class outputs, not afterthoughts | Dosi et al. (2010) |

## 6. Simulation Flow (Per Tick = 1 Month)

```
┌─────────────────────────────────────────────────────────────┐
│                     MONTHLY TICK                             │
│                                                              │
│  1. GOVERNMENT sets tax rates, spending, transfers           │
│  2. CENTRAL BANK sets base rate, macroprudential buffer      │
│  3. BANKS update lending rates, assess capital adequacy      │
│  4. FIRMS:                                                   │
│     a. Update expectations                                   │
│     b. Plan production, set prices                           │
│     c. Post vacancies, set wages                             │
│     d. Apply for credit if needed                            │
│  5. CREDIT MARKET clears (banks screen & allocate loans)     │
│  6. LABOUR MARKET clears (matching with frictions)           │
│  7. FIRMS produce (using inputs from supply network)         │
│  8. INTERMEDIATE GOODS MARKET clears (firm-to-firm trade)    │
│  9. HOUSEHOLDS receive wages + transfers, decide consumption │
│ 10. CONSUMER GOODS MARKET clears (with search frictions)     │
│ 11. FIRMS compute profits, pay taxes, service debt           │
│ 12. INVESTORS reallocate portfolios                          │
│ 13. FINANCIAL MARKET clears                                  │
│ 14. FIRM ENTRY/EXIT (births calibrated to CH data, deaths    │
│     from insolvency)                                         │
│ 15. COLLECT MACRO STATISTICS (GDP, CPI, unemployment,        │
│     Gini, credit-to-GDP, network metrics)                    │
└─────────────────────────────────────────────────────────────┘
```

## 7. References

- Acemoglu, D., Carvalho, V. M., Ozdaglar, A., & Tahbaz-Salehi, A. (2012). The network origins of aggregate fluctuations. *Econometrica*, 80(5), 1977-2016.
- Arthur, W. B. (1994). *Increasing returns and path dependence in the economy*. University of Michigan Press.
- Arthur, W. B. (2015). Complexity and the economy. *Science*, 349(6245), 284-284.
- Bak, P., Chen, K., Scheinkman, J., & Woodford, M. (1993). Aggregate fluctuations from independent sectoral shocks: self-organized criticality in a model of production and inventory dynamics. *Ricerche economiche*, 47(1), 3-30.
- Battiston, S., Delli Gatti, D., Gallegati, M., Greenwald, B., & Stiglitz, J. E. (2012). Liaisons dangereuses: Increasing connectivity, risk sharing, and systemic risk. *Journal of economic dynamics and control*, 36(8), 1121-1141.
- Dosi, G., Fagiolo, G., & Roventini, A. (2010). Schumpeter meeting Keynes: A policy-friendly model of endogenous growth and business cycles. *Journal of Economic Dynamics and Control*, 34(9), 1748-1767.
- Gigerenzer, G. (2008). *Rationality for mortals: How people cope with uncertainty*. Oxford University Press.
- Keen, S. (2011). *Debunking economics: The naked emperor dethroned?* Zed Books.
- Minsky, H. P. (1986). *Stabilizing an unstable economy*. Yale University Press.
- Nelson, R. R., & Winter, S. G. (1982). *An evolutionary theory of economic change*. Harvard University Press.
- Simon, H. A. (1955). A behavioral model of rational choice. *The quarterly journal of economics*, 69(1), 99-118.
