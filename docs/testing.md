# Testing

## Conventions

- Tests in `tests/` using pytest with class-based organisation.
- `test_companies_house_*.py` — tests for the `companies_house` package (schema,
  storage, API, PDF).
- `test_ingest.py` — XBRL ingest tests; imports from `companies_house.ingest.xbrl`
  directly.
- `test_company_analysis.py` — analysis tests; imports from
  `companies_house.analysis.*` directly.
- `test_xbrl_schema_integration.py` — validates real XBRL fixtures against the
  schema.
- `test_abm_*.py` — ABM agent/market/model/config tests.
- `test_data_sources.py` — data source and calibration tests.
- Mock `stream_read_xbrl_zip`/`stream_read_xbrl_sync` via
  `unittest.mock.patch` at `companies_house.ingest.xbrl.*`.
- DuckDB tests use `:memory:` databases.
- Coverage sources: `companies_house` and `companies_house_abm`.

## Layout

- `tests/` — shared suite covering all packages, plus `fixtures/` with real XBRL
  test files (HTML + XML).
- `packages/uk-data/tests/` — `uk-data` package tests (also collected by the root
  pytest config via `testpaths`).

## Markers

Integration and slow tests are opt-in. Run the fast offline suite with:

```bash
uv run pytest -m "not integration and not slow"
```
