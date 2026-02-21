# Agent-Based Model Design: UK Economy Simulation

## Executive Summary

This document outlines the design for an agent-based model (ABM) of the UK economy that leverages Companies House financial data to simulate firm-level Behaviour and macroeconomic dynamics. The model incorporates insights from complexity economics to capture emergent phenomena arising from heterogeneous agent interactions.

## 1. Model Overview

### 1.1 Purpose

The ABM aims to:
- Model individual UK firms as heterogeneous agents using real financial data
- Simulate production, consumption, and financial interactions between agents
- Incorporate macroeconomic actors (central bank, government, households, investors)
- Study emergent macroeconomic outcomes from micro-level interactions
- Test policy interventions and understand systemic risks

### 1.2 Theoretical Foundation

The model draws from:
- **Stock-Flow Consistent (SFC) modeling**: Ensures accounting consistency across sectors
- **Post-Keynesian economics**: Demand-driven dynamics with financial constraints
- **Complexity economics**: Network effects, path dependence, far-from-equilibrium dynamics
- **Input-Output analysis**: Sectoral interdependencies and supply chains
- **Behavioural economics**: Bounded rationality and adaptive expectations

## 2. Agent Types

### 2.1 Firm Agents

**Core Attributes** (from Companies House data):
- `company_id`: Unique identifier
- `sector`: Industry classification (derived from SIC codes if available)
- `size_class`: Micro/Small/Medium/Large (based on turnover/employees)
- Balance sheet: `tangible_fixed_assets`, `current_assets`, `cash_bank_in_hand`, `debtors`, `creditors_*`
- P&L: `turnover`, `cost_sales`, `staff_costs`, `operating_profit_loss`
- Employment: `average_number_employees_during_period`

**Derived State Variables**:
- `production_capacity`: Function of tangible fixed assets
- `inventory`: Stock of finished goods
- `wage_rate`: Staff costs / employees
- `profit_margin`: Operating profit / turnover
- `liquidity_ratio`: Cash / current liabilities
- `debt_ratio`: Total liabilities / total assets
- `bankruptcy_risk`: Probabilistic based on financial health

**Behaviours**:
1. **Production Decision**: Based on demand expectations, inventory, and capacity
2. **Pricing Decision**: Mark-up pricing based on costs and market conditions
3. **Investment Decision**: Capacity expansion based on profitability and finance availability
4. **Employment Decision**: Hiring/firing based on production needs
5. **Financial Management**: Seeking credit, managing cash flow
6. **Exit/Entry**: Bankruptcy based on insolvency, new firm entry by sector

**Inter-firm Interactions**:
- Supply chain relationships (input-output linkages)
- Credit networks (supplier credit, trade credit)
- Competition in product markets
- Labour market competition

### 2.2 Household Agents

**Attributes**:
- `income`: Wages from employment + transfer payments
- `wealth`: Accumulated savings and assets
- `consumption_propensity`: Marginal propensity to consume
- `employed`: Boolean employment status
- `employer_id`: Link to employing firm (if employed)

**Behaviours**:
1. **Consumption**: Based on income, wealth, and expectations
2. **Labour Supply**: Job search when unemployed
3. **Savings**: Unspent income accumulates as deposits

**Distribution**:
- Heterogeneous income levels calibrated to UK income distribution
- Can be aggregated into representative household classes (quintiles)

### 2.3 Bank Agents

**Attributes**:
- `capital`: Bank equity
- `reserves`: Central bank reserves
- `loans`: Outstanding loans to firms and households
- `deposits`: Household and firm deposits
- `risk_appetite`: Lending propensity

**Behaviours**:
1. **Lending Decision**: Credit evaluation based on firm financial ratios
2. **Interest Rate Setting**: Risk-based pricing
3. **Capital Adequacy**: Maintain regulatory capital ratios
4. **Interbank Lending**: Liquidity management

**Constraints**:
- Basel III capital requirements
- Reserve requirements

### 2.4 Central Bank Agent

**Attributes**:
- `policy_rate`: Base interest rate
- `inflation_target`: Target CPI inflation (2% for UK)
- `reserves_supplied`: Total reserves to banking system

**Behaviours**:
1. **Monetary Policy**: Taylor rule or variant for interest rate setting
2. **Reserve Operations**: Accommodate reserve demand
3. **Lender of Last Resort**: Emergency liquidity provision
4. **Macroprudential Policy**: Counter-cyclical capital buffers

### 2.5 Government Agent

**Attributes**:
- `tax_revenue`: Income from various taxes
- `expenditure`: Government spending on goods/services and transfers
- `deficit`: Revenue - expenditure
- `debt`: Accumulated deficits

**Behaviours**:
1. **Taxation**: VAT, corporation tax, income tax
2. **Spending**: Government consumption, public sector wages, transfers
3. **Automatic Stabilizers**: Unemployment benefits, progressive taxation
4. **Discretionary Policy**: Fiscal stimulus/austerity

### 2.6 Investor Agents (Optional)

**Attributes**:
- `portfolio`: Holdings of firm equity and bonds
- `risk_preference`: Risk aversion parameter

**Behaviours**:
1. **Asset Allocation**: Based on expected returns and risk
2. **Firm Valuation**: Impact on firm cost of capital
3. **Speculation**: Can introduce volatility

## 3. Markets and Mechanisms

### 3.1 Goods Market

- **Matching**: Firms post prices; households and government purchase
- **Market Clearing**: Inventory accumulation/depletion, not instant clearing
- **Price Discovery**: Firms adjust prices based on inventory and demand signals

### 3.2 Labour Market

- **Matching**: Job search and hiring processes with frictions
- **Wage Formation**: Bargaining or efficiency wages, sticky nominal wages
- **Unemployment**: Can be structural, frictional, or cyclical

### 3.3 Credit Market

- **Firm Borrowing**: Banks evaluate creditworthiness, set interest rates
- **Rationing**: Credit can be rationed during downturns
- **Default**: Non-performing loans affect bank capital

### 3.4 Interbank Market

- **Liquidity Redistribution**: Banks with surplus lend to those with deficit
- **Contagion**: Bank failures can spread through interbank network

## 4. Model Dynamics

### 4.1 Time Steps

The model operates in discrete time periods (e.g., quarters or months).

**Within-period sequence** (illustrative):
1. **Policy Setting**: Central bank sets interest rate; government announces budget
2. **Credit Market**: Firms apply for credit; banks make lending decisions
3. **Labour Market**: Firms post vacancies; households search; matching occurs
4. **Production**: Firms produce based on capacity, employment, and input availability
5. **Goods Market**: Households and government consume; firms sell goods
6. **Accounting**: Firms pay wages, taxes, interest; calculate profits
7. **Investment**: Firms invest in capacity expansion
8. **Entry/Exit**: Bankruptcies resolved; new firms enter
9. **Financial Statements**: Update balance sheets and income statements

### 4.2 Stock-Flow Consistency

All flows (income, expenditure, lending) must result in consistent stock changes (wealth, debt, inventory). This ensures:
- Sectoral balance identity: `(S - I) + (T - G) + (M - X) = 0`
- No black holes: money/value doesn't disappear
- Proper accounting: assets = liabilities + equity

### 4.3 Aggregation and Emergence

- **Micro → Macro**: Individual firm production → GDP
- **Emergent Phenomena**: Business cycles, crises, structural change
- **Feedback Loops**: Accelerator-multiplier, debt-deflation spirals

## 5. Calibration and Initialization

### 5.1 Firm Initialization

**Data Source**: Companies House XBRL data

**Process**:
1. Load most recent financial statements for all UK firms
2. Clean and validate data (handle missing values, outliers)
3. Classify firms by sector (use SIC codes if available)
4. Initialize agent attributes from balance sheet and P&L data
5. Create a representative sample (e.g., stratified by sector and size)

**Representative Sampling**:
- For computational efficiency, use ~10,000-100,000 representative firms
- Stratified by sector, size, region
- Weight agents to represent total UK economy

### 5.2 Parameter Calibration

**Macroeconomic Parameters**:
- Inflation target: 2%
- Policy rate: Current BoE rate
- Government budget: Match UK fiscal position
- Unemployment rate: Match ONS statistics

**Behavioural Parameters** (estimated or calibrated):
- Consumption propensity: From UK consumption data
- Mark-up rates: Sector-specific from industry data
- Investment sensitivity: Calibrate to match investment/GDP ratio
- Wage elasticity: From Labour economics literature

**Network Structure**:
- Supply chain networks: From ONS input-output tables
- Bank-firm lending: Match UK credit statistics

### 5.3 Validation Targets

The model should reproduce:
- GDP growth volatility and persistence
- Unemployment dynamics
- Inflation Behaviour
- Firm size distribution (power law)
- Firm growth rate distribution (Laplace/tent-shaped)
- Financial ratios distributions

## 6. Implementation Architecture

### 6.1 Technology Stack

#### Option A: Pure Python Stack

**Framework**: Mesa (Python ABM framework)
- Mature, well-documented
- Built-in visualization (Mesa server)
- Modular architecture (schedulers, space, data collection)

**Data Processing**: Polars (already in use)
- Fast data loading and transformation
- Integration with existing ingestion pipeline

**Numerical Computing**: NumPy/SciPy
- Matrix operations for network analysis
- Optimization routines

**Visualization**:
- Matplotlib/Plotly for time series
- NetworkX for network visualization
- Mesa's built-in dashboard

**Advantages**:
- Seamless integration with existing codebase
- Rich ecosystem, easier debugging
- Faster development cycle

**Disadvantages**:
- Performance limitations for very large models
- GIL constraints for parallelization

#### Option B: Rust Core with Python Bindings

**Framework**: Kraken/Krabmaga (Rust ABM framework)
- High performance, parallel execution
- Memory efficiency

**Bindings**: PyO3 + Maturin
- Expose Rust ABM to Python
- Keep data pipeline in Python/Polars
- Use Python for analysis and visualization

**Architecture**:
```
Python Layer:
  - Data ingestion (existing pipeline)
  - Calibration and initialization
  - Result analysis and visualization
  - Parameter exploration

Rust Layer:
  - Agent state and Behaviour
  - Scheduler and execution
  - Market mechanisms
  - Network traversal
```

**Advantages**:
- 10-100x performance improvement
- Handle millions of agents
- Efficient parallel execution

**Disadvantages**:
- Steeper learning curve
- More complex build process
- Split language ecosystem

#### Recommended Approach: Hybrid

1. **Phase 1**: Prototype in Mesa (Python)
   - Rapid development and testing
   - Validate model logic and Behaviours
   - Small-scale calibration (~10k firms)

2. **Phase 2**: Port to Rust/PyO3 if performance is insufficient
   - Keep data layer in Python
   - Implement core simulation in Rust
   - Large-scale runs (100k+ firms)

### 6.2 Module Structure

```
src/companies_house_abm/
├── abm/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── firm.py          # Firm agent class
│   │   ├── household.py     # Household agent class
│   │   ├── bank.py          # Bank agent class
│   │   ├── central_bank.py  # Central bank agent
│   │   ├── government.py    # Government agent
│   │   └── base.py          # Base agent class
│   ├── markets/
│   │   ├── __init__.py
│   │   ├── goods.py         # Goods market mechanism
│   │   ├── Labour.py         # Labour market matching
│   │   ├── credit.py        # Credit market
│   │   └── interbank.py     # Interbank market
│   ├── model.py             # Main ABM model class
│   ├── scheduler.py         # Custom scheduling logic
│   ├── calibration.py       # Parameter calibration utilities
│   ├── initialize.py        # Agent initialization from data
│   └── metrics.py           # Model output and analysis
├── data/
│   ├── __init__.py
│   ├── loader.py            # Load and process Companies House data
│   ├── networks.py          # Build supply chain networks
│   └── uk_data.py           # UK macroeconomic data
├── config/
│   ├── __init__.py
│   ├── parameters.py        # Model parameters
│   └── scenarios.yaml       # Policy scenarios
└── utils/
    ├── __init__.py
    ├── accounting.py        # SFC accounting checks
    └── statistics.py        # Distributional analysis
```

### 6.3 Configuration System

Use a simple YAML configuration file:

```yaml
# config/model_parameters.yml
simulation:
  periods: 400  # 100 years quarterly
  time_step: "quarter"
  seed: 42

agents:
  firms:
    sample_size: 50000
    sectors: ["manufacturing", "services", "construction", ...]
    entry_rate: 0.02  # per period
    exit_threshold: -0.5  # equity/assets ratio

  households:
    count: 10000
    income_distribution: "lognormal"
    mpc_mean: 0.8
    mpc_std: 0.1

  banks:
    count: 10
    capital_requirement: 0.10
    risk_weight: 1.0

markets:
  goods:
    price_adjustment_speed: 0.1
    inventory_target: 0.2  # of expected sales

  Labour:
    wage_stickiness: 0.8
    matching_efficiency: 0.3

  credit:
    base_rate: 0.01
    risk_spread: 0.05
    rationing_threshold: 0.5

policy:
  central_bank:
    taylor_rule:
      inflation_coefficient: 1.5
      output_gap_coefficient: 0.5
      smoothing: 0.8

  government:
    spending_gdp_ratio: 0.40
    tax_rate_corporate: 0.19
    tax_rate_income: 0.20
    deficit_target: 0.03
```

## 7. Key Features and Extensions

### 7.1 Network Effects

**Supply Chain Network**:
- Derived from ONS input-output tables
- Firm-level supplier-customer relationships
- Shock propagation through network

**Credit Network**:
- Bank-firm lending relationships
- Interbank exposure matrix
- Systemic risk analysis

**Methods**:
- NetworkX for Python implementation
- Graph analysis (centrality, clustering)
- Shock simulation and contagion studies

### 7.2 Sectoral Heterogeneity

- Different production functions by sector
- Sector-specific demand elasticities
- Input-output linkages between sectors

### 7.3 Adaptive Expectations

Agents form expectations based on:
- Adaptive expectations: Weighted average of past outcomes
- Trend extrapolation: Identify patterns
- Heterogeneous expectations: Optimists vs pessimists

### 7.4 Learning and Evolution

- Firms learn from experience (e.g., adjust mark-ups)
- Successful strategies spread (imitation)
- Structural change through entry/exit

### 7.5 Financial Fragility

**Minsky Dynamics**:
- Hedge finance: Can pay interest and principal from cash flow
- Speculative finance: Can pay interest but must roll over principal
- Ponzi finance: Must borrow to pay interest

**Tracking**:
- Classify firms by Minsky category
- Monitor system-wide fragility indicators
- Endogenous credit cycles

### 7.6 Policy Experiments

**Monetary Policy**:
- Quantitative easing
- Negative interest rates
- Forward guidance

**Fiscal Policy**:
- Fiscal multipliers under different conditions
- Government investment programs
- Tax reform scenarios

**Macroprudential**:
- Counter-cyclical capital buffers
- Loan-to-value restrictions
- Stress testing

**Structural Policies**:
- Industrial policy (sector-specific support)
- Labour market reforms
- Competition policy

## 8. Output and Analysis

### 8.1 Time Series Outputs

**Macroeconomic Aggregates**:
- GDP (and components: C, I, G, NX)
- Inflation (CPI, PPI)
- Unemployment rate
- Wage growth
- Interest rates
- Government deficit/debt
- Bank lending

**Distributional Measures**:
- Firm size distribution (Pareto/log-normal)
- Profit rate distribution
- Household income/wealth inequality (Gini)
- Sector shares of GDP

**Financial Stability**:
- Non-performing loan ratio
- Bank capital ratios
- Corporate debt/equity ratios
- Bankruptcies per period

### 8.2 Stylized Facts Validation

The model should replicate:
1. **Fat-tailed firm size distribution**: Power law with exponent ~1
2. **Laplace firm growth distribution**: Tent-shaped, fat tails
3. **Persistent unemployment**: Even in long-run
4. **Credit cycles**: Endogenous boom-bust patterns
5. **Pro-cyclical leverage**: Debt rises in booms
6. **Autocorrelated GDP growth**: Persistence
7. **Negative skewness of GDP growth**: Rare deep recessions

### 8.3 Visualization

- Time series dashboards (Plotly/Dash)
- Network visualizations (supply chains, credit networks)
- Spatial plots (if regional dimension added)
- Distribution evolution (animated histograms)
- Phase diagrams (e.g., inflation vs unemployment)

### 8.4 Statistical Analysis

- Monte Carlo runs (vary initial conditions and shocks)
- Sensitivity analysis (parameter space exploration)
- Scenario comparison (policy counterfactuals)
- Decomposition analysis (variance attribution)

## 9. Computational Considerations

### 9.1 Performance Optimization

**Python Optimizations**:
- Vectorize operations with NumPy/Polars
- Use Numba for JIT compilation of hot loops
- Profile with cProfile and optimize bottlenecks
- Parallel execution with multiprocessing for Monte Carlo

**Rust Optimizations**:
- Leverage ownership system for zero-copy operations
- Use Rayon for data parallelism
- SIMD operations for mathematical calculations
- Efficient memory layout (struct-of-arrays)

### 9.2 Scalability

**Sampling Strategies**:
- Representative agent sampling (not all UK firms)
- Stratified sampling by sector/size
- Re-weight results to population level

**Approximate Methods**:
- Mean-field approximations for large homogeneous groups
- Simplified network structures (random graphs vs full empirical)

**Distributed Computing** (future):
- Partition agents across nodes
- MPI for parallel execution
- GPU acceleration for matrix operations

### 9.3 Reproducibility

- Seed control for random number generation
- Version control for code and data
- Parameter logging for each run
- Containerization (Docker) for environment consistency

## 10. Development Roadmap

### Phase 1: Foundation (Months 1-3)

- [ ] Set up Mesa ABM framework integration
- [ ] Implement basic firm agent with Companies House data loading
- [ ] Create simple goods market mechanism
- [ ] Validate firm initialization from real data
- [ ] Basic time series output and plotting

### Phase 2: Core Model (Months 4-6)

- [ ] Implement all agent types (firms, households, banks, CB, government)
- [ ] Implement all markets (goods, Labour, credit)
- [ ] Stock-flow consistency validation
- [ ] Calibrate to UK macroeconomic data
- [ ] Replicate basic stylized facts

### Phase 3: Networks and Heterogeneity (Months 7-9)

- [ ] Build supply chain network from IO tables
- [ ] Implement credit network
- [ ] Add sectoral differentiation
- [ ] Implement adaptive expectations
- [ ] Financial fragility indicators

### Phase 4: Validation and Analysis (Months 10-12)

- [ ] Extensive validation against UK data
- [ ] Sensitivity analysis
- [ ] Policy experiments
- [ ] Documentation and examples
- [ ] Performance optimization

### Phase 5: Advanced Features (Optional)

- [ ] Port to Rust/Krabmaga for performance
- [ ] Regional dimension (UK regions)
- [ ] International trade
- [ ] Detailed tax system
- [ ] Housing market
- [ ] Innovation and R&D

## 11. References and Resources

### Complexity Economics and ABM

1. **Farmer, J.D. & Foley, D.** (2009). "The economy needs agent-based modelling." *Nature*
2. **Delli Gatti, D. et al.** (2011). "Macroeconomics from the Bottom-up." Springer
3. **Dawid, H. & Delli Gatti, D.** (2018). "Agent-Based Macroeconomics." *Handbook of Computational Economics*
4. **Poledna, S. et al.** (2018). "The multi-layer network nature of systemic risk." *Nature Communications*

### Stock-Flow Consistent Modeling

5. **Godley, W. & Lavoie, M.** (2007). "Monetary Economics: An Integrated Approach." Palgrave
6. **Caverzasi, E. & Godin, A.** (2015). "Post-Keynesian stock-flow-consistent modelling." *Journal of Economic Surveys*

### Firm Dynamics

7. **Axtell, R.L.** (2001). "Zipf distribution of US firm sizes." *Science*
8. **Stanley, M.H.R. et al.** (1996). "Scaling behaviour in the growth of companies." *Nature*
9. **Bottazzi, G. & Secchi, A.** (2006). "Explaining the distribution of firm growth rates." *RAND Journal of Economics*

### Financial Networks and Crises

10. **Battiston, S. et al.** (2012). "Default cascades." *Journal of Financial Stability*
11. **Haldane, A.G. & May, R.M.** (2011). "Systemic risk in banking ecosystems." *Nature*

### ABM Frameworks

12. **Mesa Documentation**: https://mesa.readthedocs.io/
13. **Krabmaga (Rust ABM)**: https://github.com/krABMaga/krABMaga
14. **PyO3 Documentation**: https://pyo3.rs/

### UK Data Sources

15. **Office for National Statistics (ONS)**: https://www.ons.gov.uk/
16. **Bank of England Statistics**: https://www.bankofengland.co.uk/statistics
17. **Companies House**: https://www.gov.uk/government/organisations/companies-house

## 12. Risk and Limitations

### Model Limitations

1. **Computational Constraints**: Cannot simulate all 4+ million UK firms
2. **Data Limitations**: Missing firm-level data (networks, detailed transactions)
3. **Behavioural Assumptions**: Simplified decision rules vs real complexity
4. **Validation Challenges**: Hard to validate micro-level Behaviour
5. **Lucas Critique**: Behavioural parameters may change under new policies

### Mitigation Strategies

1. **Representative Sampling**: Use statistical methods to represent full population
2. **Synthetic Networks**: Generate plausible networks from available data
3. **Empirical Grounding**: Base Behaviours on empirical studies where possible
4. **Multiple Validation Levels**: Validate at micro, meso, and macro levels
5. **Robustness Checks**: Test sensitivity to Behavioural assumptions

### Ethical Considerations

1. **Model Uncertainty**: Clearly communicate limitations and uncertainty
2. **Policy Advice**: Avoid overconfident policy prescriptions
3. **Transparency**: Open-source code and documentation
4. **Data Privacy**: Ensure compliance with data protection regulations

## 13. Conclusion

This agent-based model represents a ambitious but feasible approach to understanding the UK economy as a complex adaptive system. By grounding firm agents in real Companies House data and incorporating insights from complexity economics, the model can provide novel insights into:

- How micro-level heterogeneity aggregates to macro outcomes
- The role of networks in shock propagation
- The effectiveness of policy interventions
- Systemic risk and financial stability

The phased development approach allows for incremental progress, with early validation and course correction. Starting with a Python/Mesa prototype enables rapid development, with the option to scale to Rust for performance if needed.

The model will be a valuable tool for researchers, policymakers, and analysts seeking to understand the emergent properties of the economic system and test interventions in a rich, Behaviourally grounded simulation environment.
