# Coding Conventions

**Analysis Date:** 2026-04-26

## Naming Patterns

**Files:**
- `snake_case.py` throughout — e.g., `firm_distributions.py`, `storage/db.py`
- Private helpers prefixed with `_`: `_make_row`, `_find_default_parquet`, `_PL_COLS`
- Test files: `test_<module_or_domain>.py` — e.g., `test_abm_agents.py`, `test_companies_house_storage.py`

**Classes:**
- `PascalCase` — e.g., `CompaniesHouseDB`, `CompanyFiling`, `SimulationResult`, `BaseAgent`
- Test classes: `Test<Subject>` — e.g., `TestFirm`, `TestPolarsSchema`, `TestCompaniesHouseDB`

**Functions/Methods:**
- `snake_case` — e.g., `ingest_from_zips`, `compute_income_tax`, `build_peer_group`
- Private helpers: `_snake_case` prefix — e.g., `_ensure_schema`, `_make_filing_row`, `_load_sic_sector_ids`

**Variables/Constants:**
- Module constants: `UPPER_SNAKE_CASE` — e.g., `COMPANIES_HOUSE_SCHEMA`, `DEDUP_COLUMNS`, `SIC_TO_SECTOR`
- Module-level loggers: `logger = logging.getLogger(__name__)` (never `LOG` or `LOGGER`)
- Private column lists: `_UPPER_SNAKE_CASE` — e.g., `_PL_COLS`, `_BS_COLS`

**Type Annotations:**
- `from __future__ import annotations` in every source and test file (81 occurrences in packages, 27 in tests)
- Runtime-only imports inside `if TYPE_CHECKING:` blocks (33 occurrences in packages)
- Full return type annotations on all public methods; `-> None` explicit on `__init__`

## Code Style

**Formatting:**
- Tool: **Ruff** (`ruff format`)
- Line length: **88** characters
- Config: `[tool.ruff]` in root `pyproject.toml`

**Linting:**
- Tool: **Ruff** with rule sets: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `ARG`, `SIM`, `TCH`, `PTH`, `ERA`, `RUF`
- Per-file ignores:
  - `tests/**/*.py` → `ARG001` (unused fixture args in test params)
  - `packages/companies-house/src/companies_house/schema.py` → `TCH003`
  - `packages/companies-house/src/companies_house/api/models.py` → `TCH003`
  - `notebooks/**/*.py` → `B018`, `E501`

**Type checker:** **ty** (Astral) — see `[tool.ty.rules]` in root `pyproject.toml`

## Import Organization

**Order (enforced by Ruff/isort):**
1. Standard library imports
2. Third-party imports
3. First-party imports (`companies_house`, `companies_house_abm`, `uk_data`)

**Deferred imports:**
- `if TYPE_CHECKING:` guards placed after all runtime imports for heavy/circular types
- Example from `packages/companies-house/src/companies_house/ingest/xbrl.py`:
  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from pathlib import Path
  ```

**Path aliases:** `known-first-party = ["companies_house_abm", "companies_house", "uk_data"]`

## Canonical Module-Level Structure

1. Module docstring
2. `from __future__ import annotations`
3. Standard library imports
4. Third-party imports
5. First-party imports (TYPE_CHECKING-guarded for heavy types)
6. `logger = logging.getLogger(__name__)`
7. Private constants (`_UPPER_SNAKE_CASE`)
8. Private helper functions (`_snake_case`)
9. Public classes and functions

## Docstrings

**Format:** NumPy-style with `----------` separators for public API; single-line summary for private helpers.

**Placement:** Module docstring on line 1 of every `.py` file; class docstring immediately after `class`; method docstring after `def`.

**Example (from `packages/companies-house/src/companies_house/storage/db.py`):**
```python
def upsert(self, df: pl.DataFrame) -> int:
    """Insert or update rows from a Polars DataFrame.

    Parameters
    ----------
    df:
        DataFrame conforming to ``COMPANIES_HOUSE_SCHEMA``.

    Returns
    -------
    int
        Number of rows upserted.
    """
```

## Error Handling

- Use `msg = "..."` then `raise SomeError(msg)` (consistent pattern codebase-wide)
- `ValueError` for invalid arguments (e.g., unsupported tax year in HMRC functions)
- Context managers (`with ... as db`) for DuckDB connections and resource management
- Optional dependencies: `try/except ImportError` at module level; caller gets a clear `ImportError` at call-site

## Logging

**Framework:** stdlib `logging`

**Pattern:**
```python
logger = logging.getLogger(__name__)  # module-level, every file that logs
logger.debug("Ensured filings table exists")  # diagnostic tracing
```
- `logger.debug` for tracing/diagnostic; `logger.info` for significant state changes
- No f-strings in log calls; use `%`-style lazy formatting

## Data Modelling (Three Patterns)

| Pattern | Use Case | Example |
|---|---|---|
| `@dataclass(frozen=True)` | Immutable value objects, config structs | `HmrcBand`, `NationalInsurance`, `ScenarioConfig` |
| Pydantic `BaseModel` | API responses, LLM extraction, validation | `CompanyFiling`, `SimulationParams`, `Filing` |
| `@dataclass` (mutable) | Registry, client config | `APIConfig`, `DataSource` |

**Pydantic config idiom:**
```python
model_config = ConfigDict(populate_by_name=True, extra="forbid")
```

## Function / Module Design

**Parameters:** Keyword-only args (`*`) used for optional modifier parameters on agent `__init__`:
```python
def __init__(self, agent_id: str | None = None, *, sector: str = "other_services", employees: int = 0) -> None:
```

**Exports / Barrel files:** `__init__.py` re-exports public surface; internal helpers stay in sub-modules.

**Wildcard adapter shims:** `data_sources/*.py` files re-export from `uk_data.adapters.*` with `# noqa: F403`:
```python
# packages/companies-house-abm/src/companies_house_abm/data_sources/ons.py
from uk_data.adapters.ons import *  # noqa: F403
```

---

*Convention analysis: 2026-04-26*
