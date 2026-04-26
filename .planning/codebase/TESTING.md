# Testing Patterns

**Analysis Date:** 2026-04-26

## Test Framework

**Runner:**
- pytest ≥ 9.0.0
- Config: `[tool.pytest.ini_options]` in root `pyproject.toml`

**Assertion Library:** pytest built-ins + `pytest.approx` for floats

**Coverage:** pytest-cov ≥ 7.0.0; branch coverage enabled; sources: `companies_house`, `companies_house_abm`, `uk_data`

**Run Commands:**
```bash
make test           # pytest tests/ packages/uk-data/tests/ -ra -q
make test-cov       # with --cov and HTML report
make test-matrix    # hatch matrix: Python 3.12, 3.13, 3.14
```

## Test File Organization

**Location:** Separate top-level `tests/` directory for the main monorepo suite; `packages/uk-data/tests/` for the `uk-data` package.

**Naming convention:**
- `test_<domain_or_module>.py` — e.g., `test_abm_agents.py`, `test_companies_house_storage.py`
- Integration / network tests suffixed `_integration`: `test_data_sources_integration.py`, `test_historical_integration.py`

**Fixtures directory:** `tests/fixtures/` — real XBRL files (HTML iXBRL + legacy XML) used by `test_xbrl_schema_integration.py`

**Structure:**
```
tests/
├── conftest.py                        # Session-scoped hooks + shared fixtures
├── fixtures/                          # Real XBRL test files (2 files)
├── test_abm_*.py                      # ABM agent/market/model/config/evaluation
├── test_companies_house_*.py          # Schema, storage, PDF
├── test_company_analysis.py           # Analysis reports/benchmarks/forecasting
├── test_data_sources*.py              # Data sources (offline + integration)
├── test_historical*.py                # Historical data + integration
├── test_housing_*.py                  # Housing market & data sources
├── test_ingest.py                     # XBRL ingest ETL pipeline
├── test_scenarios.py                  # ABM scenario execution
├── test_sector_model.py               # Sector model
├── test_notebook.py                   # Marimo notebook smoke test
├── test_webapp.py                     # FastAPI webapp params/config mapping
└── test_xbrl_schema_integration.py    # Real XBRL fixture → schema validation
packages/uk-data/tests/
├── conftest.py                        # HTTP cache clear + network-skip helper
├── test_client.py                     # UKDataClient unit tests (offline)
├── test_client_integration.py         # Integration (real network)
├── test_companies_house_api.py
├── test_registry.py
└── adapters/                          # Per-adapter tests (ONS, BoE, HMRC, etc.)
```

## Test Structure

**Suite organisation (class-based throughout):**
```python
class TestCompaniesHouseDB:
    def test_create_in_memory(self):
        with CompaniesHouseDB(":memory:") as db:
            assert db.row_count() == 0

    def test_upsert_idempotent(self):
        """Upserting the same row twice should not create duplicates."""
        with CompaniesHouseDB(":memory:") as db:
            db.upsert(_make_df())
            db.upsert(_make_df())
            assert db.row_count() == 1
```

**Docstrings on tests:** Short explanatory string on non-obvious assertions — e.g., `"""Upserting the same row twice should not create duplicates."""`

**Module-level helper functions:** Private `_make_<thing>()` factory functions defined at module level (not as fixtures) where data is simple and reused across multiple test methods:
```python
def _make_filing_row(**overrides):
    """Build a single filing row dict with sensible defaults."""
    row = dict.fromkeys(COMPANIES_HOUSE_SCHEMA)
    row.update({...})
    row.update(overrides)
    return row
```

## Mocking

**Framework:** `unittest.mock` — `patch`, `MagicMock`

**Patterns:**
```python
# Patch at the call site (not the definition site):
with patch("companies_house.ingest.xbrl.stream_read_xbrl_zip", return_value=iter([...])):
    result = ingest_from_zips([zip_path])

# MagicMock for complex objects:
from unittest.mock import MagicMock, patch
sim = MagicMock()
sim.run.return_value = some_result
```

**What to Mock:**
- All outbound HTTP calls (ONS, BoE, Land Registry, Companies House API) in unit tests
- `stream_read_xbrl_zip` / `stream_read_xbrl_sync` in ingest tests
- External CLI subprocess calls

**What NOT to Mock:**
- DuckDB (use `:memory:` databases instead — fast and accurate)
- Pure Python computations (HMRC tax bands, NI calculations)
- Real XBRL parsing in `test_xbrl_schema_integration.py` (uses actual fixture files)

## Fixtures and Factories

**conftest.py fixtures (session/global):**
```python
@pytest.fixture(autouse=True)
def reset_typer_force_terminal() -> Generator[None]:
    """Reset typer.rich_utils.FORCE_TERMINAL before each test."""
    ...
    yield
    ...

@pytest.fixture
def sample_data() -> dict[str, str]:
    return {"key": "value"}
```

**uk-data conftest — autouse HTTP cache clear:**
```python
@pytest.fixture(autouse=True)
def _clear_http_cache() -> Iterator[None]:
    clear_cache()
    yield
    clear_cache()
```

**In-test fixtures (class-level autouse):** Used in `test_abm_performance.py` and `test_scenarios.py` to patch global state per test class:
```python
@pytest.fixture(autouse=True)
def _patch_something(self):
    with patch(...):
        yield
```

**Fixture files location:** `tests/fixtures/` — committed real XBRL files, referenced by absolute path:
```python
FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXEL_HTML = FIXTURES_DIR / "Prod224_0012_01873499_20230131.html"
```

## Pytest Markers

Three registered markers (`--strict-markers` enforced):

| Marker | Description | Run with |
|---|---|---|
| `slow` | Long-running performance/benchmark tests | `-m slow` |
| `network` | Requires external network access | `-m network` |
| `integration` | Real network requests to external APIs | `-m integration` |

**Module-level marker application:**
```python
# Applied to every test in the module:
pytestmark = pytest.mark.integration
```

**Parametrize pattern:**
```python
@pytest.mark.parametrize(
    "fixture_file",
    [EXEL_HTML, NALDER_XML],
    ids=["html-ixbrl", "xml-legacy"],
)
def test_schema_matches_exactly(self, fixture_file: Path, tmp_path: Path):
    ...
```

## Coverage

**Requirements:** No enforced threshold; branch coverage tracked (`branch = true`)

**Coverage sources:** `companies_house`, `companies_house_abm`, `uk_data`

**Excluded lines:**
```
pragma: no cover
def __repr__
raise AssertionError
raise NotImplementedError
if __name__ == "__main__":
if TYPE_CHECKING:
@abstractmethod
```

**View coverage:**
```bash
make test-cov      # generates HTML report + terminal summary
```

## Test Types

**Unit Tests (majority):**
- Scope: single class/function in isolation
- Network: always mocked
- DB: `:memory:` DuckDB
- Location: `tests/test_*.py` (non-`_integration` files)

**Integration Tests:**
- Scope: real HTTP calls to external APIs (ONS, BoE, Companies House, Land Registry)
- Location: `tests/test_*_integration.py`, `packages/uk-data/tests/test_client_integration.py`
- Marker: `@pytest.mark.integration` or `pytestmark = pytest.mark.integration`
- Run separately: `pytest -m integration`

**Schema/Fixture Tests:**
- Scope: parse real XBRL files and assert against schema
- Location: `tests/test_xbrl_schema_integration.py`
- No special marker (run in default suite)

**Performance Tests:**
- Scope: timing and throughput benchmarks
- Location: `tests/test_abm_performance.py`
- Marker: `@pytest.mark.slow`

**E2E / Smoke:**
- `tests/test_notebook.py` — Marimo notebook import/execution smoke test
- `tests/test_webapp.py` — FastAPI parameter mapping (no HTTP server started)

## Common Patterns

**Float assertions:**
```python
assert result == pytest.approx(0.20)
assert value == pytest.approx(3_486.0)
assert rate == pytest.approx(0.45, abs=1e-6)  # tight tolerance
assert score == pytest.approx(expected, rel=0.01)  # 1% relative
```

**Error testing:**
```python
with pytest.raises(ValueError, match="not supported"):
    get_income_tax_bands("2020/21")

with pytest.raises(ValidationError):
    SimulationParams(periods=-1)
```

**Async testing:** Not used — all production async code (kreuzberg) is tested indirectly via sync wrappers.

**DuckDB in-memory pattern:**
```python
with CompaniesHouseDB(":memory:") as db:
    db.upsert(df)
    assert db.row_count() == 1
```

**CLI testing (Typer):**
```python
runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})
result = runner.invoke(app, ["ingest", "--zip-dir", str(tmp_path)])
assert result.exit_code == 0
assert "zip-dir" in result.stdout
```

---

*Testing analysis: 2026-04-26*
