# Architecture

**Analysis Date:** 2026-04-26

## Pattern Overview

**Overall:** Layered uv workspace monorepo with four cooperating packages, following a data-pipeline → simulation pipeline pattern.

**Key Characteristics:**
- Four packages with strict dependency ordering: `uk-data` ← `companies-house` ← `companies-house-abm` (+ optional `rust-abm`)
- Clear separation between data ingestion, canonical data access, ABM simulation, and reporting layers
- Dual storage strategy: Parquet (legacy bulk) + DuckDB (preferred, upsert-based)
- Mesa-based agent-based modelling with frozen-dataclass configuration and YAML loading
- Rust optional performance extension (maturin, not a uv workspace member)

---

## Packages and Layers

### `uk-data` — Canonical UK Data Access Layer
- **Location:** `packages/uk-data/src/uk_data/`
- **Purpose:** Unified, source-agnostic access to UK public data (ONS, BoE, HMRC, Land Registry, Companies House API, EPC). Provides the `UKDataClient` facade, adapter protocol, concept registry, and canonical data models.
- **Key files:**
  - `packages/uk-data/src/uk_data/client.py` — `UKDataClient` facade over all adapters
  - `packages/uk-data/src/uk_data/registry.py` — `CONCEPT_REGISTRY` + `ConceptResolver`
  - `packages/uk-data/src/uk_data/adapters/` — per-source adapters (`ons.py`, `boe.py`, `hmrc.py`, `land_registry.py`, `companies_house.py`, `epc.py`, `historical.py`)
  - `packages/uk-data/src/uk_data/adapters/base.py` — `BaseAdapter` abstract protocol
  - `packages/uk-data/src/uk_data/models/` — canonical `TimeSeries`, `Entity`, `Event` models
  - `packages/uk-data/src/uk_data/_http.py` — shared HTTP utilities with in-memory cache
  - `packages/uk-data/src/uk_data/storage/` — `CanonicalStore` (optional persistence)
- **Depends on:** stdlib + external HTTP only
- **Used by:** `companies-house`, `companies-house-abm`

---

### `companies-house` — Filing Data Ingestion & Analysis Layer
- **Location:** `packages/companies-house/src/companies_house/`
- **Purpose:** Ingest, store, and analyse Companies House XBRL/PDF financial filings.
- **Key files:**
  - `packages/companies-house/src/companies_house/schema.py` — 39-column `COMPANIES_HOUSE_SCHEMA` (Polars dict) + `CompanyFiling` (Pydantic model)
  - `packages/companies-house/src/companies_house/ingest/xbrl.py` — bulk ZIP + streaming XBRL ingestion via `stream-read-xbrl`
  - `packages/companies-house/src/companies_house/ingest/pdf.py` — PDF extraction via `kreuzberg` (optional dep)
  - `packages/companies-house/src/companies_house/ingest/base.py` — `IngestSource` protocol
  - `packages/companies-house/src/companies_house/storage/db.py` — `CompaniesHouseDB` (DuckDB, composite PK upsert)
  - `packages/companies-house/src/companies_house/storage/migrations.py` — Parquet → DuckDB migration
  - `packages/companies-house/src/companies_house/analysis/reports.py` — `CompanyReport`, `analyse_company`, `generate_report`
  - `packages/companies-house/src/companies_house/analysis/benchmarks.py` — `SectorBenchmark`, peer comparison
  - `packages/companies-house/src/companies_house/analysis/forecasting.py` — `ForecastResult`, linear trend
  - `packages/companies-house/src/companies_house/cli.py` — Typer CLI (`ingest`, `search`, `filings`, `fetch`, `report`, `migrate`, `db-query`, `check-company`)
- **Depends on:** `uk-data` (workspace), `polars`, `pyarrow`, `duckdb`, `typer`, `pydantic`
- **Used by:** `companies-house-abm`

---

### `companies-house-abm` — Agent-Based Model & Calibration Layer
- **Location:** `packages/companies-house-abm/src/companies_house_abm/`
- **Purpose:** UK economy ABM calibrated from Companies House and public UK data, with simulation orchestration, firm distribution fitting, and a deprecated FastAPI webapp.
- **Sub-layers:**

  **`data_sources/` — Public Data Fetching (Legacy; partially superseded by `uk-data`)**
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/boe.py` — Bank Rate, lending rates, CET1
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/ons.py` — GDP, household income, labour, IO tables, housing
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/hmrc.py` — tax bands, NI, corporation tax, VAT
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/land_registry.py` — regional house prices
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/historical.py` — quarterly historical time-series
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/firm_distributions.py` — sector-year distribution fitting
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/calibration.py` — `calibrate_model()` → `ModelConfig`
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/companies_house.py` — SIC code bulk fetch
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/input_output.py` — ONS IO table helpers
  - `packages/companies-house-abm/src/companies_house_abm/data_sources/_http.py` — shared HTTP with in-memory cache

  **`abm/` — Simulation Core**
  - `packages/companies-house-abm/src/companies_house_abm/abm/config.py` — frozen dataclass `ModelConfig` hierarchy + `load_config()`
  - `packages/companies-house-abm/src/companies_house_abm/abm/model.py` — `Simulation` (extends `mesa.Model`), `PeriodRecord`, `SimulationResult`, `SimulationDataCollector`
  - `packages/companies-house-abm/src/companies_house_abm/abm/agents/base.py` — `BaseAgent`
  - `packages/companies-house-abm/src/companies_house_abm/abm/agents/firm.py` — `Firm` (pricing, production, employment, investment decisions)
  - `packages/companies-house-abm/src/companies_house_abm/abm/agents/household.py` — `Household`
  - `packages/companies-house-abm/src/companies_house_abm/abm/agents/bank.py` — `Bank`
  - `packages/companies-house-abm/src/companies_house_abm/abm/agents/central_bank.py` — `CentralBank` (Taylor rule)
  - `packages/companies-house-abm/src/companies_house_abm/abm/agents/government.py` — `Government` (fiscal rule)
  - `packages/companies-house-abm/src/companies_house_abm/abm/markets/base.py` — `BaseMarket` ABC (`clear()`, `get_state()`)
  - `packages/companies-house-abm/src/companies_house_abm/abm/markets/goods.py` — `GoodsMarket`
  - `packages/companies-house-abm/src/companies_house_abm/abm/markets/labor.py` — `LaborMarket`
  - `packages/companies-house-abm/src/companies_house_abm/abm/markets/credit.py` — `CreditMarket`
  - `packages/companies-house-abm/src/companies_house_abm/abm/markets/housing.py` — `HousingMarket`
  - `packages/companies-house-abm/src/companies_house_abm/abm/assets/property.py` — `Property`
  - `packages/companies-house-abm/src/companies_house_abm/abm/assets/mortgage.py` — `Mortgage`
  - `packages/companies-house-abm/src/companies_house_abm/abm/sector_model.py` — `create_sector_representative_simulation`, `SECTOR_PROFILES`
  - `packages/companies-house-abm/src/companies_house_abm/abm/historical.py` — `HistoricalSimulation`
  - `packages/companies-house-abm/src/companies_house_abm/abm/scenarios.py` — `build_uk_2013_2024`
  - `packages/companies-house-abm/src/companies_house_abm/abm/evaluation.py` — `evaluate_simulation`, `evaluate_historical`
  - `packages/companies-house-abm/src/companies_house_abm/abm/calibration.py` — ABM-level calibration helpers

  **`webapp/` — Deprecated FastAPI UI**
  - `packages/companies-house-abm/src/companies_house_abm/webapp/app.py` — FastAPI app (deprecated, static file serving)
  - `packages/companies-house-abm/src/companies_house_abm/webapp/models.py` — `SimulationParams`, `SimulationResponse`
  - `packages/companies-house-abm/src/companies_house_abm/webapp/static/` — `index.html`, `app.js`, `styles.css`

- **Depends on:** `companies-house[xbrl,analysis]` (workspace), `uk-data` (workspace), `mesa`, `numpy`, `scipy`, `polars`, `pyyaml`, `fastapi`, `uvicorn`

---

### `rust-abm` — Optional Rust Performance Extension
- **Location:** `packages/rust-abm/`
- **Purpose:** Compiled maturin extension providing `companies_house_abm._rust_abm` for performance-critical ABM loops.
- **Not a uv workspace member** — built separately via `make build-rust`.
- **Key files:**
  - `packages/rust-abm/src/` — Rust source (`agents/`, `markets/`)
  - `packages/rust-abm/python/companies_house_abm/` — Python stubs/init

---

## Data Flow

### Ingestion Pipeline

1. **Source:** Companies House bulk ZIPs (local directory or streaming URL) or REST API PDFs
2. **Parse:** `companies_house.ingest.xbrl` (XBRL → Polars DataFrame) or `companies_house.ingest.pdf` (PDF bytes → kreuzberg → LLM → `CompanyFiling`)
3. **Validate:** `CompanyFiling` Pydantic model enforces 39-column schema
4. **Store:** `CompaniesHouseDB.upsert()` (DuckDB, composite PK dedup) or `merge_and_write()` (Parquet, read-all-rewrite)
5. **Analyse:** `companies_house.analysis.reports.generate_report()` reads stored data and applies sector benchmarking + forecasting

### ABM Calibration Pipeline

1. **Fetch public data:** `data_sources/` modules or `uk_data.UKDataClient` → JSON files in `data/`
2. **Fit distributions:** `firm_distributions.run_profile_pipeline()` reads Parquet → per-sector-year distribution parameters (YAML/JSON)
3. **Calibrate config:** `data_sources/calibration.calibrate_model()` produces `ModelConfig`
4. **Load YAML:** `abm/config.load_config()` reads `config/model_parameters.yml` → frozen `ModelConfig`

### Simulation Loop (per period)

1. `Simulation.run(periods=N)` drives the Mesa model step loop
2. Each step: Government fiscal actions → Central Bank Taylor rule → Labour market clears → Goods market clears → Credit market clears → Housing market clears → firm/household state updates → `PeriodRecord` collected via `SimulationDataCollector`
3. `SimulationResult` accumulates `PeriodRecord` list + agent state snapshots
4. Output: CSV / JSON / Parquet via `run-simulation` CLI; optional evaluation against UK calibration targets via `evaluate_simulation`

---

## Key Abstractions

**`CompanyFiling` (Pydantic model):**
- Purpose: Single canonical record for one company's financial period
- Location: `packages/companies-house/src/companies_house/schema.py`
- Methods: `to_polars_row()`, `polars_schema()`, `duckdb_ddl()`

**`CompaniesHouseDB`:**
- Purpose: DuckDB storage with composite-PK upsert semantics
- Location: `packages/companies-house/src/companies_house/storage/db.py`
- Default path: `~/.companies_house/data.duckdb`; `:memory:` for tests

**`ModelConfig` (frozen dataclass hierarchy):**
- Purpose: Complete typed ABM configuration loaded from YAML
- Location: `packages/companies-house-abm/src/companies_house_abm/abm/config.py`
- Sub-configs: `SimulationConfig`, `FirmConfig`, `FirmBehaviorConfig`, `HouseholdConfig`, `BankConfig`, `TaylorRuleConfig`, `FiscalRuleConfig`, market configs
- YAML source: `config/model_parameters.yml`

**`Simulation` (extends `mesa.Model`):**
- Purpose: Top-level orchestrator owning all agents, markets, assets
- Location: `packages/companies-house-abm/src/companies_house_abm/abm/model.py`
- Factory: `Simulation.from_config(path)` or `Simulation(config)` + `initialize_agents()`

**`BaseMarket` (ABC):**
- Purpose: Interface contract for all four markets
- Location: `packages/companies-house-abm/src/companies_house_abm/abm/markets/base.py`
- Required methods: `clear(rng) → dict`, `get_state() → dict`

**`UKDataClient`:**
- Purpose: Unified facade over all public UK data adapters
- Location: `packages/uk-data/src/uk_data/client.py`
- Resolves canonical concepts (e.g. `"bank_rate"`, `"gdp"`) via `ConceptResolver` + `CONCEPT_REGISTRY`

---

## Entry Points

**CLI — `companies-house`:**
- Location: `packages/companies-house/src/companies_house/cli.py`
- Script: `companies-house` (registered in `packages/companies-house/pyproject.toml`)
- Commands: `ingest`, `check-company`, `search`, `filings`, `fetch`, `report`, `migrate`, `db-query`

**CLI — `companies_house_abm`:**
- Location: `packages/companies-house-abm/src/companies_house_abm/cli.py`
- Script: `companies_house_abm` (registered in `packages/companies-house-abm/pyproject.toml`)
- Commands: `ingest`, `check-company`, `fetch-data`, `profile-firms`, `run-simulation`, `run-sector-model`, `serve` (deprecated), `housing simulate-historical`

**FastAPI webapp (deprecated):**
- Location: `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`
- Launched via `companies_house_abm serve` (uvicorn)
- Status: Deprecated — `DeprecationWarning` raised on invocation

**Notebooks:**
- Location: `notebooks/` — Marimo interactive notebooks

---

## Error Handling

**Strategy:** Fail-fast at CLI boundary with `typer.Exit(code=N)`; library code uses standard exceptions and module-level `logging`.

**Patterns:**
- CLI commands catch exceptions, echo `err=True` messages, and exit with non-zero codes
- `CompaniesHouseDB` uses context manager (`__enter__`/`__exit__`) for connection lifecycle
- XBRL ingest logs `logger.warning` on parse errors and continues to next file
- PDF ingest (`fetch` CLI): per-filing `except Exception` continues to next filing
- Optional deps (`kreuzberg`, `stream-read-xbrl`, Rust extension) guarded by `try/except ImportError` or `TYPE_CHECKING` guards

---

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` used throughout; no centralised configuration — consumers configure handlers.

**Validation:** Pydantic `CompanyFiling` at data ingress; frozen dataclasses for config immutability; Polars schema enforcement at DataFrame construction.

**Authentication:** Companies House API key via `COMPANIES_HOUSE_API_KEY` env var or `APIConfig(api_key=...)` in `uk-data`; HTTP Basic auth (key as username, empty password).

**Configuration:** `config/model_parameters.yml` (~200+ parameters); `load_config()` falls back to dataclass defaults when file is absent. `config/sector_representative_model.yml` for sector model variant.

**State:** Simulation state is in-memory on `Simulation` object; persisted only via explicit CLI output commands (CSV/JSON/Parquet).

---

*Architecture analysis: 2026-04-26*
