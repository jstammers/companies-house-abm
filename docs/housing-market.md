# UK Housing Market ABM

## Overview

The housing market module simulates the UK residential property market using
**bilateral matching with aspiration-level pricing**, following the approach
described by Farmer (2025) and adapted for the UK by Baptista et al. (2016)
and Carro et al. (2022).

Unlike the goods or labour markets, the housing market does **not** clear to
equilibrium. Buyers and sellers are matched bilaterally, prices adjust
sluggishly through aspiration-level adaptation, and persistent imbalances
between supply and demand are the norm — just like real housing markets.

## Architecture

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Property** | `abm/assets/property.py` | Passive asset: value, type, region, listing state |
| **Mortgage** | `abm/assets/mortgage.py` | Loan contract: principal, rate, LTV, arrears tracking |
| **HousingMarket** | `abm/markets/housing.py` | Bilateral matching, aspiration-level pricing |
| **Household** (extended) | `abm/agents/household.py` | Tenure, buy/rent decision, housing payment |
| **Bank** (extended) | `abm/agents/bank.py` | Mortgage evaluation, origination, foreclosure |
| **Config** | `abm/config.py` | `PropertyConfig`, `HousingMarketConfig`, `MortgageConfig` |
| **Data sources** | `data_sources/land_registry.py`, `data_sources/ons_housing.py` | UK house price and tenure data |

### Data Flow

```
Household.decide_buy_or_rent()  →  wants_to_buy = True/False
Owner sell decision (2%/period)  →  Property.list_for_sale()
                                         ↓
                            HousingMarket.clear()
                                         ↓
                    ┌────────────────────────────────────────┐
                    │  1. Update asking prices (aspiration)  │
                    │  2. Collect buyers (wants_to_buy)      │
                    │  3. Collect listings (on_market)       │
                    │  4. Bilateral matching                 │
                    │  5. Update statistics                  │
                    └────────────────────────────────────────┘
                                         ↓
              Bank.evaluate_mortgage() → Bank.originate_mortgage()
                                         ↓
                              Property.sell() → ownership transfer
```

## Key Mechanisms

### Aspiration-Level Pricing (Farmer 2025)

Sellers set asking prices above market value and gradually reduce them:

1. **Initial listing**: `asking_price = market_value × (1 + initial_markup)`
   (default markup: 5%)
2. **Monthly reduction**: `asking_price *= (1 - price_reduction_rate)`
   (default reduction: 10%)
3. **Delisting**: After `max_months_listed` periods without a sale, the
   property is removed from the market (default: 6 months)

This creates the characteristic downward price adjustment observed in real
markets and allows persistent supply-demand imbalances.

### Buy/Rent Decision

Households compare the expected monthly cost of owning versus renting:

- **Cost of owning** = mortgage payment + maintenance − expected appreciation
- **Cost of renting** = average price × rental yield / 12

Price expectations combine backward-looking trend extrapolation (65% weight)
with a forward-looking fundamental growth assumption (2% annual, 35% weight),
following the behavioural expectation formation described by Farmer (2025).

A renter decides to buy if:

1. Owning is cheaper than renting (expected)
2. They can afford the deposit (≥ 10% of average price)

### FPC Macroprudential Toolkit

Bank mortgage evaluation applies the Financial Policy Committee's
macroprudential tools:

| Check | Default | Description |
|-------|---------|-------------|
| **LTV cap** | 90% | Loan-to-value ratio must not exceed this |
| **DTI cap** | 4.5× | Debt-to-income ratio must not exceed this |
| **Stress test** | +3% buffer | Borrower must afford payments at rate + buffer |
| **Affordability** | <40% income | Stressed monthly payment < 40% of gross income |

These parameters are fully configurable, enabling policy experiments
(e.g. varying the LTV cap to study bubble sensitivity per Baptista et al.).

### Bilateral Matching

Each period, the market matches buyers to properties:

1. Shuffle buyers randomly (fairness)
2. Each buyer computes their budget: `wealth + max_mortgage` (where
   `max_mortgage = annual_income × 4.5`)
3. Buyer visits up to `search_intensity` (default: 10) affordable properties
4. Buyer selects the best value: lowest `asking_price / quality` ratio
5. Bank evaluates the mortgage application
6. If approved: ownership transfers, mortgage created, seller receives proceeds

## Running a Simulation

### Basic Usage

```python
from companies_house_abm.abm.model import Simulation

sim = Simulation.from_config()
result = sim.run(periods=60)  # 60 months = 5 years

# Access housing time series
for record in result.records:
    print(
        f"Period {record.period}: "
        f"Price=£{record.average_house_price:,.0f} "
        f"Txns={record.housing_transactions} "
        f"Ownership={record.homeownership_rate:.1%}"
    )
```

### Custom Configuration

```python
from companies_house_abm.abm.config import (
    HousingMarketConfig,
    ModelConfig,
    MortgageConfig,
    PropertyConfig,
    SimulationConfig,
)
from companies_house_abm.abm.model import Simulation

config = ModelConfig(
    simulation=SimulationConfig(periods=120, seed=42),
    properties=PropertyConfig(count=5000, average_price=300_000),
    housing_market=HousingMarketConfig(
        search_intensity=15,
        price_reduction_rate=0.08,
    ),
    mortgage=MortgageConfig(
        max_ltv=0.80,        # Tighter LTV cap
        max_dti=4.0,         # Tighter DTI limit
        stress_test_buffer=0.04,
    ),
)

sim = Simulation(config)
sim.initialize_agents()
result = sim.run()
```

### Policy Experiments

Compare the effect of different LTV caps:

```python
from companies_house_abm.abm.config import ModelConfig, MortgageConfig
from companies_house_abm.abm.model import Simulation

for max_ltv in [0.75, 0.85, 0.95]:
    config = ModelConfig(mortgage=MortgageConfig(max_ltv=max_ltv))
    sim = Simulation(config)
    sim.initialize_agents()
    result = sim.run(periods=60)
    final = result.records[-1]
    print(
        f"LTV={max_ltv:.0%}: "
        f"Price=£{final.average_house_price:,.0f} "
        f"Ownership={final.homeownership_rate:.1%} "
        f"Txns={sum(r.housing_transactions for r in result.records)}"
    )
```

### Web Application

The economy simulator webapp includes housing parameters:

```bash
uv run companies-house-abm serve
# Open http://localhost:8000
```

Housing-specific parameters in the UI:

- **Max LTV** — Maximum loan-to-value ratio (0.50–1.00)
- **Max DTI** — Maximum debt-to-income multiple (2.0–7.0)
- **Search intensity** — Properties visited per buyer per period (1–50)

### Calibration from Live Data

```python
from companies_house_abm.data_sources import (
    calibrate_housing,
    fetch_regional_prices,
    fetch_tenure_distribution,
    fetch_affordability_ratio,
)

# Fetch current UK housing data
prices = fetch_regional_prices()  # HM Land Registry
tenure = fetch_tenure_distribution()  # English Housing Survey
affordability = fetch_affordability_ratio()  # ONS

# Auto-calibrate housing parameters
prop_config, market_config = calibrate_housing()
```

## Configuration Reference

### PropertyConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `count` | 12,000 | Number of properties in the simulation |
| `regions` | 11 UK regions | Region labels for heterogeneity |
| `types` | 4 types | detached, semi_detached, terraced, flat |
| `type_shares` | (0.16, 0.24, 0.28, 0.32) | Share of each type |
| `average_price` | £285,000 | UK average house price |

### HousingMarketConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `search_intensity` | 10 | Properties visited per buyer per period |
| `initial_markup` | 5% | Initial asking price markup above market value |
| `price_reduction_rate` | 10% | Monthly price reduction for unsold listings |
| `max_months_listed` | 6 | Months before delisting |
| `backward_expectation_weight` | 0.65 | Weight on backward-looking price trend |
| `expectation_lookback` | 12 | Months of price history for expectations |
| `transaction_cost` | 5% | Transaction costs (stamp duty etc.) |
| `maintenance_cost` | 1% | Annual maintenance cost as share of value |
| `rental_yield` | 4.5% | Gross rental yield |

### MortgageConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_ltv` | 90% | Maximum loan-to-value ratio |
| `max_dti` | 4.5× | Maximum debt-to-income multiple |
| `stress_test_buffer` | 3% | Rate buffer for affordability stress test |
| `default_term_months` | 300 | Default mortgage term (25 years) |
| `fixed_rate_share` | 75% | Share of new mortgages at fixed rates |
| `mortgage_risk_weight` | 0.35 | Basel risk weight for mortgage assets |
| `foreclosure_threshold` | 3 months | Arrears before foreclosure |
| `mortgage_spread` | 1.5% | Spread over policy rate |

## Simulation Output

Each period record includes:

| Field | Description |
|-------|-------------|
| `average_house_price` | Mean transaction price this period |
| `housing_transactions` | Number of sales completed |
| `housing_listings` | Properties currently on the market |
| `homeownership_rate` | Share of households who are owner-occupiers |
| `house_price_inflation` | Monthly house price change |
| `total_mortgage_lending` | Total new mortgage lending this period |
| `foreclosures` | Mortgages foreclosed this period |

Time-series properties on `SimulationResult`:

- `result.house_price_series` — average house price per period
- `result.homeownership_series` — homeownership rate per period

## Validation Targets

| Metric | Target | Source |
|--------|--------|--------|
| Homeownership rate | ~64% | English Housing Survey 2023-24 |
| Average house price | ~£285,000 | ONS UK HPI |
| Price-to-income ratio | ~8.3 | ONS Affordability Ratio |
| Average mortgage LTV | ~70% | BoE MLAR |
| Average time to sell | 3–4 months | Rightmove/Zoopla |
| Gross rental yield | 4–5% | ONS Rental Index |

## Theoretical Background

The housing market module is based on three key papers:

1. **Farmer (2025)** "Quantitative agent-based models: a promising
   alternative for macroeconomics" — describes the aspiration-level pricing
   mechanism, backward-looking expectations, and the insight that lending
   policy (not interest rates) was the primary driver of the 2008 bubble.

2. **Baptista et al. (2016)** "Macroprudential policy in an agent-based
   model of the UK housing market" — adapts the Farmer/Geanakoplos
   Washington DC model for the UK, adding FPC macroprudential tools.

3. **Carro et al. (2022)** — further development of the Bank of England
   housing ABM with improved calibration and validation.

## Future Development

- **bytes-and-mortar integration**: Use HM Land Registry Price Paid and
  EPC data for property-level calibration
- **Mortgage default risk**: Combine housing simulation, economy simulation,
  and borrower characteristics to estimate P(default)
- **Regional heterogeneity**: Full spatial model with 11 UK regions
- **Rental market**: Explicit rental market mechanism with landlord agents
