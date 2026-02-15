# Companies House ABM

[![CI](https://github.com/jstammers/companies-house-abm/actions/workflows/ci.yml/badge.svg)](https://github.com/jstammers/companies-house-abm/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jstammers/companies-house-abm/branch/main/graph/badge.svg)](https://codecov.io/gh/jstammers/companies-house-abm)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/type--checked-ty-blue?labelColor=orange)](https://github.com/astral-sh/ty)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/jstammers/companies-house-abm/blob/main/LICENSE)

Agent-Based Modelling using Companies House Account Data

## Features

- Fast and modern Python toolchain using Astral's tools (uv, ruff, ty)
- Type-safe with full type annotations
- Command-line interface built with Typer
- Comprehensive documentation with MkDocs — [View Docs](https://jstammers.github.io/companies-house-abm/)

## Installation

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

### CLI Usage

```bash
# Show version
companies_house_abm --version

# Say hello
companies_house_abm hello World
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
