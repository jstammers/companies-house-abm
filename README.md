# Companies House ABM

[![CI](https://github.com/jstammers/companies-house-abm/actions/workflows/ci.yml/badge.svg)](https://github.com/jstammers/companies-house-abm/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jstammers/companies-house-abm/branch/main/graph/badge.svg)](https://codecov.io/gh/jstammers/companies-house-abm)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/type--checked-ty-blue?labelColor=orange)](https://github.com/astral-sh/ty)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/jstammers/companies-house-abm/blob/main/LICENSE)

**Agent-Based Model of the UK Economy using Companies House Data**

A complexity economics approach to macroeconomic simulation, where ~5 million real firms from Companies House data interact with synthetic households, banks, and government to generate emergent macro phenomena.

## Features

### Current (v0.1.0)
- Fast XBRL data ingestion from Companies House (streaming and batch modes)
- Efficient data processing using Polars
- Command-line interface built with Typer
- Type-safe with full type annotations
- Comprehensive documentation — [View Docs](https://jstammers.github.io/companies-house-abm/)

### Vision: UK Economy ABM
This project is building toward a large-scale agent-based model of the UK economy:
- **~5 million Firm agents** initialized from real Companies House data
- **~30 million Household agents** (synthetic population calibrated to ONS)
- **Complexity economics** framework: emergence, bounded rationality, networks
- **Rust core** (planned) for high-performance simulation at scale
- **Python interface** for research workflows and analysis

See [Architecture Documentation](docs/abm_architecture.md) and [Roadmap](docs/roadmap.md) for details.

## Installation

```bash
pip install companies_house_abm
```

Or using uv (recommended):

```bash
uv add companies_house_abm
```

## Quick Start

### Data Ingestion

```python
from companies_house_abm.ingest import ingest_from_stream, merge_and_write
from pathlib import Path

# Ingest Companies House XBRL data
new_data = ingest_from_stream()
result = merge_and_write(new_data, Path("accounts.parquet"))
print(f"Ingested {len(result)} company accounts")
```

### CLI Usage

```bash
# Ingest data from Companies House streaming API
companies_house_abm ingest --output accounts.parquet

# Ingest from local ZIP files
companies_house_abm ingest --zip-dir ./data/zips --output accounts.parquet

# Show version
companies_house_abm --version
```

### Agent-Based Model (Preview)

```python
from companies_house_abm.agents import Firm, Household

# Create a firm agent from Companies House data
firm = Firm(
    agent_id=1,
    company_number="12345678",
    sector="62.01",  # SIC code
    region="UKI3",   # NUTS-2 region
    capital=100000,
    equity=30000,
    debt=70000
)

# Create a household agent
household = Household(
    agent_id=1001,
    region="UKI3",
    income_decile=5,
    wealth=25000,
    propensity_to_consume=0.85
)

# Simulation framework coming in Phase 2 (see roadmap)
```

## Development

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for package management

### Setup

```bash
git clone https://github.com/jstammers/companies-house-abm.git
cd companies-house-abm
make install
```

### Running Tests

```bash
make test

# With coverage
make test-cov

# Across all Python versions
make test-matrix
```

### Code Quality

```bash
# Run all checks (lint, format, type-check)
make verify

# Auto-fix lint and format issues
make fix
```

### Prek

```bash
prek install
prek run --all-files
```

### Documentation

```bash
make docs-serve
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
