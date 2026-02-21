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

## Quick Start

```python
import companies_house_abm

print(companies_house_abm.__version__)
```

### Command Line Interface

Companies House ABM provides a command-line interface:

```bash
# Show version
companies_house_abm --version

# Say hello
companies_house_abm hello World

# Profile firm data and fit distributions
companies_house_abm profile-firms \
    --parquet data/companies_house_accounts.parquet \
    --output data/firm_distribution_parameters.yml

# Profile with SIC code sector assignment
companies_house_abm profile-firms \
    --sic-file data/sic_codes.csv \
    --sample 0.01

# Output as JSON
companies_house_abm profile-firms --format json -o data/params.json
```

### Interactive Notebooks

Marimo notebooks are available in `notebooks/` for interactive exploration:

```bash
# Firm data analysis (profiling, distributions, parameter export)
marimo edit notebooks/firm_data_analysis.py

# Individual agent explorers
marimo edit notebooks/firm_agent.py
marimo edit notebooks/ecosystem.py
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
