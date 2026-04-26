# Codebase Structure

**Analysis Date:** 2026-04-26

## Directory Layout

```
EarningsAI/                            # Workspace root (virtual, not publishable)
├── pyproject.toml                     # uv workspace root — dev/docs deps + tool config
├── uv.lock                            # Lockfile (committed)
├── Makefile                           # Developer task runner
├── Dockerfile                         # Container build
├── config/                            # ABM model YAML configuration
│   ├── model_parameters.yml           # 200+ ABM parameters (default config)
│   └── sector_representative_model.yml # Sector-representative simulation config
├── data/                              # Ingested data (local, gitignored)
│   └── archive/                       # CH bulk ZIP archives
├── notebooks/                         # Marimo interactive notebooks
├── outputs/                           # Simulation output files (local)
│   ├── .drafts/
│   └── .plans/
├── papers/                            # Research papers / references
├── results/                           # Simulation result CSVs/JSONs (local)
├── scripts/
│   ├── build_rust_abm.sh              # Build & install Rust extension
│   └── run_benchmark.py               # Python vs Rust benchmark
├── docs/                              # MkDocs documentation source
├── tests/                             # Root test suite (all packages tested together)
│   ├── conftest.py
│   ├── fixtures/                      # Real XBRL test files (HTML + XML)
│   ├── test_abm_*.py                  # ABM agent/market/model/config tests
│   ├── test_companies_house_*.py      # companies_house package tests
│   ├── test_data_sources*.py          # Data source & calibration tests
│   ├── test_historical*.py            # Historical simulation tests
│   ├── test_housing*.py               # Housing market tests
│   ├── test_ingest.py                 # XBRL ingest tests
│   ├── test_company_analysis.py       # Analysis tests
│   ├── test_firm_distributions.py     # Distribution fitting tests
│   ├── test_sector_model.py           # Sector-representative model tests
│   ├── test_scenarios.py              # Scenario builder tests
│   ├── test_webapp.py                 # FastAPI webapp tests
│   └── test_xbrl_schema_integration.py # Real XBRL fixture validation
└── packages/                          # Workspace packages
    ├── uk-data/                       # Package: canonical UK public data
    ├── companies-house/               # Package: filing ingestion & analysis
    ├── companies-house-abm/           # Package: ABM simulation
    └── rust-abm/                      # Rust extension (NOT a uv member)
```

---

## Package Internals

### `packages/uk-data/`

```
packages/uk-data/
├── pyproject.toml
├── src/uk_data/
│   ├── __init__.py
│   ├── py.typed
│   ├── _http.py               # Shared urllib HTTP + in-memory cache
│   ├── client.py              # UKDataClient (facade over all adapters)
│   ├── registry.py            # CONCEPT_REGISTRY, ConceptResolver
│   ├── cli.py                 # uk-data CLI
│   ├── adapters/
│   │   ├── base.py            # BaseAdapter ABC
│   │   ├── ons.py             # ONSAdapter
│   │   ├── ons_manifest.py    # ONS series manifest + concept map
│   │   ├── ons_provider.py    # ONS data provider helpers
│   │   ├── boe.py             # BoEAdapter
│   │   ├── hmrc.py            # HMRCAdapter
│   │   ├── land_registry.py   # LandRegistryAdapter
│   │   ├── companies_house.py # CompaniesHouseAdapter (REST API)
│   │   ├── epc.py             # EPCAdapter
│   │   └── historical.py      # HistoricalAdapter
│   ├── models/                # Canonical data models (TimeSeries, Entity, Event)
│   ├── storage/               # CanonicalStore
│   ├── api/                   # Companies House REST API client
│   │   ├── client.py          # APIConfig, CompaniesHouseClient
│   │   ├── search.py          # search_companies
│   │   ├── filings.py         # get_filing_history, download_document
│   │   └── models.py          # CompanySearchResult, Filing
│   └── data/                  # Bundled static data files
└── tests/
    ├── conftest.py
    ├── test_registry.py
    ├── test_companies_house_api.py
    └── adapters/              # Per-adapter tests
```

### `packages/companies-house/`

```
packages/companies-house/
├── pyproject.toml
└── src/companies_house/
    ├── __init__.py            # Exports: CompanyFiling, COMPANIES_HOUSE_SCHEMA, etc.
    ├── py.typed
    ├── schema.py              # 39-column schema + CompanyFiling Pydantic model
    ├── cli.py                 # Typer CLI (ingest, search, filings, fetch, report, …)
    ├── ingest/
    │   ├── base.py            # IngestSource protocol
    │   ├── xbrl.py            # XBRL from ZIPs/streaming
    │   └── pdf.py             # PDF via kreuzberg (optional dep)
    ├── storage/
    │   ├── db.py              # CompaniesHouseDB (DuckDB, upsert)
    │   └── migrations.py      # Parquet → DuckDB migration
    └── analysis/
        ├── reports.py         # CompanyReport, analyse_company, generate_report
        ├── forecasting.py     # ForecastResult, linear trend
        ├── benchmarks.py      # SectorBenchmark, peer comparison
        └── formatting.py      # Report text generation
```

### `packages/companies-house-abm/`

```
packages/companies-house-abm/
├── pyproject.toml
└── src/companies_house_abm/
    ├── __init__.py
    ├── py.typed
    ├── cli.py                 # Typer CLI (ingest, fetch-data, profile-firms, run-simulation, …)
    ├── _rust_abm.cpython-*.so # Built Rust extension (when compiled)
    ├── data_sources/
    │   ├── _http.py           # Shared HTTP + in-memory cache
    │   ├── boe.py             # Bank of England data
    │   ├── ons.py             # ONS data
    │   ├── hmrc.py            # HMRC tax data
    │   ├── land_registry.py   # House price data
    │   ├── historical.py      # Quarterly historical time-series
    │   ├── companies_house.py # SIC code bulk fetch
    │   ├── input_output.py    # ONS IO table helpers
    │   ├── firm_distributions.py # Distribution fitting pipeline
    │   └── calibration.py     # calibrate_model() → ModelConfig
    ├── abm/
    │   ├── config.py          # ModelConfig frozen dataclasses + load_config()
    │   ├── model.py           # Simulation (mesa.Model), PeriodRecord, SimulationResult
    │   ├── calibration.py     # ABM-level calibration helpers
    │   ├── evaluation.py      # evaluate_simulation, evaluate_historical
    │   ├── historical.py      # HistoricalSimulation
    │   ├── scenarios.py       # build_uk_2013_2024
    │   ├── sector_model.py    # create_sector_representative_simulation
    │   ├── agents/
    │   │   ├── base.py        # BaseAgent
    │   │   ├── firm.py        # Firm
    │   │   ├── household.py   # Household
    │   │   ├── bank.py        # Bank
    │   │   ├── central_bank.py # CentralBank (Taylor rule)
    │   │   └── government.py  # Government (fiscal rule)
    │   ├── markets/
    │   │   ├── base.py        # BaseMarket ABC
    │   │   ├── goods.py       # GoodsMarket
    │   │   ├── labor.py       # LaborMarket
    │   │   ├── credit.py      # CreditMarket
    │   │   └── housing.py     # HousingMarket
    │   └── assets/
    │       ├── property.py    # Property
    │       └── mortgage.py    # Mortgage
    └── webapp/                # Deprecated FastAPI UI
        ├── app.py
        ├── models.py
        └── static/            # index.html, app.js, styles.css
```

### `packages/rust-abm/` (not a uv workspace member)

```
packages/rust-abm/
├── Cargo.toml
├── pyproject.toml             # maturin build config
├── python/companies_house_abm/ # Python stubs for the extension
└── src/
    ├── agents/                # Rust agent implementations
    └── markets/               # Rust market implementations
```

---

## Key File Locations

**Workspace Configuration:**
- `pyproject.toml` — workspace root, ruff/ty/pytest/coverage config
- `uv.lock` — committed lockfile
- `Makefile` — developer commands

**Package Manifests:**
- `packages/uk-data/pyproject.toml`
- `packages/companies-house/pyproject.toml`
- `packages/companies-house-abm/pyproject.toml`
- `packages/rust-abm/pyproject.toml` (maturin, separate build)

**Schema / Core Models:**
- `packages/companies-house/src/companies_house/schema.py` — `COMPANIES_HOUSE_SCHEMA`, `CompanyFiling`

**ABM Configuration:**
- `config/model_parameters.yml` — default 200+ ABM parameters
- `config/sector_representative_model.yml` — sector model variant
- `packages/companies-house-abm/src/companies_house_abm/abm/config.py` — `ModelConfig`, `load_config()`

**Storage:**
- `packages/companies-house/src/companies_house/storage/db.py` — `CompaniesHouseDB`
- Default DuckDB path: `~/.companies_house/data.duckdb`

**CLIs:**
- `packages/companies-house/src/companies_house/cli.py`
- `packages/companies-house-abm/src/companies_house_abm/cli.py`

**Tests:**
- `tests/` — root suite (all packages)
- `packages/uk-data/tests/` — uk-data specific tests

---

## Naming Conventions

**Files:**
- `snake_case.py` throughout all packages
- Private helpers prefixed with `_` (e.g. `_http.py`, `_rust_abm.so`)
- Test files: `test_<module_or_feature>.py`

**Directories:**
- `snake_case` for Python source directories
- Kebab-case for package directories under `packages/` (e.g. `companies-house-abm`)

**Classes:**
- `PascalCase` (e.g. `CompaniesHouseDB`, `ModelConfig`, `GoodsMarket`, `BaseAgent`)

**Functions/Variables:**
- `snake_case` throughout

---

## Where to Add New Code

**New data source adapter:**
- Implement `BaseAdapter` in `packages/uk-data/src/uk_data/adapters/<source>.py`
- Register in `packages/uk-data/src/uk_data/client.py` `UKDataClient.adapters`
- Add concepts to `packages/uk-data/src/uk_data/registry.py` `CONCEPT_REGISTRY`

**New ABM agent type:**
- Extend `BaseAgent` in `packages/companies-house-abm/src/companies_house_abm/abm/agents/<type>.py`
- Import and instantiate in `packages/companies-house-abm/src/companies_house_abm/abm/model.py` `Simulation.initialize_agents()`

**New market:**
- Extend `BaseMarket` in `packages/companies-house-abm/src/companies_house_abm/abm/markets/<name>.py`
- Instantiate in `Simulation.__init__()` and call `clear()` in the step loop

**New simulation output metric:**
- Add field to `PeriodRecord` dataclass in `packages/companies-house-abm/src/companies_house_abm/abm/model.py`
- Populate in the step loop; it will be collected by `SimulationDataCollector` automatically

**New CLI command:**
- Add `@app.command()` to the relevant CLI module (`cli.py` of the appropriate package)
- Use lazy imports inside the command function body for optional deps

**New ingestion format:**
- Implement `IngestSource` protocol in `packages/companies-house/src/companies_house/ingest/<format>.py`
- Wire into `cli.py` `ingest` or `fetch` commands

**New tests:**
- Place in `tests/test_<module>.py` for cross-package integration
- Or `packages/uk-data/tests/` for uk-data-specific tests
- Use `:memory:` DuckDB for storage tests; `unittest.mock.patch` for external calls

---

## Special Directories

**`data/`:**
- Purpose: Locally ingested Companies House Parquet + raw data files
- Generated: Yes (by ingest commands)
- Committed: No (gitignored)

**`results/`:**
- Purpose: Simulation output CSVs/JSONs/Parquet
- Generated: Yes (by `run-simulation`)
- Committed: No (gitignored)

**`outputs/`:**
- Purpose: Draft outputs and plan artifacts
- Generated: Yes
- Committed: No

**`config/`:**
- Purpose: ABM model parameter YAML files
- Generated: Manually maintained; can be overwritten by `fetch-data --calibrate`
- Committed: Yes

**`site/`:**
- Purpose: MkDocs built documentation
- Generated: Yes (`make docs`)
- Committed: No

**`.planning/`:**
- Purpose: GSD project planning artifacts (roadmap, codebase maps, phase plans)
- Generated: Yes (by GSD commands)
- Committed: Yes

---

*Structure analysis: 2026-04-26*
