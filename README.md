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

- Fast and modern Python toolchain using Astral's tools (uv, ruff, ty)
- Type-safe with full type annotations
- Command-line interface built with Typer
- XBRL ingestion pipeline transforming Companies House accounts to Parquet
- Agent-based model (ABM) simulating UK macroeconomic dynamics
- Public data fetcher for ONS, Bank of England, and HMRC calibration data
- Interactive economy simulator web application
- Comprehensive documentation with MkDocs — [View Docs](https://jstammers.github.io/companies-house-abm/)

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

### CLI Usage

```bash
# Show version
companies_house_abm --version

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
