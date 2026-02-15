# API Reference

## Overview

The Companies House ABM provides Python APIs for:
- Data ingestion from Companies House XBRL accounts
- Agent-based modeling components (Firm, Household agents)
- Future: Full simulation framework

## Installation Required

To use the API documentation, first install the package:

```bash
pip install companies_house_abm
# or
uv add companies_house_abm
```

## Main Modules

### Data Ingestion (`companies_house_abm.ingest`)

Functions for ingesting Companies House XBRL data:

- `ingest_from_stream()` - Stream data from Companies House API
- `ingest_from_zips()` - Process local ZIP files
- `merge_and_write()` - Merge and deduplicate data
- `infer_start_date()` - Determine incremental ingestion start point

### Agent Classes (`companies_house_abm.agents`)

Agent-based modeling components:

- `Agent` - Abstract base class for all agents
- `Firm` - Firm agent representing companies
- `Household` - Household agent representing consumers/workers
- `SimulationState` - Abstract simulation state interface

### CLI (`companies_house_abm.cli`)

Command-line interface:

- `ingest` - Ingest Companies House data
- `hello` - Example command
- `--version` - Show version

## Example Usage

See the [Introduction notebook](https://github.com/jstammers/companies-house-abm/blob/main/notebooks/01_introduction_to_abm.ipynb) for interactive examples.

## Full API Documentation

For full API documentation with docstrings, install the package and use:

```python
help(companies_house_abm.ingest)
help(companies_house_abm.agents.Firm)
```

Or build the documentation locally:

```bash
cd companies-house-abm
make docs-serve
```
