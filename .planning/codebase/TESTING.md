# Testing Patterns

**Analysis Date:** Sat Apr 25 2026

## Test Framework

**Runner:**
- `pytest` (configured in `pyproject.toml` under `[tool.pytest.ini_options]`)
- Config: `pyproject.toml`

**Assertion Library:**
- Built-in `assert` statements with `pytest` helpers (`pytest.raises`, `pytest.approx`, fixtures) across `tests/*.py`.

**Run Commands:**
```bash
make test              # Run all tests (uv run pytest tests/ -v)
uv run pytest -q       # Quiet run using repo defaults
make test-cov          # Coverage run
```

## Test File Organization

**Location:**
- Separate top-level `tests/` directory, not co-located with source (`pyproject.toml` sets `testpaths = ["tests"]`).

**Naming:**
- Test modules use `test_*.py` (examples: `tests/test_ingest.py`, `tests/test_abm_model.py`, `tests/test_xbrl_schema_integration.py`).
- Tests are grouped into classes by feature area (examples: `TestCLIIngest` in `tests/test_ingest.py`, `TestSimulationStep` in `tests/test_abm_model.py`).

**Structure:**
```
tests/
├── conftest.py
├── test_companies_house_*.py
├── test_abm_*.py
├── test_data_sources.py
├── test_webapp.py
└── fixtures/
```

## Test Structure

**Suite Organization:**
```python
class TestSimulationStep:
    def _make_sim(self, n_firms: int = 10, n_hh: int = 20) -> Simulation:
        ...

    def test_single_step(self):
        sim = self._make_sim()
        record = sim.step()
        assert isinstance(record, PeriodRecord)
```
Pattern source: `tests/test_abm_model.py`.

**Patterns:**
- Setup pattern: class-local builders/helpers (for example `_make_sim()` in `tests/test_abm_model.py`, `_make_row()` in `tests/test_ingest.py`).
- Teardown pattern: context managers and fixture-managed cleanup (`tmp_path`, `with patch(...)`, custom context managers in `tests/test_ingest.py`).
- Assertion pattern: direct asserts with domain checks and approximate numeric comparisons (`pytest.approx`) in `tests/test_data_sources.py` and `tests/test_webapp.py`.

## Mocking

**Framework:**
- `unittest.mock` (`patch`, `MagicMock`) with `pytest` fixtures.

**Patterns:**
```python
with patch("urllib.request.urlopen", return_value=mock_response):
    result = client.request("/test")
    assert result == {"items": [], "total_results": 0}
```
From `tests/test_companies_house_api.py`.

```python
with (
    patch("companies_house_abm.data_sources.ons.retry", side_effect=Exception("api down")),
    patch("companies_house_abm.data_sources.boe.retry", side_effect=Exception("api down")),
):
    cfg = calibrate_model()
```
From `tests/test_data_sources.py`.

**What to Mock:**
- External HTTP/network boundaries (`urllib.request.urlopen`, `...data_sources.*.retry`) in `tests/test_companies_house_api.py` and `tests/test_data_sources.py`.
- Third-party parser/streaming boundaries (`companies_house.ingest.xbrl.stream_read_xbrl_zip` and `stream_read_xbrl_sync`) in `tests/test_ingest.py`.

**What NOT to Mock:**
- Core domain logic and state transitions: run `Simulation` methods directly in `tests/test_abm_model.py` and validate output records.
- Real schema integration path from fixture XBRL through ingest and parquet roundtrip in `tests/test_xbrl_schema_integration.py`.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture(autouse=True)
def reset_typer_force_terminal() -> Generator[None]:
    ru = sys.modules.get("typer.rich_utils")
    ...
```
From `tests/conftest.py` (global CLI color-state reset).

```python
def _make_row(**overrides: object) -> tuple:
    defaults = {...}
    defaults.update(overrides)
    return tuple(defaults[col] for col in _COLUMNS)
```
From `tests/test_ingest.py` (schema-aligned test row factory).

**Location:**
- Shared fixtures in `tests/conftest.py`.
- Module-scoped factories/helpers in each test file (examples: `tests/test_ingest.py`, `tests/test_xbrl_schema_integration.py`).
- Real data fixtures in `tests/fixtures/` used by `tests/test_xbrl_schema_integration.py`.

## Coverage

**Requirements:**
- No explicit percentage threshold enforced in `pyproject.toml`.
- Coverage source scope is enforced: `companies_house` and `companies_house_abm` in `[tool.coverage.run]`.

**View Coverage:**
```bash
make test-cov
uv run pytest --cov --cov-report=term-missing --cov-report=xml
```

## Test Types

**Unit Tests:**
- Dominant pattern. Validate pure logic and small modules (examples: `tests/test_companies_house_api.py`, `tests/test_data_sources.py`, `tests/test_webapp.py`).

**Integration Tests:**
- Present for parser/schema/dataflow integration with real fixtures in `tests/test_xbrl_schema_integration.py`.
- Present for multi-component ABM progression in `tests/test_abm_model.py` (initialization + stepping + aggregated outputs).

**E2E Tests:**
- No browser/UI E2E framework detected (no Playwright/Cypress/Selenium configs).
- CLI-level integration tests exist via Typer `CliRunner` in `tests/test_ingest.py` and `tests/test_data_sources.py` (`fetch-data --help`, ingest flows).

## Common Patterns

**Async Testing:**
```python
# Not detected: no pytest-asyncio markers or async test functions in tests/*.py
```

**Error Testing:**
```python
with pytest.raises(ValueError, match="not supported"):
    get_income_tax_bands("2020/21")
```
From `tests/test_data_sources.py`.

```python
with pytest.raises(RuntimeError, match=r"All .* attempts failed"):
    retry(always_fails, retries=2, backoff=0.001)
```
From `tests/test_data_sources.py`.

Additional marker usage:
- Slow performance tests are explicitly marked with `@pytest.mark.slow` in `tests/test_abm_performance.py`.

---

*Testing analysis: Sat Apr 25 2026*
