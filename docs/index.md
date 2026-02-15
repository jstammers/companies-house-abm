# Companies House ABM

**Agent-Based Model of the UK Economy using Companies House Data**

A complexity economics approach to macroeconomic simulation, where ~5 million real firms from Companies House data interact with synthetic households, banks, and government to generate emergent macro phenomena.

## Project Status

**Current Version:** 0.1.0 (Alpha)

**Current Capabilities:**
- Companies House XBRL data ingestion (streaming and batch)
- Efficient data processing using Polars
- Command-line interface
- Foundation for agent-based modeling

**Vision:** Building toward a large-scale agent-based model with Rust core and Python bindings. See [Architecture](abm_architecture.md) and [Roadmap](roadmap.md).

## Quick Start

### Installation

Install using pip:

```bash
pip install companies_house_abm
```

Or using uv (recommended):

```bash
uv add companies_house_abm
```

### Data Ingestion

Ingest Companies House XBRL accounts data:

```bash
# Stream from Companies House API
companies_house_abm ingest --output accounts.parquet

# Process local ZIP files
companies_house_abm ingest --zip-dir ./data/zips --output accounts.parquet
```

### Python API

```python
from companies_house_abm.ingest import ingest_from_stream, merge_and_write
from pathlib import Path

# Ingest data
new_data = ingest_from_stream()
result = merge_and_write(new_data, Path("accounts.parquet"))
print(f"Ingested {len(result)} company accounts")
```

### Agent-Based Model (Preview)

```python
from companies_house_abm.agents import Firm, Household

# Create agents from Companies House data
firm = Firm(
    agent_id=1,
    company_number="12345678",
    sector="62.01",  # Computer programming
    region="UKI3",   # Inner London West
    capital=100000,
    equity=30000
)

household = Household(
    agent_id=1001,
    region="UKI3",
    income_decile=5,
    wealth=25000
)

# Full simulation framework coming in Phase 2
```

## Development

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for package management

### Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/jstammers/companies-house-abm.git
cd companies-house-abm
uv sync --group dev
```

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run ty check
```

### Prek Hooks

Install prek hooks:

```bash
prek install
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/jstammers/companies-house-abm/blob/main/LICENSE) file for details.
