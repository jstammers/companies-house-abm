# ABM Summary: UK Economy Agent-Based Model Plan

## Overview

This repository now includes a comprehensive plan for implementing an agent-based model (ABM) of the UK economy. The model will use real Companies House financial data to simulate firms as individual agents, alongside households, banks, central bank, and government agents, to study emergent macroeconomic dynamics.

## What's Been Added

### 1. Documentation (3 Major Documents)

#### a. ABM Design Document (`docs/abm-design.md`) - 23KB
A comprehensive design document covering:
- **Theoretical foundation**: Stock-flow consistency, complexity economics, post-Keynesian economics
- **Agent types**: Detailed specifications for firms, households, banks, central bank, government
- **Markets**: Goods, labor, credit, and interbank markets
- **Model dynamics**: Time steps, accounting, emergent phenomena
- **Calibration**: How to initialize from Companies House data
- **Implementation options**: Python (Mesa) vs Rust (Krabmaga) with PyO3 bindings
- **Validation targets**: UK stylized facts to replicate
- **Policy experiments**: Monetary, fiscal, and macroprudential scenarios

#### b. Implementation Roadmap (`docs/implementation-roadmap.md`) - 8.4KB
A detailed 12-month development plan with:
- **Phase 1 (Months 1-3)**: Foundation - firm agents and goods market
- **Phase 2 (Months 4-6)**: Core model - all agent types
- **Phase 3 (Months 7-9)**: Networks and heterogeneity
- **Phase 4 (Months 10-12)**: Validation and policy analysis
- **Phase 5 (Optional)**: Advanced features (Rust port, regional model, housing)
- Weekly milestones and deliverables
- Testing strategy and success criteria

#### c. ABM Module README (`src/companies_house_abm/abm/README.md`) - 5.9KB
User-facing documentation with:
- Quick start guide
- Installation instructions
- Module structure overview
- Implementation status
- Python vs Rust comparison

### 2. Code Structure

#### a. Module Organization
```
src/companies_house_abm/abm/
├── __init__.py              # Package initialization with docstring
├── agents/
│   ├── __init__.py          # Agent package exports
│   └── base.py              # BaseAgent abstract class
└── markets/
    └── __init__.py          # Market mechanisms package
```

#### b. Base Agent Class (`agents/base.py`)
- Abstract base class defining the agent interface
- All agents inherit from this and implement `step()` and `get_state()`
- UUID-based unique identifiers
- Type-safe design with proper typing

### 3. Configuration

#### Model Parameters (`config/model_parameters.yml`) - 8KB
Comprehensive YAML configuration covering:

**Simulation Settings**:
- 400 periods (100 years quarterly)
- Reproducible seeds
- Warm-up periods

**Agent Parameters**:
- Firms: 50,000 agents, stratified sampling, entry/exit dynamics
- Households: 10,000 agents, income/wealth distributions
- Banks: 10 agents, capital requirements
- Central bank and government settings

**Behavioral Parameters**:
- Firm pricing (markup rules)
- Investment decisions
- Wage dynamics
- Consumer behavior
- Credit rationing

**Market Mechanisms**:
- Price and quantity adjustment speeds
- Wage stickiness
- Matching efficiency

**Policy Rules**:
- Taylor rule for monetary policy
- Fiscal rules and automatic stabilizers
- Tax rates and spending targets

**Network Structure**:
- Supply chain topology
- Credit network formation

**Shocks and Scenarios**:
- Demand, productivity, financial shocks
- Policy experiments

**Output Configuration**:
- Data collection frequency
- Aggregate and distributional statistics
- Network metrics

**Validation Targets**:
- UK macroeconomic statistics for calibration

### 4. Dependencies

Updated `pyproject.toml` with new `abm` dependency group:
```toml
[dependency-groups.abm]
- mesa>=3.0.0              # Python ABM framework
- networkx>=3.2            # Network analysis
- numpy>=1.26.0            # Numerical computing
- scipy>=1.11.0            # Scientific computing
- matplotlib>=3.8.0        # Visualization
- pyyaml>=6.0.0            # YAML config parsing
```

### 5. Example Notebook

`notebooks/abm_getting_started.ipynb` demonstrates:
- Loading Companies House data
- Analyzing firm size distributions (Zipf's law)
- Example ABM initialization code (for when implemented)
- Simulation loop structure
- Results visualization
- Policy experiment framework
- Network analysis examples

### 6. Documentation Site Updates

Updated `mkdocs.yml` navigation to include:
- ABM Design
- Implementation Roadmap

## Key Design Decisions

### 1. Hybrid Implementation Strategy

**Phase 1**: Start with Python/Mesa
- Rapid prototyping
- Easy debugging
- Rich ecosystem
- Good for 10k-100k agents

**Phase 2 (if needed)**: Port to Rust
- 10-100x performance
- Handle millions of agents
- Use PyO3/Maturin for Python bindings
- Keep data layer in Python

### 2. Stock-Flow Consistent Accounting

All financial flows result in consistent stock changes:
- Sectoral balance identity enforced
- No "black holes" - money is conserved
- Proper double-entry bookkeeping

### 3. Network-Based Modeling

**Supply Chain Network**:
- Based on ONS input-output tables
- Captures sectoral interdependencies
- Enables shock propagation analysis

**Credit Network**:
- Bank-firm lending relationships
- Interbank exposure
- Systemic risk measurement

### 4. Complexity Economics Principles

- **Heterogeneity**: Each firm unique (real data)
- **Adaptation**: Agents learn and adjust
- **Emergence**: Macro patterns from micro rules
- **Networks**: Non-trivial interaction structure
- **Far-from-equilibrium**: No equilibrium assumption

### 5. Policy-Relevant Design

Built for policy analysis:
- **Monetary**: Interest rates, QE, macroprudential
- **Fiscal**: Spending, taxation, automatic stabilizers
- **Structural**: Sector support, competition policy
- Counterfactual scenarios
- Welfare analysis

## Model Validation Strategy

The model will be validated at multiple levels:

### Micro-level
- Firm behaviors (pricing, investment) match empirical studies
- Realistic financial ratios

### Meso-level
- Sectoral dynamics
- Network properties (degree distributions, clustering)

### Macro-level
Replicate UK stylized facts:
1. **Firm size distribution**: Power law (Zipf) with exponent ~1.06
2. **Firm growth rates**: Laplace/tent-shaped distribution
3. **GDP growth**: Mean ~2% annual, autocorrelated, fat tails
4. **Unemployment**: Persistent, fluctuates around 4-5%
5. **Inflation**: Mean ~2%, volatile
6. **Credit cycles**: Endogenous boom-bust patterns
7. **Pro-cyclical leverage**: Debt rises in booms

## Data Requirements

### Primary Data (Already Available)
- **Companies House XBRL**: Firm financial statements
- Schema: 39 columns including balance sheet, P&L, employment

### Additional Data Needed
- **ONS Input-Output Tables**: For supply chain network (~100MB)
- **ONS Macroeconomic Data**: GDP, employment, inflation (~50MB)
- **Bank of England Statistics**: Interest rates, credit aggregates (~20MB)
- **Income/Wealth Distributions**: For household initialization

## Usage Example

Once implemented, the model will be used like this:

```python
from companies_house_abm.abm import UKEconomyModel
from companies_house_abm.abm.initialize import load_firms_from_parquet

# Load configuration
config_path = "config/model_parameters.yml"

# Initialize model
model = UKEconomyModel(
    config_path=config_path,
    data_path="data/companies_house.parquet",
    seed=42
)

# Run simulation
for period in range(400):  # 100 years
    model.step()
    
# Get results
results = model.get_results()
results.to_csv("simulation_output.csv")

# Policy experiment
model_stimulus = UKEconomyModel(config_path=config_path, seed=42)
model_stimulus.government.increase_spending(0.05)  # +5%
# ... run and compare
```

## Next Steps for Implementation

### Immediate (Week 1-2)
1. Set up Mesa framework integration
2. Create model class skeleton
3. Implement scheduler
4. Write unit tests for base classes

### Short-term (Month 1)
1. Implement Firm agent with Companies House data loading
2. Create simple goods market
3. Basic simulation runs
4. Output visualization

### Medium-term (Months 2-6)
1. Add all agent types
2. Implement all markets
3. Build networks
4. Calibrate to UK data
5. Validate against stylized facts

### Long-term (Months 7-12)
1. Policy experiments
2. Sensitivity analysis
3. Documentation and examples
4. Performance optimization (Rust port if needed)
5. Release v1.0

## Technical Considerations

### Performance
- **Small scale** (<10k agents): Pure Python fine
- **Medium scale** (10k-100k): Optimize with Numba
- **Large scale** (>100k): Consider Rust port

### Reproducibility
- Seed control for all RNGs
- Version-pinned dependencies
- Docker containers for environment
- Git for code versioning

### Testing
- Unit tests for agent behaviors
- Integration tests for markets
- System tests for full runs
- Property tests for invariants (SFC)
- Regression tests

## References and Resources

### Key Papers
1. Farmer & Foley (2009) - "The economy needs agent-based modelling"
2. Delli Gatti et al. (2011) - "Macroeconomics from the Bottom-up"
3. Dawid & Delli Gatti (2018) - "Agent-Based Macroeconomics"
4. Poledna et al. (2018) - "Multi-layer network nature of systemic risk"

### Frameworks
- Mesa: https://mesa.readthedocs.io/
- Krabmaga: https://github.com/krABMaga/krABMaga
- PyO3: https://pyo3.rs/

### Data Sources
- ONS: https://www.ons.gov.uk/
- Bank of England: https://www.bankofengland.co.uk/statistics
- Companies House: https://www.gov.uk/government/organisations/companies-house

## Contributing

To contribute to the ABM implementation:

1. Read the design document (`docs/abm-design.md`)
2. Check the roadmap (`docs/implementation-roadmap.md`)
3. Pick a task (issues will be created)
4. Follow conventional commits
5. Ensure tests pass (`make test`)
6. Submit PR

## Questions and Discussion

For questions about the ABM design or implementation:
- Open an issue on GitHub
- Reference the design document
- Suggest improvements via PRs

---

**Status**: Planning Complete ✅  
**Implementation**: Not Started (Phase 1 ready to begin)  
**Last Updated**: 2026-02-15
