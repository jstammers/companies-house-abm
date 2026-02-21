# Companies House ABM

Agent-Based Modelling using Companies House Account Data

## Installation

Install using pip:

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

### Command Line Interface

Companies House ABM provides a command-line interface with the following commands:

#### Ingest XBRL data

```bash
# Stream all available data from the Companies House API
companies_house_abm ingest --output accounts.parquet

# Ingest from local ZIP files
companies_house_abm ingest --zip-dir ./zips/ --output accounts.parquet

# Stream data from a specific start date
companies_house_abm ingest --start-date 2024-01-01 --output accounts.parquet
```

#### Fetch calibration data

Download publicly available UK economic data from ONS, Bank of England, and HMRC
to calibrate the ABM parameters:

```bash
# Fetch all sources and save to ./data/
companies_house_abm fetch-data

# Fetch only ONS and Bank of England data
companies_house_abm fetch-data --source ons --source boe

# Fetch all data and write a calibrated model config
companies_house_abm fetch-data --calibrate --output ./calibrated/
```

#### Launch the web application

```bash
# Start the economy simulator at http://127.0.0.1:8000
companies_house_abm serve

# Custom host and port
companies_house_abm serve --host 0.0.0.0 --port 8080

# Enable auto-reload for development
companies_house_abm serve --reload
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

Clone the repository and install dependencies:

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

### Prek Hooks

Install prek hooks:

```bash
prek install
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/jstammers/companies-house-abm/blob/main/LICENSE) file for details.
