# Architecture

This is a **uv workspace monorepo** following the [uv recommended workspace
layout](https://docs.astral.sh/uv/concepts/projects/workspaces/). Packages live
under `packages/`, each with its own `pyproject.toml` and `src/<name>/` source
tree.

## Packages

1. **`companies-house`** (`packages/companies-house/`) — Standalone package for
   ingesting, storing, and analysing Companies House financial data. Supports
   XBRL (bulk ZIPs and streaming), PDF extraction (via kreuzberg), DuckDB
   storage with upsert semantics, and company financial analysis with sector
   benchmarking. Depends on `uk-data` for the Companies House REST API client.

2. **`uk-data`** (`packages/uk-data/`) — Unified UK data-loading layer. Source
   **adapters** (Companies House REST + bulk, ONS, BoE, HMRC, Land Registry,
   EPC, historical), **workflows** (high-level `fetch_*` helpers),
   **transformers**, typed **models** (`TimeSeries`, `Entity`, `Event`),
   **storage** (`RawStore`/`CanonicalStore`), and a `UKDataClient`. This is the
   single home for external data retrieval.

3. **`companies_house_abm`** (`packages/companies-house-abm/`) — Agent-Based
   Model of the UK economy calibrated from Companies House data. Depends on
   `companies-house[xbrl,analysis]` and `uk-data`. Contains the ABM
   agents/markets/simulation, calibration helpers under `data_sources/`
   (data→`ModelConfig`, firm profiling, input-output), and a FastAPI economy
   simulator webapp. Raw data retrieval lives in `uk-data`, not here.

4. **`companies-house-abm-rust`** (`packages/rust-abm/`) — Optional Rust
   extension built with maturin. Outputs `companies_house_abm._rust_abm`. Not a
   uv workspace member; built separately via `make build-rust`.

**Status**: Alpha (v0.4.1 ABM / v0.2.1 companies-house) · **License**: MIT ·
**Python**: >=3.10 (CI tests 3.10-3.13)

## Repository Structure

```
packages/
├── companies-house/                  # Standalone data package
│   ├── pyproject.toml                # Package config (hatchling)
│   └── src/companies_house/
│       ├── __init__.py               # Exports: CompanyFiling, COMPANIES_HOUSE_SCHEMA, etc.
│       ├── py.typed                  # PEP 561 marker
│       ├── schema.py                 # 39-column Polars schema + Pydantic CompanyFiling model
│       ├── cli.py                    # Typer CLI: ingest, search, filings, fetch, report, migrate, db-query
│       ├── ingest/                   # Ingestion pipelines
│       │   ├── base.py               # IngestSource protocol
│       │   ├── xbrl.py               # XBRL from ZIPs/streaming (stream-read-xbrl)
│       │   └── pdf.py                # PDF via kreuzberg text extraction (optional dep)
│       ├── storage/                  # DuckDB storage layer
│       │   ├── db.py                 # CompaniesHouseDB: upsert, query, export/import
│       │   └── migrations.py         # Parquet-to-DuckDB migration
│       └── analysis/                 # Company financial analysis
│           ├── reports.py            # CompanyReport, analyse_company, generate_report
│           ├── forecasting.py        # ForecastResult, linear trend extrapolation
│           ├── benchmarks.py         # SectorBenchmark, revenue-weighted peer comparison
│           └── formatting.py         # Report text generation, tables, ordinal helpers
├── uk-data/                          # Unified UK data-loading layer
│   ├── pyproject.toml                # Package config (hatchling)
│   └── src/uk_data/
│       ├── client.py                 # UKDataClient: source registry front door
│       ├── registry.py               # Adapter registry
│       ├── cli.py                    # Typer CLI: sources, get-series, entities, events
│       ├── adapters/                 # Source-specific fetchers (CH, ONS, BoE, HMRC, LR, EPC, historical)
│       ├── workflows/                # High-level fetch_* helpers (boe, ons)
│       ├── transformers/             # Raw → TimeSeries/Entity/Event transformers
│       ├── models/                   # Typed records: TimeSeries, Entity, Event
│       ├── storage/                  # RawStore + CanonicalStore (parquet/DuckDB)
│       ├── api/                      # Companies House REST API client
│       │   ├── client.py             # APIConfig, CompaniesHouseClient (auth, rate limiting)
│       │   ├── search.py             # Company search endpoint
│       │   ├── filings.py            # Filing history + document download
│       │   └── models.py             # Pydantic response models
│       └── utils/                    # Shared HTTP (urllib + cache) + series helpers
├── companies-house-abm/              # ABM package
│   ├── pyproject.toml                # Package config (hatchling)
│   └── src/companies_house_abm/
│       ├── __init__.py               # Package version
│       ├── cli.py                    # ABM CLI: ingest, fetch-data, profile-firms, serve, check-company
│       ├── data_sources/             # ABM calibration helpers (retrieval lives in uk-data)
│       │   ├── calibration.py        # Translate fetched data into ModelConfig parameters
│       │   ├── firm_distributions.py # Firm data profiling and distribution fitting
│       │   ├── input_output.py       # ONS input-output table → sector production relations
│       │   └── historical.py         # HistoricalAdapter: orchestrates uk_data quarterly fetchers
│       ├── webapp/                   # FastAPI economy simulator
│       │   ├── app.py                # REST API + static file serving
│       │   ├── models.py             # Pydantic request/response models
│       │   └── static/               # Frontend assets (index.html, app.js, styles.css)
│       └── abm/                      # Agent-based model
│           ├── config.py             # Frozen dataclass configuration + YAML loader
│           ├── model.py              # Simulation orchestrator
│           ├── agents/               # Firm, Household, Bank, CentralBank, Government
│           └── markets/              # Goods, Labour, Credit, Housing
└── rust-abm/                         # Rust ABM extension (maturin, not a uv member)
    ├── Cargo.toml
    ├── pyproject.toml                # maturin build config
    ├── python/                       # Python stubs / init for the extension
    └── src/                          # Rust source
tests/                                # Pytest test suite (all packages tested together)
config/model_parameters.yml           # ABM model parameters (200+)
docs/                                 # MkDocs documentation
notebooks/                            # Marimo interactive notebooks
scripts/
├── build_rust_abm.sh                 # Build & install Rust extension
└── run_benchmark.py                  # Python vs Rust benchmark
```

## Workspace Architecture

The monorepo uses **uv workspace** with `members = ["packages/*"]` in the root
`pyproject.toml`. The root is a virtual workspace root (`package = false`) that
holds only dev/docs dependency groups and project-wide tool configuration.

Each package uses `hatchling` as its build backend and declares
`packages = ["src/<name>"]` in `[tool.hatch.build.targets.wheel]`.

### Workspace Sources

`companies_house_abm` declares:

```toml
[tool.uv.sources]
companies-house = { workspace = true }
```

so `companies-house[xbrl,analysis]` resolves to the local workspace member
rather than PyPI.

## Dual Schema (`schema.py`)

The 39-column Companies House schema has two representations in
`companies_house/schema.py`:

| Representation | Type | Purpose |
|---|---|---|
| `COMPANIES_HOUSE_SCHEMA` | `dict[str, pl.DataType]` | Polars DataFrame construction, Parquet I/O |
| `CompanyFiling` | Pydantic `BaseModel` | LLM extraction target, API validation, DuckDB DDL |

`CompanyFiling` has methods: `to_polars_row()`, `polars_schema()`,
`duckdb_ddl()`.

## Storage

- **Parquet** (legacy): Read/write via
  `companies_house.ingest.xbrl.merge_and_write()`. Dedup is read-all-rewrite.
- **DuckDB** (preferred): `CompaniesHouseDB` in `companies_house.storage.db`.
  Uses composite PK for upsert. Default path: `~/.companies_house/data.duckdb`.

## PDF Extraction Pipeline

```
PDF bytes → kreuzberg (text extraction) → structured output → CompanyFiling → DuckDB
```

- **kreuzberg**: Async PDF/image text extraction with OCR support (optional dep
  `companies-house[pdf]`)

## Companies House API Client

Lives in `uk_data.api` (`from uk_data.api.client import APIConfig,
CompaniesHouseClient`). Consumed by the `companies_house` CLI's
`search`/`filings`/`fetch` commands.

- HTTP Basic auth (API key as username, empty password)
- Rate limiting: 600 requests / 5 minutes (configurable)
- Auth via `COMPANIES_HOUSE_API_KEY` env var or `APIConfig(api_key=...)`
- Endpoints: search, filing history, document download (handles S3 redirect)

## Rust Extension (`packages/rust-abm/`)

The Rust extension is **not** a uv workspace member — it is built with maturin
separately:

```bash
make build-rust          # builds release .so and copies to packages/companies-house-abm/src/companies_house_abm/
make build-rust -- --dev # debug build
```

The output `.so` (`_rust_abm.cpython-*.so`) is placed alongside the Python ABM
package and is `import`-able as `companies_house_abm._rust_abm`. Tests that
require it are skipped automatically when the extension is not built.

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `COMPANIES_HOUSE_API_KEY` | For API commands | HTTP Basic auth username for Companies House REST API |

## Dependencies

### companies-house (standalone package)

| Dependency | Purpose |
|---|---|
| polars, pyarrow | DataFrame + Parquet I/O |
| duckdb | Local OLAP storage |
| typer | CLI framework |
| pydantic | Schema validation |

Optional: `stream-read-xbrl` (xbrl), `kreuzberg` (pdf), `numpy`+`scipy`
(analysis). Depends on `uk-data` for the Companies House REST API client.

### uk-data (data-loading package)

| Dependency | Purpose |
|---|---|
| polars, pyarrow | DataFrame + Parquet I/O |
| duckdb | CanonicalStore upsert/query |
| typer | CLI framework |
| pydantic | Typed response/record models |

Retrieval uses the standard-library `urllib` (via `uk_data.utils.http`) so no
HTTP client dependency is required.

### companies_house_abm (ABM package)

Depends on `companies-house[xbrl,analysis]` and `uk-data`, plus: mesa, networkx,
numpy, scipy, matplotlib, pyyaml, marimo, fastapi, uvicorn, pydantic.

### Dev

pytest, pytest-cov, ruff, ty, hatch, prek, pysentry-rs.
