# Architecture

**Analysis Date:** 2026-04-25

## Pattern Overview

**Overall:** Workspace monorepo with package-oriented layered architecture.

**Key Characteristics:**
- Two Python packages under `packages/` with clear boundaries: `packages/companies-house/src/companies_house/` and `packages/companies-house-abm/src/companies_house_abm/`.
- Inside each package, code is grouped by responsibility (CLI, domain logic, integrations, persistence, web API).
- Runtime orchestration is explicit in top-level coordinators (`packages/companies-house/src/companies_house/cli.py`, `packages/companies-house-abm/src/companies_house_abm/abm/model.py`, `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`).

## Layers

**Interface Layer (CLI + HTTP):**
- Purpose: Parse user/API input and trigger domain workflows.
- Location: `packages/companies-house/src/companies_house/cli.py`, `packages/companies-house-abm/src/companies_house_abm/cli.py`, `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`.
- Contains: Typer commands, FastAPI routes, request/response mapping.
- Depends on: domain and integration modules (e.g., `companies_house.ingest.xbrl`, `companies_house_abm.abm.model`).
- Used by: shell users and browser/API clients.

**Domain/Application Layer:**
- Purpose: Implement financial analysis and macro simulation behavior.
- Location: `packages/companies-house/src/companies_house/analysis/`, `packages/companies-house-abm/src/companies_house_abm/abm/`.
- Contains: simulation orchestrator, agents, markets, forecasting/benchmark logic.
- Depends on: config models and shared schemas.
- Used by: CLI commands and web API endpoints.

**Integration Layer:**
- Purpose: External I/O with APIs, bulk datasets, and files.
- Location: `packages/companies-house/src/companies_house/api/`, `packages/companies-house/src/companies_house/ingest/`, `packages/companies-house-abm/src/companies_house_abm/data_sources/`.
- Contains: Companies House REST client, XBRL/PDF ingest, ONS/BoE/HMRC fetchers.
- Depends on: HTTP clients, parsers, schema definitions.
- Used by: CLI commands and calibration flows.

**Persistence Layer:**
- Purpose: Store/query filing records with upsert semantics.
- Location: `packages/companies-house/src/companies_house/storage/db.py`, `packages/companies-house/src/companies_house/storage/migrations.py`.
- Contains: DuckDB table lifecycle, upsert/query/export/import, migration helpers.
- Depends on: `companies_house.schema` and DuckDB/Polars.
- Used by: ingest/fetch/migrate/db-query CLI commands.

## Data Flow

**Companies House ingestion flow:**

1. Command in `packages/companies-house/src/companies_house/cli.py` (`ingest`, `fetch`) collects options.
2. Parser/extractor runs in `packages/companies-house/src/companies_house/ingest/xbrl.py` or `packages/companies-house/src/companies_house/ingest/pdf.py`.
3. Normalized rows follow `packages/companies-house/src/companies_house/schema.py`.
4. Data is persisted via `packages/companies-house/src/companies_house/storage/db.py` (`CompaniesHouseDB.upsert`) or parquet write path in `ingest/xbrl.py`.

**ABM simulation flow:**

1. Parameters load from `config/model_parameters.yml` through `packages/companies-house-abm/src/companies_house_abm/abm/config.py`.
2. `packages/companies-house-abm/src/companies_house_abm/abm/model.py` initializes agents/markets.
3. `Simulation.step()` executes period sequence across government, central bank, banks, firms, labor/goods/credit/housing markets, and households.
4. Results are returned as `SimulationResult` / `PeriodRecord` and serialized by CLI (`packages/companies-house-abm/src/companies_house_abm/cli.py`) or API (`packages/companies-house-abm/src/companies_house_abm/webapp/app.py`).

**State Management:**
- Configuration state is immutable dataclasses in `packages/companies-house-abm/src/companies_house_abm/abm/config.py`.
- Runtime state is mutable in-memory objects owned by `Simulation` in `packages/companies-house-abm/src/companies_house_abm/abm/model.py`.
- Filing state persists in DuckDB via `packages/companies-house/src/companies_house/storage/db.py`.

## Key Abstractions

**Canonical filing schema:**
- Purpose: Single contract across ingest, storage, and analysis.
- Examples: `packages/companies-house/src/companies_house/schema.py`, `packages/companies-house/src/companies_house/ingest/xbrl.py`, `packages/companies-house/src/companies_house/storage/db.py`.
- Pattern: Shared schema/constants + typed model.

**Simulation orchestrator + pluggable markets/agents:**
- Purpose: Coordinate macroeconomic period updates.
- Examples: `packages/companies-house-abm/src/companies_house_abm/abm/model.py`, `packages/companies-house-abm/src/companies_house_abm/abm/agents/*.py`, `packages/companies-house-abm/src/companies_house_abm/abm/markets/*.py`.
- Pattern: Aggregator/orchestrator object composing specialized domain objects.

**Config translation boundary (web API):**
- Purpose: Map flat UI parameters to nested model config and back.
- Examples: `packages/companies-house-abm/src/companies_house_abm/webapp/app.py` (`_config_to_params`, `_params_to_config`), `packages/companies-house-abm/src/companies_house_abm/webapp/models.py`.
- Pattern: DTO mapping layer isolating frontend contract from internal config model.

## Entry Points

**Companies House CLI:**
- Location: `packages/companies-house/src/companies_house/cli.py`.
- Triggers: `companies-house` script (`packages/companies-house/pyproject.toml`).
- Responsibilities: ingest/search/fetch/report/migrate/db-query workflows.

**ABM CLI:**
- Location: `packages/companies-house-abm/src/companies_house_abm/cli.py`.
- Triggers: `companies_house_abm` script (`packages/companies-house-abm/pyproject.toml`).
- Responsibilities: data fetch/calibration, simulation runs, web server startup.

**Web API server:**
- Location: `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`.
- Triggers: `serve` command in `packages/companies-house-abm/src/companies_house_abm/cli.py`.
- Responsibilities: serve static UI and run `/api/defaults` + `/api/simulate`.

## Error Handling

**Strategy:** Boundary-level validation and exception handling, with typed exits for CLI and safe fallbacks for ingestion/network paths.

**Patterns:**
- CLI commands validate inputs and terminate with `typer.Exit` in `packages/companies-house/src/companies_house/cli.py` and `packages/companies-house-abm/src/companies_house_abm/cli.py`.
- Integration layers catch parse/network faults and continue or raise controlled errors in `packages/companies-house/src/companies_house/ingest/xbrl.py` and `packages/companies-house/src/companies_house/api/client.py`.

## Cross-Cutting Concerns

**Logging:** Standard `logging` module in integration/storage modules such as `packages/companies-house/src/companies_house/ingest/xbrl.py`, `packages/companies-house/src/companies_house/storage/db.py`, and `packages/companies-house/src/companies_house/api/client.py`.
**Validation:** Dataclass/Pydantic validation boundaries in `packages/companies-house-abm/src/companies_house_abm/abm/config.py`, `packages/companies-house/src/companies_house/schema.py`, and `packages/companies-house-abm/src/companies_house_abm/webapp/models.py`.
**Authentication:** API key-based Basic auth in `packages/companies-house/src/companies_house/api/client.py` via `COMPANIES_HOUSE_API_KEY`.

---

*Architecture analysis: 2026-04-25*
