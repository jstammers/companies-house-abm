# Technology Stack

**Analysis Date:** 2026-04-26

## Languages

**Primary:**
- Python >=3.10 — all application code across all packages

**Secondary:**
- Rust (2021 edition) — optional high-performance ABM extension (`packages/rust-abm/`)
- YAML — ABM model configuration (`config/model_parameters.yml`, `config/sector_representative_model.yml`)
- HTML/CSS/JS — static frontend for deprecated FastAPI webapp (`packages/companies-house-abm/src/companies_house_abm/webapp/static/`)

## Runtime

**Environment:**
- CPython >=3.10 (CI matrix: 3.12, 3.13, 3.14)
- Container: `python:3.13-slim` (`Dockerfile`)

**Package Manager:**
- uv (Astral) — workspace-aware, lockfile-based
- Lockfile: `uv.lock` present and committed

## Workspace Layout

uv monorepo — root is a virtual package (`package = false`):

| Package | Version | Path |
|---|---|---|
| `companies-house` | 0.2.1 | `packages/companies-house/` |
| `companies_house_abm` | 0.4.1 | `packages/companies-house-abm/` |
| `uk-data` | 0.1.0 | `packages/uk-data/` |
| `companies_house_abm_rust` | 0.1.0 | `packages/rust-abm/` (not a uv member; maturin build) |

Build backend for all Python packages: **hatchling**

## Frameworks

**Core:**
- `polars >=1.38.1` — primary DataFrame/Parquet I/O across all packages
- `pydantic >=2.0.0` — schema validation, API models, LLM extraction targets
- `duckdb >=1.0.0` — local OLAP storage for filings and UK data
- `fastapi >=0.115.0` — deprecated economy simulator webapp (`packages/companies-house-abm/src/companies_house_abm/webapp/app.py`)
- `uvicorn[standard] >=0.30.0` — ASGI server for FastAPI app
- `mesa >=3.0.0` — agent-based modelling framework
- `typer >=0.12.0` — CLI for `companies-house`, `companies_house_abm`, and `uk-data` (`ukd`)
- `marimo >=0.10.0` — interactive notebooks (runtime dep in `companies-house`)

**Simulation / Science:**
- `numpy >=1.26.0` — numerical computation
- `scipy >=1.11.0` — statistical distribution fitting for ABM calibration
- `networkx >=3.2` — graph structures for agent relationships
- `matplotlib >=3.8.0` — simulation output plots
- `pyzmq >=27.1.0` — ZeroMQ bindings (Mesa server comms)
- `pyyaml >=6.0.0` — model config loading in `companies_house_abm`

**Rust Extension:**
- `pyo3 >=0.23` — Python↔Rust bindings
- `krabmaga 0.5.3` — Rust ABM framework (no default features)
- `rand 0.8`, `rand_distr 0.4` — random number generation in Rust

## Optional Dependencies

| Extra | Package | Dep |
|---|---|---|
| `xbrl` | `companies-house` | `stream-read-xbrl >=0.1.1` |
| `pdf` | `companies-house` | `kreuzberg >=0.5.0` |
| `analysis` | `companies-house` | `numpy >=1.26.0`, `scipy >=1.11.0` |
| `sdmx` | `uk-data` | `pandasdmx >=1.6.0,<2` |

## Testing

- `pytest >=9.0.0` — test runner; config in root `pyproject.toml`
- `pytest-cov >=7.0.0` — branch coverage; sources: `companies_house`, `companies_house_abm`, `uk_data`
- Hatch matrix: Python 3.12, 3.13, 3.14 via `make test-matrix`
- Coverage upload: Codecov via `CODECOV_TOKEN` secret

## Build / Dev Tools

| Tool | Purpose | Config |
|---|---|---|
| `ruff >=0.14.14` | Lint + format (line-length 88) | `[tool.ruff]` in root `pyproject.toml` |
| `ty >=0.0.14` | Type checking (Astral) | `[tool.ty]` in root `pyproject.toml` |
| `hatch >=1.16.3` | Cross-Python matrix testing | `[tool.hatch.envs.test]` |
| `prek >=0.1.0` | Pre-commit hook runner | `.pre-commit-config.yaml` |
| `pysentry-rs >=0.1.0` | Dependency vulnerability scan | `make pysentry` |
| `maturin >=1.0,<2.0` | Rust extension build | `packages/rust-abm/pyproject.toml` |
| `mkdocs >=1.6.0` + `mkdocs-material >=9.7.0` | Documentation | `mkdocs.yml`, `[dependency-groups.docs]` |
| `git-cliff` | Changelog generation (Conventional Commits) | `cliff.toml` |

## Configuration

**Environment:**
- `.env` file present (contents not read)
- Key env var: `COMPANIES_HOUSE_API_KEY` — HTTP Basic auth for Companies House REST API
- Key env vars: `EPC_API_USER`, `EPC_API_PASS` — EPC Open Data Communities API (`packages/uk-data/src/uk_data/adapters/epc.py`)

**Build:**
- Root config: `pyproject.toml` (workspace, tooling, dev/docs groups)
- Package configs: `packages/*/pyproject.toml`
- Container: `Dockerfile`
- Rust: `packages/rust-abm/Cargo.toml`
- Automation: `Makefile`

## Platform Requirements

**Development:**
- Python >=3.10, uv
- Cargo + maturin (only for Rust extension)
- Pre-commit hooks: `uv run prek install`

**Production:**
- Docker multi-stage build (Python 3.13-slim)
- Entrypoint: `companies_house_abm` CLI
- Default DuckDB storage: `~/.companies_house/data.duckdb`

---

*Stack analysis: 2026-04-26*
