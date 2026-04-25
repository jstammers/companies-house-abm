# Technology Stack

**Analysis Date:** Sat Apr 25 2026

## Languages

**Primary:**
- Python >=3.10 - Core implementation in `packages/companies-house/src/companies_house/` and `packages/companies-house-abm/src/companies_house_abm/`

**Secondary:**
- TOML - Project and package configuration in `pyproject.toml`, `packages/companies-house/pyproject.toml`, `packages/companies-house-abm/pyproject.toml`, and `packages/rust-abm/pyproject.toml`
- YAML - CI/docs config in `.github/workflows/*.yml` and `mkdocs.yml`
- Rust (edition 2021) - Optional performance extension in `packages/rust-abm/src/` with config in `packages/rust-abm/Cargo.toml`

## Runtime

**Environment:**
- Python runtime >=3.10 (`packages/companies-house/pyproject.toml`, `packages/companies-house-abm/pyproject.toml`)
- CI/dev standard runtime Python 3.13 (`.github/workflows/ci.yml`, `.github/workflows/docs.yml`)
- Container runtime uses `python:3.13-slim` (`Dockerfile`)

**Package Manager:**
- uv workspace (`pyproject.toml` `[tool.uv]` + `[tool.uv.workspace]`)
- Lockfile: present (`uv.lock`)

## Frameworks

**Core:**
- Typer >=0.12.0 - CLI apps (`packages/companies-house/src/companies_house/cli.py`, `packages/companies-house-abm/src/companies_house_abm/cli.py`)
- FastAPI >=0.115.0 - Economy simulator API/web app (`packages/companies-house-abm/src/companies_house_abm/webapp/app.py`)
- Pydantic >=2.0.0 - Data models/validation (`packages/companies-house/src/companies_house/schema.py`, `packages/companies-house-abm/src/companies_house_abm/webapp/models.py`)

**Testing:**
- pytest >=9.0.0 - Test runner (`pyproject.toml` `[dependency-groups].dev`, `[tool.pytest.ini_options]`)
- pytest-cov >=7.0.0 - Coverage reporting (`pyproject.toml` `[dependency-groups].dev`, `Makefile` `test-cov` target)

**Build/Dev:**
- Ruff >=0.14.14 - Lint + formatting (`pyproject.toml` `[tool.ruff]`)
- ty >=0.0.14 - Static type checking (`pyproject.toml` `[tool.ty.rules]`)
- Hatch >=1.16.3 - Python matrix testing (`pyproject.toml` `[tool.hatch.envs.test]`)
- MkDocs + Material - Documentation build (`mkdocs.yml`, `pyproject.toml` `[dependency-groups].docs`)
- maturin >=1.0,<2.0 - Rust extension build backend (`packages/rust-abm/pyproject.toml`)

## Key Dependencies

**Critical:**
- polars >=1.38.1 - Tabular transform and schema-backed data handling (`packages/companies-house/pyproject.toml`, `packages/companies-house/src/companies_house/storage/db.py`)
- duckdb >=1.0.0 - Primary local OLAP storage engine (`packages/companies-house/pyproject.toml`, `packages/companies-house/src/companies_house/storage/db.py`)
- pyarrow >=14.0.0 - Arrow/Parquet interoperability (`packages/companies-house/pyproject.toml`)
- mesa >=3.0.0 - ABM engine dependency (`packages/companies-house-abm/pyproject.toml`)
- numpy/scipy - Numeric modeling and calibration (`packages/companies-house-abm/pyproject.toml`, `packages/companies-house/pyproject.toml` optional `analysis`)

**Infrastructure:**
- uvicorn[standard] >=0.30.0 - ASGI serving for FastAPI app (`packages/companies-house-abm/pyproject.toml`)
- pyyaml >=6.0.0 - Model config loading (`packages/companies-house-abm/pyproject.toml`, `packages/companies-house-abm/src/companies_house_abm/abm/config.py`)
- stream-read-xbrl >=0.1.1 (optional) - XBRL ingestion (`packages/companies-house/pyproject.toml`)
- kreuzberg >=0.5.0 (optional) - PDF text extraction (`packages/companies-house/pyproject.toml`, `packages/companies-house/src/companies_house/ingest/pdf.py`)
- litellm (dynamic import) - LLM extraction bridge in PDF pipeline (`packages/companies-house/src/companies_house/ingest/pdf.py`)

## Configuration

**Environment:**
- Runtime API auth is environment-driven via `COMPANIES_HOUSE_API_KEY` (`packages/companies-house/src/companies_house/api/client.py`)
- `.env` file present for local environment configuration (`.env`)
- CI secrets are injected by GitHub Actions (e.g., `CODECOV_TOKEN` in `.github/workflows/ci.yml`)

**Build:**
- Workspace/tooling config: `pyproject.toml`
- Package builds: `packages/companies-house/pyproject.toml`, `packages/companies-house-abm/pyproject.toml`, `packages/rust-abm/pyproject.toml`
- Container image: `Dockerfile`
- Rust extension profile/deps: `packages/rust-abm/Cargo.toml`
- Automation commands: `Makefile`

## Platform Requirements

**Development:**
- Python >=3.10 and uv (`README.md`, `pyproject.toml`)
- Optional Rust toolchain + maturin for extension builds (`packages/rust-abm/pyproject.toml`, `Makefile` `build-rust`)

**Production:**
- CLI/service execution on Python 3.13-compatible environment (`Dockerfile`)
- Optional ASGI hosting through Uvicorn/FastAPI path (`packages/companies-house-abm/src/companies_house_abm/webapp/app.py`)

---

*Stack analysis: Sat Apr 25 2026*
