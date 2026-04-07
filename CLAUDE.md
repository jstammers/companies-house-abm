# CLAUDE.md

This file provides guidance for AI assistants working on the Companies House ABM codebase.

## Project Overview

This is a **uv workspace monorepo** following the [uv recommended workspace layout](https://docs.astral.sh/uv/concepts/projects/workspaces/).  Packages live under `packages/`, each with its own `pyproject.toml` and `src/<name>/` source tree.

1. **`companies-house`** (`packages/companies-house/`) — Standalone package for ingesting, storing, and analysing Companies House financial data. Supports XBRL (bulk ZIPs and streaming), PDF extraction (via kreuzberg), a Companies House REST API client, DuckDB storage with upsert semantics, and company financial analysis with sector benchmarking.

2. **`companies_house_abm`** (`packages/companies-house-abm/`) — Agent-Based Model of the UK economy calibrated from Companies House data. Depends on `companies-house[xbrl,analysis]`. Contains ABM agents/markets/simulation, public data fetchers (ONS/BoE/HMRC), and a FastAPI economy simulator webapp.

3. **`companies-house-abm-rust`** (`packages/rust-abm/`) — Optional Rust extension built with maturin. Outputs `companies_house_abm._rust_abm`. Not a uv workspace member; built separately via `make build-rust`.

**Status**: Alpha (v0.4.1 ABM / v0.2.1 companies-house)
**License**: MIT
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
│       ├── api/                      # Companies House REST API client
│       │   ├── client.py             # APIConfig, CompaniesHouseClient (auth, rate limiting)
│       │   ├── search.py             # Company search endpoint
│       │   ├── filings.py            # Filing history + document download
│       │   └── models.py             # Pydantic response models
│       └── analysis/                 # Company financial analysis
│           ├── reports.py            # CompanyReport, analyse_company, generate_report
│           ├── forecasting.py        # ForecastResult, linear trend extrapolation
│           ├── benchmarks.py         # SectorBenchmark, revenue-weighted peer comparison
│           └── formatting.py         # Report text generation, tables, ordinal helpers
├── companies-house-abm/              # ABM package
│   ├── pyproject.toml                # Package config (hatchling)
│   └── src/companies_house_abm/
│       ├── __init__.py               # Package version
│       ├── cli.py                    # ABM CLI: ingest, fetch-data, profile-firms, serve, check-company
│       ├── data_sources/             # Public data fetchers for ABM calibration
│       │   ├── _http.py              # Shared HTTP utilities (urllib-based, in-memory cache)
│       │   ├── boe.py                # Bank of England: Bank Rate, lending rates, CET1
│       │   ├── calibration.py        # Translate fetched data into ModelConfig parameters
│       │   ├── firm_distributions.py # Firm data profiling and distribution fitting
│       │   ├── hmrc.py               # HMRC: income tax bands, NI, corporation tax, VAT
│       │   └── ons.py                # ONS: GDP, household income, labour market, IO tables
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
├── test_companies_house_*.py         # Tests for companies_house package
├── test_ingest.py                    # XBRL ingest tests
├── test_company_analysis.py          # Analysis tests
├── test_xbrl_schema_integration.py   # Real XBRL fixture validation
├── test_abm_*.py                     # ABM agent/market/model/config tests
├── test_data_sources.py              # Data source and calibration tests
└── fixtures/                         # Real XBRL test files (HTML + XML)
config/model_parameters.yml           # ABM model parameters (200+)
docs/                                 # MkDocs documentation
notebooks/                            # Marimo interactive notebooks
scripts/
├── build_rust_abm.sh                 # Build & install Rust extension
└── run_benchmark.py                  # Python vs Rust benchmark
```

## Quick Reference Commands

```bash
make install        # Install all dependencies (uv sync --all-groups)
make verify         # Run lint + format-check + type-check (no changes)
make fix            # Auto-fix lint and formatting issues
make test           # Run tests (pytest tests/ -v)
make test-cov       # Run tests with coverage report
make type-check     # Run ty type checker
make lint           # Run ruff check
make format-check   # Check formatting with ruff
make docs           # Build documentation (mkdocs build)
make docs-serve     # Serve documentation locally
make pysentry       # Dependency vulnerability scan
make format         # Auto-format in-place (ruff format .)
make test-matrix    # Run tests across Python 3.10-3.13 (hatch)
make build-rust     # Build optional Rust ABM extension (requires cargo + maturin)
make benchmark      # Run Python vs Rust ABM performance benchmark
```

## Workspace Architecture

The monorepo uses **uv workspace** with `members = ["packages/*"]` in the root `pyproject.toml`.  The root is a virtual workspace root (`package = false`) that holds only dev/docs dependency groups and project-wide tool configuration.

Each package uses `hatchling` as its build backend and declares `packages = ["src/<name>"]` in `[tool.hatch.build.targets.wheel]`.

### Workspace Sources

`companies_house_abm` declares:
```toml
[tool.uv.sources]
companies-house = { workspace = true }
```
so `companies-house[xbrl,analysis]` resolves to the local workspace member rather than PyPI.

### Dual Schema (`schema.py`)

The 39-column Companies House schema has two representations in `companies_house/schema.py`:

| Representation | Type | Purpose |
|---|---|---|
| `COMPANIES_HOUSE_SCHEMA` | `dict[str, pl.DataType]` | Polars DataFrame construction, Parquet I/O |
| `CompanyFiling` | Pydantic `BaseModel` | LLM extraction target, API validation, DuckDB DDL |

`CompanyFiling` has methods: `to_polars_row()`, `polars_schema()`, `duckdb_ddl()`.

### Storage

- **Parquet** (legacy): Read/write via `companies_house.ingest.xbrl.merge_and_write()`. Dedup is read-all-rewrite.
- **DuckDB** (preferred): `CompaniesHouseDB` in `companies_house.storage.db`. Uses composite PK for upsert. Default path: `~/.companies_house/data.duckdb`.

### PDF Extraction Pipeline

```
PDF bytes → kreuzberg (text extraction) → structured output → CompanyFiling → DuckDB
```

- **kreuzberg**: Async PDF/image text extraction with OCR support (optional dep `companies-house[pdf]`)

### Companies House API Client

- HTTP Basic auth (API key as username, empty password)
- Rate limiting: 600 requests / 5 minutes (configurable)
- Auth via `COMPANIES_HOUSE_API_KEY` env var or `APIConfig(api_key=...)`
- Endpoints: search, filing history, document download (handles S3 redirect)

### Rust Extension (`packages/rust-abm/`)

The Rust extension is **not** a uv workspace member — it is built with maturin separately:

```bash
make build-rust          # builds release .so and copies to packages/companies-house-abm/src/companies_house_abm/
make build-rust -- --dev # debug build
```

The output `.so` (`_rust_abm.cpython-*.so`) is placed alongside the Python ABM package and is `import`-able as `companies_house_abm._rust_abm`.  Tests that require it are skipped automatically when the extension is not built.

### pyproject.toml TOML Structure Gotcha

`[tool.ty.rules]` **must** appear before `[[tool.ty.overrides]]`. Defining the
`[[...]]` array-of-tables first and then re-opening the parent table with
`[tool.ty.rules]` triggers a "duplicate key" TOML parse error in strict parsers
(uv in CI, for example). The pre-commit `check-toml` hook does **not** catch this.

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `COMPANIES_HOUSE_API_KEY` | For API commands | HTTP Basic auth username for Companies House REST API |

## Development Workflow

### 1. Initial Setup

```bash
make install        # Runs: uv sync --all-groups
uv run prek install # Install pre-commit hooks (required)
```

### 2. Before Every Commit

```bash
make fix            # Auto-fix lint and formatting
make verify         # Check lint, format, and type checks pass
make test           # Run all tests
```

### 3. Pre-commit Hooks (Required)

```bash
uv run prek install         # Install hooks
uv run prek run --all-files # Run all hooks manually
```

Do not bypass hooks with `--no-verify`.

## Code Quality Tools

| Tool | Purpose | Config |
|------|---------|--------|
| **Ruff** | Linting + formatting (line-length 88) | `[tool.ruff]` in root `pyproject.toml` |
| **ty** | Type checking (Astral) | `[tool.ty]` in root `pyproject.toml` |
| **pytest** | Testing | `[tool.pytest.ini_options]` in root `pyproject.toml` |
| **prek** | Pre-commit hooks | `.pre-commit-config.yaml` |

### Type Checking Notes

ty rule overrides for Polars stubs, optional deps, and dynamic patterns:
- `invalid-assignment`: ignored
- `invalid-argument-type`: warn
- `not-subscriptable`: ignored
- `unresolved-attribute`: warn
- `invalid-return-type`: warn
- `invalid-method-override`: warn (io.RawIOBase stub mismatch for `_TailBuffer`)
- `unresolved-import`: warn (Rust extension not built in dev by default)
- `unresolved-import` fully ignored for `packages/companies-house/src/companies_house/ingest/pdf.py` (optional deps)

## Testing Conventions

- Tests in `tests/` using pytest with class-based organisation
- `test_companies_house_*.py` — tests for the `companies_house` package (schema, storage, API, PDF)
- `test_ingest.py` — XBRL ingest tests; imports from `companies_house.ingest.xbrl` directly
- `test_company_analysis.py` — analysis tests; imports from `companies_house.analysis.*` directly
- `test_xbrl_schema_integration.py` — validates real XBRL fixtures against schema
- Mock `stream_read_xbrl_zip`/`stream_read_xbrl_sync` via `unittest.mock.patch` at `companies_house.ingest.xbrl.*`
- DuckDB tests use `:memory:` databases
- Coverage sources: `companies_house` and `companies_house_abm`

## Dependencies

### companies-house (standalone package)

| Dependency | Purpose |
|---|---|
| polars, pyarrow | DataFrame + Parquet I/O |
| duckdb | Local OLAP storage |
| typer | CLI framework |
| pydantic | Schema validation |

Optional: `stream-read-xbrl` (xbrl), `kreuzberg` (pdf), `numpy`+`scipy` (analysis)

### companies_house_abm (ABM package)

Depends on `companies-house[xbrl,analysis]` plus: mesa, networkx, numpy, scipy, matplotlib, pyyaml, marimo, fastapi, uvicorn, pydantic

### Dev

pytest, pytest-cov, ruff, ty, hatch, prek, pysentry-rs

## Git Conventions

Uses [Conventional Commits](https://www.conventionalcommits.org/): `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`, `ci`. Required for git-cliff changelog generation.

## CI Pipeline

GitHub Actions on push/PR to `main`:
1. Lint: `ruff check` + `ruff format --check`
2. Type Check: `ty check`
3. Test: pytest across Python 3.10-3.13 with coverage
4. Security: Gitleaks + pysentry-rs
5. SAST: Semgrep
