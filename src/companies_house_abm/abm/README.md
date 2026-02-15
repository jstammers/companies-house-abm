# Agent-Based Model (ABM) Module

This module implements an agent-based model of the UK economy using Companies House financial data.

## Overview

The ABM models the UK economy as a complex adaptive system with the following agent types:

- **Firms**: Modeled from Companies House data, each firm produces, consumes, employs, and makes financial decisions
- **Households**: Consume goods, supply labor, save and borrow
- **Banks**: Provide credit to firms and households, manage liquidity
- **Central Bank**: Sets monetary policy (interest rates, quantitative easing)
- **Government**: Fiscal policy (taxation, spending, transfers)

## Installation

To use the ABM functionality, install the package with the ABM extra:

```bash
uv sync --group abm
```

Or using pip:

```bash
pip install companies_house_abm[abm]
```

## Quick Start

### 1. Configuration

Model parameters are defined in `conf/base/model_parameters.yml`. You can create local overrides in `conf/local/` (which are gitignored).

### 2. Initialize Firm Agents from Data

```python
from companies_house_abm.abm.initialize import load_firms_from_parquet

# Load firm agents from Companies House data
firms = load_firms_from_parquet(
    parquet_path="data/companies_house.parquet",
    sample_size=50000,
    sampling_strategy="stratified"
)
```

### 3. Run a Simulation

```python
from companies_house_abm.abm.model import UKEconomyModel

# Initialize the model with configuration
model = UKEconomyModel(config_path="conf/base/model_parameters.yml")

# Run simulation for 400 quarters (100 years)
for i in range(400):
    model.step()
    
    # Collect and save statistics
    if i % 4 == 0:  # Every year
        stats = model.get_statistics()
        print(f"Year {i//4}: GDP={stats['gdp']:.2e}, "
              f"Unemployment={stats['unemployment_rate']:.2%}")

# Analyze results
results = model.get_results()
results.to_csv("simulation_results.csv")
```

## Module Structure

```
abm/
├── __init__.py
├── agents/
│   ├── base.py          # Base agent class
│   ├── firm.py          # Firm agent (TODO)
│   ├── household.py     # Household agent (TODO)
│   ├── bank.py          # Bank agent (TODO)
│   ├── central_bank.py  # Central bank agent (TODO)
│   └── government.py    # Government agent (TODO)
├── markets/
│   ├── goods.py         # Goods market mechanism (TODO)
│   ├── labor.py         # Labor market matching (TODO)
│   ├── credit.py        # Credit market (TODO)
│   └── interbank.py     # Interbank market (TODO)
├── model.py             # Main ABM model class (TODO)
├── scheduler.py         # Custom scheduling logic (TODO)
├── calibration.py       # Parameter calibration (TODO)
├── initialize.py        # Agent initialization from data (TODO)
└── metrics.py           # Model output and analysis (TODO)
```

## Development Status

**Current Status**: Planning and Initial Structure

- [x] Design document created (`docs/abm-design.md`)
- [x] Base agent class implemented
- [x] Configuration system defined
- [x] Module structure created
- [ ] Firm agent implementation
- [ ] Market mechanisms
- [ ] Data initialization pipeline
- [ ] Calibration utilities
- [ ] Validation against UK data
- [ ] Full model integration

## Key Features (Planned)

### Complexity Economics

- **Heterogeneous agents**: Each firm has unique financial characteristics from real data
- **Network effects**: Supply chain networks, credit networks, systemic risk
- **Adaptive behavior**: Agents learn and adjust strategies
- **Emergent phenomena**: Business cycles, crises arise from micro interactions

### Stock-Flow Consistency

- All financial flows (income, spending, lending) result in consistent stock changes
- Accounting identities enforced at sectoral and aggregate levels
- No "black holes" - money is conserved in the system

### Policy Analysis

- **Monetary policy**: Interest rate rules, quantitative easing, macroprudential regulation
- **Fiscal policy**: Government spending, taxation, automatic stabilizers
- **Structural policy**: Industrial policy, competition policy, labor market reforms

### Validation

The model aims to replicate key stylized facts:

- Fat-tailed firm size distribution (Zipf's law)
- Laplace distribution of firm growth rates
- Persistent unemployment
- Endogenous credit cycles
- Pro-cyclical leverage
- Autocorrelated GDP growth

## Implementation Options

### Python (Mesa Framework)

**Advantages**:
- Rapid prototyping
- Rich ecosystem
- Easy integration with existing data pipeline
- Good visualization tools

**Use for**:
- Initial development
- Models with <100k agents
- Research and exploration

### Rust (Krabmaga + PyO3)

**Advantages**:
- 10-100x performance improvement
- Can handle millions of agents
- Efficient parallel execution

**Use for**:
- Large-scale simulations (>100k agents)
- Production deployments
- Computationally intensive scenarios

**Setup** (if using Rust):

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install maturin for building Python bindings
pip install maturin

# Build Rust ABM with Python bindings
maturin develop --release
```

## Further Reading

- [ABM Design Document](../docs/abm-design.md) - Comprehensive design and theory
- [Mesa Documentation](https://mesa.readthedocs.io/) - Python ABM framework
- [Krabmaga](https://github.com/krABMaga/krABMaga) - Rust ABM framework

## References

Key papers on agent-based macroeconomics:

1. Farmer, J.D. & Foley, D. (2009). "The economy needs agent-based modelling." *Nature*
2. Delli Gatti, D. et al. (2011). "Macroeconomics from the Bottom-up." Springer
3. Dawid, H. & Delli Gatti, D. (2018). "Agent-Based Macroeconomics." Handbook of Computational Economics
4. Poledna, S. et al. (2018). "The multi-layer network nature of systemic risk." Nature Communications

## Contributing

See the [contributing guide](../CONTRIBUTING.md) for information on how to contribute to the ABM implementation.
