# CLAUDE.md

This file provides guidance for AI assistants working on the Companies House ABM codebase.

## Project Overview

Companies House ABM is a Python library and CLI tool for ingesting and processing financial data from Companies House XBRL accounts. It transforms XBRL data into Parquet format using Polars for downstream agent-based modelling.

**Status**: Alpha (v0.1.0)
**License**: MIT
**Python**: >=3.13 (CI tests 3.10–3.13)

## Repository Structure

```
src/companies_house_abm/     # Production code (~300 lines)
├── __init__.py               # Package version
├── cli.py                    # Typer CLI (ingest, hello, --version)
└── ingest.py                 # ETL pipeline: schema, dedup, zip/stream ingest, merge
tests/                        # Pytest test suite
├── conftest.py               # Shared fixtures
├── test_companies_house_abm.py  # CLI/version tests
└── test_ingest.py            # Ingest module tests (class-based, ~380 lines)
docs/                         # MkDocs documentation
scripts/                      # Utility scripts (download, extract, import)
notebooks/                    # Jupyter analysis notebooks
conf/                         # Kedro-style config (base/local)
.github/workflows/            # CI, docs deployment, release
```

## Quick Reference Commands

All commands use `uv` as the package manager and are defined in the `Makefile`:

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
```

## Development Workflow

### Before committing, always run:

```bash
make verify   # Ensures lint, format, and type checks pass
make test     # Ensures tests pass
```

### Fixing issues:

```bash
make fix      # Auto-fix lint and format problems
```

## Code Quality Tools

| Tool | Purpose | Config location |
|------|---------|-----------------|
| **Ruff** | Linting and formatting | `[tool.ruff]` in `pyproject.toml` |
| **ty** | Type checking (Astral) | `[tool.ty]` in `pyproject.toml` |
| **pytest** | Testing | `[tool.pytest.ini_options]` in `pyproject.toml` |
| **pytest-cov** | Coverage | `[tool.coverage]` in `pyproject.toml` |
| **prek** | Pre-commit hooks | `.pre-commit-config.yaml` |

### Ruff Rules

Line length is 88. Selected rule sets: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `ARG`, `SIM`, `TCH`, `PTH`, `ERA`, `RUF`. The `ARG001` rule (unused arguments) is ignored in test files.

### Type Checking Notes

ty has specific rule overrides due to Polars stubs:
- `invalid-assignment`: ignored
- `not-subscriptable`: ignored
- `unresolved-attribute`: warn only

## Testing Conventions

- Tests live in `tests/` and use pytest.
- Test classes are organized by function/module (e.g., `TestSchema`, `TestDeduplicate`, `TestIngestFromZips`).
- Helper factories `_make_row()` and `_make_df()` in `test_ingest.py` create test data with sensible defaults.
- External dependencies (`stream_read_xbrl_zip`, `stream_read_xbrl_sync`) are mocked using `unittest.mock`.
- Mark slow tests with `@pytest.mark.slow` (deselect with `-m "not slow"`).
- Coverage source is `src/companies_house_abm` with branch coverage enabled.

## Architecture Notes

### Key modules

- **`cli.py`**: Typer-based CLI. The `ingest` command supports two modes: local ZIP processing (`--zip-dir`) and streaming from the Companies House API (default). Lazy-imports ingest functions to keep CLI startup fast.
- **`ingest.py`**: Core ETL logic. `COMPANIES_HOUSE_SCHEMA` defines 39 columns with Polars types. Financial fields use `Decimal(20, 2)`. Deduplication uses `company_id`, `balance_sheet_date`, `period_start`, `period_end` as composite key. Data is always written as Parquet.

### Data flow

1. Data sourced from ZIP files or streamed from Companies House API
2. Raw XBRL parsed via `stream-read-xbrl` into row-oriented data
3. Rows cast to a strict Polars schema
4. New data merged with existing Parquet file (if present)
5. Deduplicated (keep last occurrence)
6. Written to output Parquet file

## CI Pipeline

GitHub Actions runs on push/PR to `main`:

1. **Lint**: `ruff check` + `ruff format --check`
2. **Type Check**: `ty check`
3. **Test**: pytest with coverage across Python 3.10–3.13, uploaded to Codecov
4. **Security**: Gitleaks (secret detection) + pysentry-rs (dependency scan)
5. **SAST**: Semgrep static analysis

## Git Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/). All commit messages **must** follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit types

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `refactor` | Code refactoring (no behavior change) |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks, dependency updates |
| `perf` | Performance improvements |
| `style` | Code style changes (formatting, no logic change) |
| `ci` | CI/CD configuration changes |

### Examples

```
feat: add export to CSV format
fix: handle empty XBRL responses gracefully
docs: update API reference for ingest module
test: add edge case coverage for deduplication
refactor: extract schema validation into helper
chore: update polars to v1.40
```

Conventional commits are required because the project uses **git-cliff** (`cliff.toml`) for automated changelog generation. Non-conventional commits are filtered out.

## Dependencies

### Core

- **polars** (>=1.38.1): DataFrame processing and Parquet I/O
- **stream-read-xbrl** (>=0.1.1): XBRL data streaming/parsing
- **typer** (>=0.12.0): CLI framework

### Build

- **hatchling**: Build backend
- **uv**: Package manager (with lockfile `uv.lock`)
