# uk-data

A standalone Python package that provides a unified, canonical interface for
fetching UK public economic and business data from multiple official sources.

## Overview

`uk-data` wraps six data sources behind a single `UKDataClient` API,
normalising their outputs into three canonical model types — `TimeSeries`,
`Entity`, and `Event` — so downstream consumers (such as the
[`companies_house_abm`](../companies-house-abm/) simulation) need no
source-specific knowledge.

## Data Sources

| Adapter | Source | Data types |
|---|---|---|
| `ons` | Office for National Statistics API | Time series (GDP, unemployment, earnings, …) |
| `boe` | Bank of England IADB | Time series (Bank Rate, mortgage rates, CET1) |
| `hmrc` | HMRC (static) | Time series (corporation tax, income tax, VAT) |
| `land_registry` | HM Land Registry SPARQL / Price Paid CSV | Time series (HPI), Events (property transactions) |
| `companies_house` | Companies House REST API + bulk download | Entities (companies), Events (filing history) |
| `epc` | EPC Open Data API | Events (EPC lodgements) |

## Installation

```bash
# As part of the workspace (development)
uv sync --all-groups

# Standalone
pip install uk-data
```

## Quick Start

```python
from uk_data import UKDataClient

client = UKDataClient()

# Fetch a canonical macro series by concept name
ts = client.get_series("gdp")
print(ts.latest_value)          # e.g. 564_912.0

# Discover all available series per source
for src in client.list_sources():
    print(src.name, src.series)

# Discover which sources expose entity lookup
for info in client.list_entities():
    print(info.source, info.entity_types)   # companies_house ['company']

# Discover which sources expose events
for info in client.list_events():
    print(info.source, info.event_types)

# Fetch a company entity
entity = client.get_entity("BBC")
print(entity.name, entity.source_id)

# Fetch filing events for a company (by Companies House number)
events = client.get_events(entity_id="companies_house:00101498")
for ev in events[:3]:
    print(ev.event_type, ev.timestamp)
```

## CLI

```bash
# Show available data sources
ukd sources

# Fetch a canonical time series
ukd series gdp

# List available entities
ukd entities

# List available events
ukd events
```

## Canonical Concepts

`get_series()` accepts concept strings resolved via the built-in registry:

| Concept | Primary source |
|---|---|
| `gdp` | ONS `ABMI` |
| `household_income` | ONS `RPHQ` |
| `savings_ratio` | ONS `NRJS` |
| `unemployment` | ONS `MGSX` |
| `average_earnings` | ONS `KAB9` |
| `bank_rate` | BoE `IUMABEDR` |
| `mortgage_rate` | BoE `IUMTLMV` |
| `business_rate` | BoE `IUMZICQ` |
| `house_price_uk` | Land Registry `uk_hpi_average` |
| `affordability` | ONS `HP7A` |
| `rental_growth` | ONS `D7RA` |
| `corp_tax_rate` | HMRC `corporation_tax_2024` |
| `income_tax_basic` | HMRC `income_tax_basic_2024` |
| `vat_standard` | HMRC `vat_standard_2024` |

## Package Structure

```
packages/uk-data/
├── src/uk_data/
│   ├── __init__.py          # Public API: UKDataClient, SourceInfo, EntityTypeInfo,
│   │                        #   EventTypeInfo, TimeSeries, Entity, Event
│   ├── client.py            # UKDataClient + info dataclasses
│   ├── registry.py          # CONCEPT_REGISTRY + ConceptResolver
│   ├── _http.py             # Shared HTTP helpers (urllib, in-memory cache)
│   ├── cli.py               # Typer CLI (ukd entrypoint)
│   ├── adapters/
│   │   ├── base.py          # BaseAdapter ABC
│   │   ├── ons.py           # ONSAdapter
│   │   ├── boe.py           # BoEAdapter
│   │   ├── hmrc.py          # HMRCAdapter
│   │   ├── land_registry.py # LandRegistryAdapter
│   │   ├── companies_house.py  # CompaniesHouseAdapter
│   │   ├── epc.py           # EPCAdapter
│   │   └── historical.py    # HistoricalAdapter (utility)
│   ├── models/
│   │   ├── timeseries.py    # TimeSeries
│   │   ├── entity.py        # Entity
│   │   └── event.py         # Event
│   └── storage/             # CanonicalStore (optional DuckDB persistence)
└── tests/
    ├── test_client.py                       # Offline unit tests
    ├── test_client_integration.py           # Live network integration tests
    └── adapters/                            # Per-adapter test files
```

## Running Tests

```bash
# Unit tests only (no network)
make test-uk-data

# Integration tests (requires live internet access)
make test-uk-data-integration

# All tests across the whole workspace (includes these)
make test
```

Integration tests are marked with `pytest.mark.integration` and are excluded
from the default `make test` / CI run. Run them explicitly with
`make test-uk-data-integration` or
`uv run pytest packages/uk-data/tests/ -m integration -v`.

## Environment Variables

| Variable | Purpose |
|---|---|
| `COMPANIES_HOUSE_API_KEY` | API key for Companies House REST API (entity + event fetch) |
| `EPC_API_USER` / `EPC_API_PASS` | Credentials for EPC Open Data API download |
