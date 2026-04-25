# Coding Conventions

**Analysis Date:** Sat Apr 25 2026

## Naming Patterns

**Files:**
- Use `snake_case.py` for modules in `packages/companies-house/src/companies_house/` and `packages/companies-house-abm/src/companies_house_abm/` (examples: `schema.py`, `model.py`, `firm_distributions.py`, `test_abm_model.py`).
- Use `test_*.py` naming for tests in `tests/` (examples: `tests/test_ingest.py`, `tests/test_data_sources.py`, `tests/test_webapp.py`).

**Functions:**
- Use `snake_case` for functions and methods in implementation and tests (examples: `load_config()` in `packages/companies-house-abm/src/companies_house_abm/abm/config.py`, `search_companies()` in `packages/companies-house/src/companies_house/api/search.py`, `_mock_stream_read_xbrl_zip()` in `tests/test_ingest.py`).

**Variables:**
- Use `snake_case` for local variables and attributes (examples: `parsed_start_date` in `packages/companies-house/src/companies_house/cli.py`, `household_behavior` in `packages/companies-house-abm/src/companies_house_abm/abm/config.py`).
- Use `UPPER_SNAKE_CASE` for constants (examples: `COMPANIES_HOUSE_SCHEMA` in `packages/companies-house/src/companies_house/schema.py`, `SCENARIOS` in `tests/test_abm_performance.py`).

**Types:**
- Use `PascalCase` for dataclasses/Pydantic models/classes (examples: `APIConfig` in `packages/companies-house/src/companies_house/api/client.py`, `ModelConfig` in `packages/companies-house-abm/src/companies_house_abm/abm/config.py`, `SimulationParams` in `packages/companies-house-abm/src/companies_house_abm/webapp/models.py`).

## Code Style

**Formatting:**
- Tool used: Ruff formatter configured at `pyproject.toml` (`[tool.ruff]` and `make format`/`make format-check` in `Makefile`).
- Key settings: `line-length = 88`, `target-version = "py311"` in `pyproject.toml`.

**Linting:**
- Tool used: Ruff lint configured in `pyproject.toml` (`[tool.ruff.lint]`) and run via `make lint` in `Makefile`.
- Key rules: enabled families include `E/W/F/I/B/C4/UP/ARG/SIM/TCH/PTH/ERA/RUF` in `pyproject.toml`; test-specific ignore `ARG001` for `tests/**/*.py` in `pyproject.toml`.

## Import Organization

**Order:**
1. `__future__` imports first (examples: `from __future__ import annotations` in `packages/companies-house/src/companies_house/cli.py`, `tests/test_ingest.py`).
2. Standard library imports next (examples: `datetime`, `pathlib`, `typing` in `packages/companies-house/src/companies_house/cli.py`).
3. Third-party imports after stdlib (examples: `typer` in `packages/companies-house/src/companies_house/cli.py`, `pytest`/`polars` in `tests/test_ingest.py`).
4. First-party imports last (examples: `from companies_house...` in `packages/companies-house/src/companies_house/cli.py`, `from companies_house_abm...` in `packages/companies-house-abm/src/companies_house_abm/abm/model.py`).

**Path Aliases:**
- Not detected. Imports use package-qualified module paths rooted at `companies_house` and `companies_house_abm` (examples in `packages/companies-house/src/companies_house/storage/db.py` and `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`).

## Error Handling

**Patterns:**
- CLI commands validate inputs and terminate with explicit `typer.Exit(code=...)` in `packages/companies-house/src/companies_house/cli.py`.
- Network/client code retries transient failures and re-raises hard failures in `packages/companies-house/src/companies_house/api/client.py` and `packages/companies-house-abm/src/companies_house_abm/data_sources/_http.py`.
- Transaction-like operations wrap critical sections in `try/except/finally` with rollback/cleanup in `packages/companies-house/src/companies_house/storage/db.py`.

## Logging

**Framework:**
- Use `logging` module loggers (`logger = logging.getLogger(__name__)`) in `packages/companies-house/src/companies_house/api/client.py` and `packages/companies-house/src/companies_house/storage/db.py`.

**Patterns:**
- Prefer structured logger calls for operational events (`logger.info/warning/debug`) in `packages/companies-house/src/companies_house/api/client.py` and `packages/companies-house/src/companies_house/storage/db.py`.
- CLI user-facing output uses `typer.echo(...)` instead of logger output in `packages/companies-house/src/companies_house/cli.py`.

## Comments

**When to Comment:**
- Use block comments to explain economic/calibration rationale and non-obvious thresholds (examples in `packages/companies-house-abm/src/companies_house_abm/abm/model.py` and `packages/companies-house-abm/src/companies_house_abm/abm/config.py`).
- Use concise inline comments to clarify guards and fallback behavior (examples in `packages/companies-house/src/companies_house/api/client.py` and `packages/companies-house/src/companies_house/storage/db.py`).

**JSDoc/TSDoc:**
- Not applicable (Python codebase). Use docstrings instead in `packages/companies-house/src/companies_house/schema.py`, `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`, and tests like `tests/test_xbrl_schema_integration.py`.

## Function Design

**Size:**
- Keep functions/methods cohesive around a single concern; decompose large flows into private helpers (pattern in `packages/companies-house-abm/src/companies_house_abm/abm/model.py` with `_initial_employment()`, `_initial_housing()`, `_process_foreclosures()`).

**Parameters:**
- Use type hints throughout and keyword-only arguments where clarity matters (examples: `request(..., *, base_url, accept, raw, retries)` in `packages/companies-house/src/companies_house/api/client.py`, `run(..., periods, collect_micro)` in `packages/companies-house-abm/src/companies_house_abm/abm/model.py`).

**Return Values:**
- Return typed domain objects or data containers, not untyped tuples, for main APIs (examples: `ModelConfig` from `load_config()` in `packages/companies-house-abm/src/companies_house_abm/abm/config.py`, `pl.DataFrame` from `execute_query()` in `packages/companies-house/src/companies_house/storage/db.py`).

## Module Design

**Exports:**
- Use package module boundaries by domain (`api`, `ingest`, `storage`, `analysis`, `abm`, `data_sources`, `webapp`) as seen under `packages/companies-house/src/companies_house/` and `packages/companies-house-abm/src/companies_house_abm/`.

**Barrel Files:**
- Minimal `__init__.py` barrels are used for package markers/exports (examples: `packages/companies-house/src/companies_house/__init__.py`, `packages/companies-house-abm/src/companies_house_abm/abm/__init__.py`); most modules are imported directly by full path.

---

*Convention analysis: Sat Apr 25 2026*
