# Companies House ABM

[![CI](https://github.com/jstammers/companies-house-abm/actions/workflows/ci.yml/badge.svg)](https://github.com/jstammers/companies-house-abm/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jstammers/companies-house-abm/branch/main/graph/badge.svg)](https://codecov.io/gh/jstammers/companies-house-abm)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/type--checked-ty-blue?labelColor=orange)](https://github.com/astral-sh/ty)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/jstammers/companies-house-abm/blob/main/LICENSE)

Agent-Based Modelling using Companies House Account Data

## Features

- **uv workspace monorepo** — standalone `companies-house` data package + ABM simulation package
- Fast and modern Python toolchain using Astral's tools (uv, ruff, ty)
- Type-safe with full type annotations
- Command-line interface built with Typer
- XBRL and PDF ingestion for Companies House accounts data
- DuckDB storage with upsert semantics for efficient OLAP queries
- Companies House REST API client (search, filings, document download)
- LLM-powered PDF extraction via litellm (Anthropic, OpenAI, Ollama, etc.)
- Agent-based model (ABM) simulating UK macroeconomic dynamics
- Public data fetcher for ONS, Bank of England, and HMRC calibration data
- Interactive economy simulator web application
- Comprehensive documentation with MkDocs — [View Docs](https://jstammers.github.io/companies-house-abm/)

## Packages

This repository contains two packages:

| Package | Install | Description |
|---------|---------|-------------|
| `companies-house` | `pip install companies-house[xbrl,llm]` | Standalone data ingestion and analysis |
| `companies_house_abm` | `pip install companies_house_abm` | ABM simulation (depends on `companies-house`) |

## Installation

```bash
pip install companies_house_abm
```

Or using uv (recommended):

```bash
uv add companies_house_abm
```

To install with ABM and web application support:

```bash
uv sync --all-groups
```

## Quick Start

```python
import companies_house_abm

print(companies_house_abm.__version__)
```

### Companies House CLI

```bash
# Search for a company
companies-house search "Exel Computer Systems"

# List filing history
companies-house filings 01873499 --category accounts --api-key YOUR_KEY

# Fetch filings and store in DuckDB (XBRL + PDF via LLM)
companies-house fetch 01873499 --db companies.duckdb --api-key YOUR_KEY

# Ingest bulk XBRL data into DuckDB
companies-house ingest --archive-dir ./zips/ --db companies.duckdb

# Query the DuckDB database
companies-house db-query "SELECT company_id, turnover_gross_operating_revenue FROM filings LIMIT 10" --db companies.duckdb

# Generate a financial analysis report
companies-house report "Exel Computer Systems" --parquet accounts.parquet
```

### ABM CLI

```bash
# Ingest Companies House XBRL data into Parquet
companies_house_abm ingest --output accounts.parquet

# Ingest from local ZIP files
companies_house_abm ingest --zip-dir ./zips/ --output accounts.parquet

# Fetch public UK economic data for ABM calibration
companies_house_abm fetch-data --output ./data/

# Fetch specific sources
companies_house_abm fetch-data --source ons --source boe

# Fetch data and write a calibrated model config
companies_house_abm fetch-data --calibrate --output ./calibrated/

# Launch the economy simulator web application
companies_house_abm serve

# Launch with custom host and port
companies_house_abm serve --host 0.0.0.0 --port 8080
```

### ABM Usage

```python
from companies_house_abm.abm import Simulation, load_config

config = load_config("config/model_parameters.yml")
sim = Simulation(config)
sim.run()
```

## Development

### Prerequisites

- Python 3.10+
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
