# Changelog

All notable changes to this project are documented here.  The two packages
(`companies_house_abm` and `companies-house`) are versioned independently.

---

## companies_house_abm [0.4.1] - 2026-04-06

### Bug Fixes

- **abm/central_bank:** Fix Taylor rule update order — `_previous_rate` is now
  stored *after* `policy_rate` is set, preventing stale smoothing input on the
  next step
- **abm/bank:** Replace `random.random()` with seeded `numpy.random.Generator`
  so mortgage origination is reproducible when the model RNG is seeded
- **abm/markets:** Propagate `rng` through `BaseMarket.clear()` so bounded-
  rationality mechanisms (`adapt_markup`) use the model RNG instead of a
  per-call default
- **abm/evaluation:** Use sample standard deviation (÷ N-1) for GDP volatility,
  consistent with econometric calibration targets
- **abm/sector_model:** Fix employee assignment — use `n_assigned_households`
  field rather than overwriting the calibrated `employees` attribute
- **abm/calibration:** Track failed parameter-sweep combinations in
  `SweepSummary.n_failed` and `SweepSummary.failed_combinations`
- **abm/housing:** `HousingMarket.clear()` signature updated to include the
  optional `rng` parameter, conforming to the updated `BaseMarket` abstract

### Refactor

- Remove `companies_house_abm.ingest` and `companies_house_abm.company_analysis`
  backward-compatibility shims — import directly from `companies_house` instead
- Move ABM runtime dependencies to `src/companies_house_abm/pyproject.toml`;
  the workspace root is now a virtual root that only holds dev tooling

---

## companies-house [0.2.1] - 2026-04-06

### Bug Fixes

- **ingest/xbrl:** `_TailBuffer.read()` now raises `io.UnsupportedOperation`
  when a read starts before the buffered tail, triggering the larger-range retry
  path instead of silently corrupting Zip64 EOCD parsing
- **ingest/xbrl:** `check_company_in_zip` matches against the third underscore-
  separated filename segment, preventing false positives when the company ID
  appears in other parts of the filename
- **ingest/xbrl:** `fetch_zip_index` catches `OSError` (including
  `io.UnsupportedOperation`) alongside `BadZipFile` to properly trigger retry
- **analysis/forecasting:** `forecast_metric` requires at least 4 clean data
  points (`_MIN_FORECAST_OBS = 4`); returns `None` for sparser data where
  linear regression intervals are too wide to be informative
- **analysis/forecasting:** `ForecastResult` exposes `p_value` and `std_err`
  for programmatic forecast quality assessment
- **storage/db:** `execute_query` opens a read-only DuckDB connection for
  arbitrary SQL, preventing accidental DML/DDL execution
- **storage/db:** `upsert` wraps the INSERT in `BEGIN`/`COMMIT` with `ROLLBACK`
  on failure for atomicity
- **storage/db:** `upsert` fills all schema columns before inserting, preventing
  silent NULL overwrite of previously stored data from partial DataFrames
- **api/client:** `_rate_limit` releases the threading lock before sleeping so
  other threads are not blocked for up to 300 s while waiting for quota

### Security

- Removed `litellm` from optional dependencies (`[llm]` extra); a version
  containing credential-harvesting malware (PYSEC-2026-2) was published to
  PyPI.  Users who need LLM-assisted PDF extraction should install a vetted
  version of litellm separately.

---

## companies_house_abm [0.4.0] - 2026-02-22

### Features

- **abm:** Add bounded-rationality mechanisms — firm satisficing markup,
  household adaptive expectations, bank noisy credit scoring
- **abm:** Add parameter sweep and calibration utilities (`parameter_sweep`,
  `SweepSummary`)
- **abm:** Add simulation evaluation framework (`compute_simulation_stats`,
  `evaluate_simulation`) and `run-simulation` CLI command
- **abm:** Add sector-representative one-firm-per-sector model
  (`SectorModel`, `SECTOR_PROFILES`)
- **webapp:** Expose all `ModelConfig` parameters via REST and load defaults
  from `config/model_parameters.yml`

### Bug Fixes

- **data_sources:** Correct ONS and BoE API endpoints to resolve 403 errors

### Documentation

- Add `CLAUDE.md` with codebase guidance for AI assistants
- Make `prek` pre-commit hooks mandatory; document workflow in `CLAUDE.md`

---

## companies-house [0.2.0] - 2026-02-22

### Features

- Extract `companies-house` as a standalone uv workspace package with its own
  `src/companies_house/pyproject.toml`
- **storage:** Add `CompaniesHouseDB` DuckDB storage layer with composite-PK
  upsert, arbitrary SQL query, and Parquet export/import
- **ingest/pdf:** Add PDF extraction pipeline — kreuzberg for text extraction,
  structured output via litellm; guarded behind `[pdf]` / `[llm]` optional deps
- **api:** Add Companies House REST API client with HTTP Basic auth, token-bucket
  rate limiting (600 req / 5 min), and document download via S3 redirect
- **analysis:** Add company financial analysis, linear-trend forecasting, and
  revenue-weighted sector benchmarking
- **cli:** Add `companies-house` CLI with `ingest`, `search`, `filings`,
  `fetch`, `report`, `migrate`, and `db-query` commands

---

## companies_house_abm [0.3.0] - 2025-12-01

### Features

- Add public data sources for ABM calibration (ONS, Bank of England, HMRC)
- Add economy simulator web application (FastAPI + static frontend)
- **abm:** Add Rust ABM core via krabmaga with Python/Rust benchmark script
- **data:** Add firm distribution analysis and profiling
- **data_sources:** Add Companies House SIC code fetcher

---

## companies_house_abm [0.2.0] - 2025-09-01

### Features

- **abm:** Implement agent-based model — `Firm`, `Household`, `Bank`,
  `CentralBank`, `Government` agents; `GoodsMarket`, `LabourMarket`,
  `CreditMarket`; `Simulation` orchestrator
- Add `ModelConfig` frozen-dataclass configuration with YAML loader

### Miscellaneous Tasks

- Remove legacy Kedro scaffolding and example files

---

## companies_house_abm [0.1.0] - 2025-06-01

### Features

- Initial release: restructure project from `earningsai` to
  `companies-house-abm`
- Simplify config structure; remove Kedro-style layout and deprecated data
<!-- generated by git-cliff -->
