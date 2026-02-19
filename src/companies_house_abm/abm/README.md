# Agent-Based Model (ABM) Module

This module implements an agent-based model of the UK economy using Companies House financial data.

## Overview

The ABM models the UK economy as a complex adaptive system with five agent types interacting through three markets:

**Agents:**

- **Firm** (`agents/firm.py`): Productive agents with balance sheets, pricing, production and employment decisions
- **Household** (`agents/household.py`): Labour supply, consumption and savings
- **Bank** (`agents/bank.py`): Credit provision with Basel III capital constraints
- **Central Bank** (`agents/central_bank.py`): Monetary policy via Taylor rule
- **Government** (`agents/government.py`): Taxation, spending and fiscal rule

**Markets:**

- **Goods Market** (`markets/goods.py`): Firms post prices; households and government purchase
- **Labour Market** (`markets/labor.py`): Vacancy posting, job search and matching with frictions
- **Credit Market** (`markets/credit.py`): Firms borrow from banks with risk-based pricing

## Installation

```bash
uv sync --group abm
```

## Quick Start

```python
from companies_house_abm.abm import Simulation

# Run with default configuration
sim = Simulation.from_config()
result = sim.run(periods=40)

# Inspect results
for rec in result.records:
    print(f"Period {rec.period}: GDP={rec.gdp:,.0f}  "
          f"Unemployment={rec.unemployment_rate:.1%}")
```

### Custom Configuration

```python
from companies_house_abm.abm.config import (
    ModelConfig, SimulationConfig, FirmBehaviorConfig,
)
from companies_house_abm.abm.model import Simulation

config = ModelConfig(
    simulation=SimulationConfig(periods=100, seed=7),
    firm_behavior=FirmBehaviorConfig(price_markup=0.20),
)
sim = Simulation(config)
sim.initialize_agents()
result = sim.run()
```

### YAML Configuration

Parameters can also be loaded from `config/model_parameters.yml`:

```python
from companies_house_abm.abm import load_config, Simulation

config = load_config()  # loads default config/model_parameters.yml
sim = Simulation(config)
sim.initialize_agents()
result = sim.run(periods=50)
```

## Module Structure

```
abm/
├── __init__.py          # Package exports (Simulation, ModelConfig, load_config)
├── config.py            # Dataclass configuration and YAML loader
├── model.py             # Simulation orchestrator
├── agents/
│   ├── base.py          # Abstract BaseAgent class
│   ├── firm.py          # Firm agent
│   ├── household.py     # Household agent
│   ├── bank.py          # Bank agent
│   ├── central_bank.py  # Central bank agent
│   └── government.py    # Government agent
└── markets/
    ├── base.py          # Abstract BaseMarket class
    ├── goods.py         # Goods market
    ├── labor.py         # Labour market
    └── credit.py        # Credit market
```

## Interactive Notebooks

Marimo notebooks in `notebooks/` provide interactive exploration of each component:

- `firm_agent.py` — Firm dynamics and parameter sensitivity
- `household_agent.py` — Consumption, saving and wealth distribution
- `bank_agent.py` — Lending decisions and NPL impact
- `policy_agents.py` — Taylor rule and fiscal dynamics
- `ecosystem.py` — Full simulation with all agents and markets

Run a notebook with:

```bash
uv run marimo edit notebooks/ecosystem.py
```

## References

1. Farmer, J.D. & Foley, D. (2009). "The economy needs agent-based modelling." *Nature*
2. Delli Gatti, D. et al. (2011). "Macroeconomics from the Bottom-up." Springer
3. Dawid, H. & Delli Gatti, D. (2018). "Agent-Based Macroeconomics." *Handbook of Computational Economics*
4. Godley, W. & Lavoie, M. (2007). "Monetary Economics: An Integrated Approach." Palgrave
