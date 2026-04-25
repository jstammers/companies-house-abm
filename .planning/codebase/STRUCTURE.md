# Codebase Structure

**Analysis Date:** 2026-04-25

## Directory Layout

```text
EarningsAI/
├── packages/                      # Workspace packages
│   ├── companies-house/           # Filing ingest/storage/api/analysis package
│   ├── companies-house-abm/       # ABM simulation + webapp package
│   └── rust-abm/                  # Optional Rust extension crate
├── tests/                         # Repository-wide pytest suite
├── config/                        # YAML model/calibration configuration
├── docs/                          # MkDocs content
├── scripts/                       # Utility scripts (benchmark, Rust build)
├── pyproject.toml                 # Workspace/tooling config
└── Makefile                       # Standard dev/test/lint targets
```

## Directory Purposes

**`packages/companies-house/src/companies_house/`:**
- Purpose: Standalone Companies House data package.
- Contains: CLI, schema, ingest, API client modules, storage, analysis.
- Key files: `packages/companies-house/src/companies_house/cli.py`, `packages/companies-house/src/companies_house/schema.py`, `packages/companies-house/src/companies_house/storage/db.py`.

**`packages/companies-house-abm/src/companies_house_abm/`:**
- Purpose: ABM package and simulator web interface.
- Contains: ABM core (`abm/`), data fetchers (`data_sources/`), FastAPI webapp (`webapp/`), CLI.
- Key files: `packages/companies-house-abm/src/companies_house_abm/cli.py`, `packages/companies-house-abm/src/companies_house_abm/abm/model.py`, `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`.

**`packages/rust-abm/`:**
- Purpose: Optional accelerated Rust extension build.
- Contains: Cargo crate, maturin project config, Rust sources.
- Key files: `packages/rust-abm/Cargo.toml`, `packages/rust-abm/src/`.

**`tests/`:**
- Purpose: Single top-level test suite for both Python packages.
- Contains: `test_companies_house_*.py`, `test_abm_*.py`, integration/performance and webapp tests.
- Key files: `tests/conftest.py`, `tests/test_abm_model.py`, `tests/test_companies_house_api.py`.

## Key File Locations

**Entry Points:**
- `packages/companies-house/src/companies_house/cli.py`: Typer entrypoint for `companies-house`.
- `packages/companies-house-abm/src/companies_house_abm/cli.py`: Typer entrypoint for `companies_house_abm`.
- `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`: FastAPI app entrypoint.

**Configuration:**
- `pyproject.toml`: uv workspace membership, lint/type/test tool configuration.
- `config/model_parameters.yml`: default ABM model parameters.
- `packages/companies-house-abm/src/companies_house_abm/abm/config.py`: YAML loader + frozen config dataclasses.

**Core Logic:**
- `packages/companies-house/src/companies_house/ingest/xbrl.py`: XBRL stream/ZIP ingest pipeline.
- `packages/companies-house/src/companies_house/storage/db.py`: DuckDB persistence and upsert.
- `packages/companies-house/src/companies_house/api/client.py`: authenticated/rate-limited API client.
- `packages/companies-house-abm/src/companies_house_abm/abm/model.py`: simulation orchestrator and period loop.

**Testing:**
- `tests/`: top-level pytest coverage for both packages.

## Naming Conventions

**Files:**
- Use `snake_case.py` for Python modules: `packages/companies-house-abm/src/companies_house_abm/data_sources/firm_distributions.py`.
- Use `test_*.py` for tests in `tests/`: `tests/test_housing_market.py`.

**Directories:**
- Package source follows `src/<import_name>/` layout: `packages/companies-house/src/companies_house/`, `packages/companies-house-abm/src/companies_house_abm/`.
- Subdirectories reflect responsibility/layer: `abm/agents/`, `abm/markets/`, `storage/`, `analysis/`, `data_sources/`, `webapp/static/`.

## Where to Add New Code

**New Feature:**
- Primary code:
  - Companies House feature: `packages/companies-house/src/companies_house/` (choose `ingest/`, `api/`, `storage/`, or `analysis/`).
  - ABM feature: `packages/companies-house-abm/src/companies_house_abm/` (choose `abm/`, `data_sources/`, or `webapp/`).
- Tests: add `tests/test_<feature>.py` in `tests/` and extend nearest existing domain test module.

**New Component/Module:**
- Implementation:
  - New agent/market: `packages/companies-house-abm/src/companies_house_abm/abm/agents/` or `.../abm/markets/`.
  - New external fetcher: `packages/companies-house-abm/src/companies_house_abm/data_sources/`.
  - New Companies House API endpoint wrapper: `packages/companies-house/src/companies_house/api/`.

**Utilities:**
- Shared helpers:
  - ABM data-source HTTP utility pattern: `packages/companies-house-abm/src/companies_house_abm/data_sources/_http.py`.
  - Package export surfaces: `packages/companies-house/src/companies_house/__init__.py` and `packages/companies-house-abm/src/companies_house_abm/abm/__init__.py`.

## Special Directories

**`.planning/codebase/`:**
- Purpose: generated codebase map artifacts for GSD planning.
- Generated: Yes.
- Committed: Yes.

**`src/build/`:**
- Purpose: build artifacts under repository root `src/`.
- Generated: Yes.
- Committed: Not applicable (treat as generated output).

**`site/`:**
- Purpose: built MkDocs static site output.
- Generated: Yes.
- Committed: Not applicable (treat as generated output).

**`dist/`:**
- Purpose: built package distributions (`.whl`, `.tar.gz`).
- Generated: Yes.
- Committed: Not applicable (treat as release artifacts).

**`packages/companies-house-abm/src/companies_house_abm/_rust_abm.cpython-313-darwin.so`:**
- Purpose: compiled Rust extension module loaded by Python.
- Generated: Yes (from `scripts/build_rust_abm.sh`).
- Committed: Not applicable (platform-specific build artifact).

---

*Structure analysis: 2026-04-25*
