# Quick Start: Contributing to the ABM

This guide helps you get started with implementing the agent-based model.

## Prerequisites

- Python 3.13+ (or 3.10+ for compatibility)
- uv package manager (recommended) or pip
- Git

## Installation

```bash
# Clone the repository
git clone https://github.com/jstammers/companies-house-abm.git
cd companies-house-abm

# Install dependencies including ABM extras
make install  # or: uv sync --all-groups
```

## Understanding the Codebase

### 1. Read the Documentation (30 minutes)

Start here to understand the vision:

1. **ABM Summary** (`ABM_SUMMARY.md`) - 10-minute overview
2. **Design Document** (`docs/abm-design.md`) - Deep dive into theory and architecture
3. **Implementation Roadmap** (`docs/implementation-roadmap.md`) - Development plan

### 2. Explore the Structure (10 minutes)

```
src/companies_house_abm/
├── ingest.py              # Existing: Data ingestion from Companies House
├── cli.py                 # Existing: CLI interface
└── abm/                   # NEW: Agent-based model
    ├── agents/            # Agent classes
    │   └── base.py        # Base agent (implemented)
    ├── markets/           # Market mechanisms (TODO)
    └── README.md          # Module documentation

conf/base/
└── model_parameters.yml   # NEW: Model configuration

docs/
├── abm-design.md          # NEW: Comprehensive design
└── implementation-roadmap.md  # NEW: Development plan

notebooks/
└── abm_getting_started.ipynb  # NEW: Example usage
```

### 3. Review the Configuration (5 minutes)

Open `conf/base/model_parameters.yml` to see:
- Simulation settings (periods, time steps)
- Agent populations (firms, households, banks)
- Behavioral parameters (pricing, consumption, lending)
- Policy rules (Taylor rule, fiscal rules)
- Network structure (supply chains, credit)

## Development Workflow

### 1. Pick a Task

Check the [Implementation Roadmap](docs/implementation-roadmap.md) for Phase 1 tasks:

**Good first tasks**:
- [ ] Implement Firm agent class (`abm/agents/firm.py`)
- [ ] Create data loader (`abm/data/loader.py`)
- [ ] Implement simple goods market (`abm/markets/goods.py`)
- [ ] Write tests for base agent

### 2. Create a Branch

```bash
git checkout -b feature/implement-firm-agent
```

### 3. Implement Your Feature

Example: Implementing the Firm agent

```python
# src/companies_house_abm/abm/agents/firm.py

from __future__ import annotations
from typing import TYPE_CHECKING
from decimal import Decimal
from companies_house_abm.abm.agents.base import BaseAgent

if TYPE_CHECKING:
    from typing import Any

class Firm(BaseAgent):
    """Firm agent with financial data from Companies House.
    
    Attributes:
        company_id: Unique company identifier
        sector: Industry sector
        turnover: Gross operating revenue
        cash: Available cash
        employees: Number of employees
        ...
    """
    
    def __init__(
        self,
        company_id: str,
        sector: str,
        turnover: Decimal,
        cash: Decimal,
        employees: int,
        # ... other attributes from COMPANIES_HOUSE_SCHEMA
    ) -> None:
        super().__init__(agent_id=company_id)
        self.company_id = company_id
        self.sector = sector
        self.turnover = turnover
        self.cash = cash
        self.employees = employees
        # Initialize derived state
        self.inventory = Decimal(0)
        self.production = Decimal(0)
        
    def step(self) -> None:
        """Execute one time step of firm behavior."""
        # 1. Decide production
        self._decide_production()
        # 2. Set prices
        self._set_prices()
        # 3. Pay wages
        self._pay_wages()
        # 4. Update financial statements
        self._update_accounts()
        
    def _decide_production(self) -> None:
        """Determine production quantity based on demand and capacity."""
        # Simple rule: produce to capacity
        capacity = self._calculate_capacity()
        self.production = capacity
        
    def _calculate_capacity(self) -> Decimal:
        """Calculate production capacity from tangible assets."""
        # Simplified: capacity proportional to assets
        return self.turnover  # Placeholder
        
    def _set_prices(self) -> None:
        """Set product prices using markup pricing."""
        # TODO: Implement markup pricing
        pass
        
    def _pay_wages(self) -> None:
        """Pay wages to employees."""
        # TODO: Calculate wage bill and update cash
        pass
        
    def _update_accounts(self) -> None:
        """Update balance sheet and income statement."""
        # TODO: Stock-flow consistent accounting
        pass
        
    def get_state(self) -> dict[str, Any]:
        """Return current firm state."""
        return {
            'agent_id': self.agent_id,
            'company_id': self.company_id,
            'sector': self.sector,
            'turnover': float(self.turnover),
            'cash': float(self.cash),
            'employees': self.employees,
            'production': float(self.production),
            'inventory': float(self.inventory),
        }
```

### 4. Write Tests

```python
# tests/abm/test_firm.py

import pytest
from decimal import Decimal
from companies_house_abm.abm.agents.firm import Firm

def test_firm_initialization():
    """Test firm can be initialized with Companies House data."""
    firm = Firm(
        company_id="12345678",
        sector="manufacturing",
        turnover=Decimal("1000000"),
        cash=Decimal("100000"),
        employees=50,
    )
    
    assert firm.company_id == "12345678"
    assert firm.sector == "manufacturing"
    assert firm.turnover == Decimal("1000000")
    assert firm.employees == 50
    
def test_firm_step():
    """Test firm step method executes."""
    firm = Firm(
        company_id="12345678",
        sector="manufacturing",
        turnover=Decimal("1000000"),
        cash=Decimal("100000"),
        employees=50,
    )
    
    # Should not raise
    firm.step()
    
def test_firm_get_state():
    """Test firm state can be retrieved."""
    firm = Firm(
        company_id="12345678",
        sector="manufacturing",
        turnover=Decimal("1000000"),
        cash=Decimal("100000"),
        employees=50,
    )
    
    state = firm.get_state()
    assert state['company_id'] == "12345678"
    assert state['sector'] == "manufacturing"
    assert 'turnover' in state
```

### 5. Run Tests

```bash
# Run tests for your feature
make test

# Or with pytest directly
pytest tests/abm/test_firm.py -v

# With coverage
make test-cov
```

### 6. Check Code Quality

```bash
# Run all quality checks
make verify

# Or individually
make lint          # Check for issues
make format-check  # Check formatting
make type-check    # Type checking with ty
```

### 7. Fix Issues

```bash
# Auto-fix linting and formatting
make fix

# Then check again
make verify
```

### 8. Commit and Push

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git add src/companies_house_abm/abm/agents/firm.py tests/abm/test_firm.py
git commit -m "feat: implement Firm agent with Companies House data

- Add Firm agent class with financial attributes
- Implement basic production decision
- Add unit tests for firm initialization and behavior
- Follows stock-flow consistent accounting principles"

git push origin feature/implement-firm-agent
```

### 9. Create Pull Request

- Go to GitHub and create a PR
- Reference the roadmap task
- Request review from maintainers

## Common Tasks

### Loading Companies House Data

```python
import polars as pl
from pathlib import Path

# Load data
df = pl.read_parquet("data/companies_house.parquet")

# Get latest data for each firm
latest = (
    df.sort("date")
    .group_by("company_id")
    .tail(1)
)

# Filter valid firms
firms_data = latest.filter(
    pl.col("turnover_gross_operating_revenue").is_not_null() &
    (pl.col("turnover_gross_operating_revenue") > 0)
)
```

### Working with Configuration

```python
import yaml
from pathlib import Path

# Load config
config_path = Path("conf/base/model_parameters.yml")
with config_path.open() as f:
    config = yaml.safe_load(f)

# Access parameters
n_firms = config['agents']['firms']['sample_size']
markup = config['behavior']['firms']['price_markup']
```

### Running the Existing Pipeline

```bash
# Ingest Companies House data
companies_house_abm ingest --output data/companies_house.parquet

# This will take a while as it downloads from Companies House API
```

## Getting Help

### Documentation
- [ABM Design Document](docs/abm-design.md) - Theory and architecture
- [Implementation Roadmap](docs/implementation-roadmap.md) - Development plan
- [CLAUDE.md](CLAUDE.md) - AI assistant context (useful reference)

### Code Examples
- [Base Agent](src/companies_house_abm/abm/agents/base.py) - Reference implementation
- [Ingest Module](src/companies_house_abm/ingest.py) - Data processing patterns
- [Getting Started Notebook](notebooks/abm_getting_started.ipynb) - Usage examples

### Community
- Open an issue on GitHub
- Discuss in pull requests
- Reference academic papers in the design doc

## Key Principles

### 1. Stock-Flow Consistency
All financial flows must result in consistent stock changes:
```python
# Bad: Money appears from nowhere
firm.cash += revenue

# Good: Track both sides
firm.cash += revenue
household.cash -= revenue  # Household paid
```

### 2. Type Safety
Use type annotations and TYPE_CHECKING:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal
    
def calculate_profit(revenue: Decimal, costs: Decimal) -> Decimal:
    return revenue - costs
```

### 3. Decimal for Money
Use `Decimal` for financial calculations:
```python
from decimal import Decimal

# Good
price = Decimal("10.50")
quantity = Decimal("100")
revenue = price * quantity

# Bad: Floating point errors
price = 10.50
quantity = 100
revenue = price * quantity  # May have precision issues
```

### 4. Configuration-Driven
Don't hard-code parameters:
```python
# Good: Read from config
markup = config['behavior']['firms']['price_markup']
price = unit_cost * (1 + markup)

# Bad: Hard-coded
price = unit_cost * 1.15
```

### 5. Test Everything
Aim for >80% coverage:
```python
# Test normal operation
def test_firm_produces():
    ...

# Test edge cases
def test_firm_zero_employees():
    ...
    
# Test invariants
def test_accounting_identity():
    # Assets = Liabilities + Equity
    ...
```

## Next Steps

1. ✅ Read this guide
2. ✅ Review the design document
3. ✅ Set up your development environment
4. ⬜ Pick a task from the roadmap
5. ⬜ Implement and test
6. ⬜ Submit your first PR!

Welcome to the team! 🚀
