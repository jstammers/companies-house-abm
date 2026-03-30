# CLAUDE.md

This file provides guidance for AI assistants working on the Companies House ABM codebase.

## Project Overview

This is a **uv workspace monorepo** containing two Python packages:

1. **`companies-house`** — Standalone package for ingesting, storing, and analysing Companies House financial data. Supports XBRL (bulk ZIPs and streaming), PDF extraction (via kreuzberg + litellm), a Companies House REST API client, DuckDB storage with upsert semantics, and company financial analysis with sector benchmarking.

2. **`companies_house_abm`** — Agent-Based Model of the UK economy calibrated from Companies House data. Depends on `companies-house[xbrl,analysis]`. Contains ABM agents/markets/simulation, public data fetchers (ONS/BoE/HMRC), and a FastAPI economy simulator webapp.

**Status**: Alpha (v0.4.0 ABM / v0.2.0 companies-house)
**License**: MIT
**Python**: >=3.10 (CI tests 3.10-3.13)

## Repository Structure

```
src/
├── companies_house/              # Standalone data package (can be split to own repo)
│   ├── pyproject.toml            # Independent package config
│   ├── __init__.py               # Exports: CompanyFiling, COMPANIES_HOUSE_SCHEMA, etc.
│   ├── py.typed                  # PEP 561 marker
│   ├── schema.py                 # 39-column Polars schema + Pydantic CompanyFiling model
│   ├── cli.py                    # Typer CLI: ingest, search, filings, fetch, report, migrate, db-query
│   ├── ingest/                   # Ingestion pipelines
│   │   ├── base.py               # IngestSource protocol
│   │   ├── xbrl.py               # XBRL from ZIPs/streaming (stream-read-xbrl)
│   │   └── pdf.py                # PDF via kreuzberg text extraction + litellm structured output
│   ├── storage/                  # DuckDB storage layer
│   │   ├── db.py                 # CompaniesHouseDB: upsert, query, export/import
│   │   └── migrations.py         # Parquet-to-DuckDB migration
│   ├── api/                      # Companies House REST API client
│   │   ├── client.py             # APIConfig, CompaniesHouseClient (auth, rate limiting)
│   │   ├── search.py             # Company search endpoint
│   │   ├── filings.py            # Filing history + document download
│   │   └── models.py             # Pydantic response models
│   └── analysis/                 # Company financial analysis
│       ├── reports.py            # CompanyReport, analyse_company, generate_report
│       ├── forecasting.py        # ForecastResult, linear trend extrapolation
│       ├── benchmarks.py         # SectorBenchmark, revenue-weighted peer comparison
│       └── formatting.py         # Report text generation, tables, ordinal helpers
├── companies_house_abm/          # ABM package
│   ├── __init__.py               # Package version
│   ├── cli.py                    # ABM CLI: ingest, fetch-data, profile-firms, serve, check-company
│   ├── ingest.py                 # Backward-compat wrapper → companies_house.ingest.xbrl
│   ├── company_analysis.py       # Backward-compat wrapper → companies_house.analysis
│   ├── data_sources/             # Public data fetchers for ABM calibration
│   │   ├── _http.py              # Shared HTTP utilities (urllib-based, in-memory cache)
│   │   ├── boe.py                # Bank of England: Bank Rate, lending rates, CET1
│   │   ├── calibration.py        # Translate fetched data into ModelConfig parameters
│   │   ├── firm_distributions.py # Firm data profiling and distribution fitting
│   │   ├── hmrc.py               # HMRC: income tax bands, NI, corporation tax, VAT
│   │   └── ons.py                # ONS: GDP, household income, labour market, IO tables
│   ├── webapp/                   # FastAPI economy simulator
│   │   ├── app.py                # REST API + static file serving
│   │   ├── models.py             # Pydantic request/response models
│   │   └── static/               # Frontend assets (index.html, app.js, styles.css)
│   └── abm/                      # Agent-based model
│       ├── config.py             # Frozen dataclass configuration + YAML loader
│       ├── model.py              # Simulation orchestrator
│       ├── agents/               # Firm, Household, Bank, CentralBank, Government
│       └── markets/              # Goods, Labour, Credit
tests/                            # Pytest test suite
├── test_companies_house_*.py     # Tests for companies_house package (schema, storage, API, PDF)
├── test_ingest.py                # XBRL ingest tests (backward-compat imports)
├── test_company_analysis.py      # Analysis tests (backward-compat imports)
├── test_xbrl_schema_integration.py # Real XBRL fixture validation
├── test_abm_*.py                 # ABM agent/market/model/config tests
├── test_data_sources.py          # Data source and calibration tests
└── fixtures/                     # Real XBRL test files (HTML + XML)
config/model_parameters.yml       # ABM model parameters (200+)
docs/                             # MkDocs documentation
notebooks/                        # Marimo interactive notebooks
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

The monorepo uses **uv workspace** (`[tool.uv.workspace]` in root `pyproject.toml`) with `src/companies_house` as a workspace member. The ABM package depends on `companies-house[xbrl,analysis]` via a workspace source reference.

### Dual Schema (`schema.py`)

The 39-column Companies House schema has two representations in `companies_house/schema.py`:

| Representation | Type | Purpose |
|---|---|---|
| `COMPANIES_HOUSE_SCHEMA` | `dict[str, pl.DataType]` | Polars DataFrame construction, Parquet I/O |
| `CompanyFiling` | Pydantic `BaseModel` | LLM extraction target, API validation, DuckDB DDL |

`CompanyFiling` has methods: `to_polars_row()`, `polars_schema()`, `duckdb_ddl()`.

### Storage

- **Parquet** (legacy): Read/write via `ingest.xbrl.merge_and_write()`. Dedup is read-all-rewrite.
- **DuckDB** (preferred): `CompaniesHouseDB` in `storage/db.py`. Uses composite PK for upsert. Default path: `~/.companies_house/data.duckdb`.

### PDF Extraction Pipeline

```
PDF bytes → kreuzberg (text extraction) → litellm (structured output) → CompanyFiling → DuckDB
```

- **kreuzberg**: Async PDF/image text extraction with OCR support
- **litellm**: Unified LLM provider (Anthropic, OpenAI, Ollama, etc.)
- Both are optional dependencies: `companies-house[pdf]` and `companies-house[llm]`

### Companies House API Client

- HTTP Basic auth (API key as username, empty password)
- Rate limiting: 600 requests / 5 minutes (configurable)
- Auth via `COMPANIES_HOUSE_API_KEY` env var or `APIConfig(api_key=...)`
- Endpoints: search, filing history, document download (handles S3 redirect)

### Backward Compatibility

`companies_house_abm.ingest` and `companies_house_abm.company_analysis` are thin re-export wrappers. All existing imports continue to work. New code should import from `companies_house` directly.

When patching in tests, target the actual module: `companies_house.ingest.xbrl.stream_read_xbrl_zip` (not the wrapper).

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
| **Ruff** | Linting + formatting (line-length 88) | `[tool.ruff]` in `pyproject.toml` |
| **ty** | Type checking (Astral) | `[tool.ty]` in `pyproject.toml` |
| **pytest** | Testing | `[tool.pytest.ini_options]` in `pyproject.toml` |
| **prek** | Pre-commit hooks | `.pre-commit-config.yaml` |

### Type Checking Notes

ty rule overrides for Polars stubs, optional deps, and dynamic patterns:
- `invalid-assignment`: ignored
- `invalid-argument-type`: warn
- `not-subscriptable`: ignored
- `unresolved-attribute`: warn
- `invalid-return-type`: warn
- `unresolved-import` ignored for `src/companies_house/ingest/pdf.py` (optional deps)

## Testing Conventions

- Tests in `tests/` using pytest with class-based organisation
- `test_companies_house_*.py` — tests for the standalone package (schema, storage, API, PDF)
- `test_ingest.py`, `test_company_analysis.py` — test via backward-compat wrappers
- `test_xbrl_schema_integration.py` — validates real XBRL fixtures against schema
- Mock `stream_read_xbrl_zip`/`stream_read_xbrl_sync` via `unittest.mock.patch` at `companies_house.ingest.xbrl.*`
- DuckDB tests use `:memory:` databases
- Coverage source: `src/companies_house_abm` and `src/companies_house`

## Dependencies

### companies-house (standalone package)

| Dependency | Purpose |
|---|---|
| polars, pyarrow | DataFrame + Parquet I/O |
| duckdb | Local OLAP storage |
| typer | CLI framework |
| pydantic | Schema validation |

Optional: `stream-read-xbrl` (xbrl), `kreuzberg` (pdf), `litellm` (llm), `numpy`+`scipy` (analysis)

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
