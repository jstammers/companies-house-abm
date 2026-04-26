# Codebase Concerns

**Analysis Date:** 2026-04-26

## Tech Debt

**Legacy `data_sources/` package now mostly silent compatibility shims:**
- Issue: Most modules under `companies_house_abm.data_sources/` have been reduced to `from uk_data.adapters.<x> import *  # noqa: F403` shims with no `DeprecationWarning` emitted. They are superseded by the canonical `uk-data` package adapters but neither call sites nor importers are alerted.
- Files: `packages/companies-house-abm/src/companies_house_abm/data_sources/boe.py`, `data_sources/hmrc.py`, `data_sources/historical.py`, `data_sources/land_registry.py`, `data_sources/companies_house.py`, `data_sources/_http.py`, `data_sources/ons.py` (3-line shims); plus `data_sources/__init__.py` re-exports
- Impact: Two import paths for the same symbols; unclear deprecation timeline; CLI (`packages/companies-house-abm/src/companies_house_abm/cli.py` lines 306-488) still imports through the legacy path; risk of silent drift if the re-export surface changes.
- Fix approach: Add `warnings.warn(..., DeprecationWarning, stacklevel=2)` at module top of each shim, migrate `cli.py` and `abm/scenarios.py` imports to `uk_data.adapters.*` directly, then schedule shim removal in CHANGELOG.

**Real logic still living under legacy `data_sources/`:**
- Issue: `firm_distributions.py` (821 lines), `calibration.py` (420 lines), and `input_output.py` (214 lines) remain only in `companies_house_abm.data_sources/`, never moved to `uk-data`. The split between "shim" and "real logic" inside the same legacy directory is undocumented.
- Files: `packages/companies-house-abm/src/companies_house_abm/data_sources/firm_distributions.py`, `data_sources/calibration.py`, `data_sources/input_output.py`
- Impact: Future readers must inspect each file to know which path is canonical; refactor tools may follow shim re-exports incorrectly.
- Fix approach: Decide per-module whether to (a) promote to `uk-data` (input_output, generic distribution helpers) or (b) move to `companies_house_abm.calibration/` (ABM-specific). Document the boundary in `packages/companies-house-abm/src/companies_house_abm/data_sources/__init__.py`.

**Duplicated CLI ingest/check logic across two packages:**
- Issue: `check-company` is implemented twice with divergent matching semantics (substring vs segment-accurate). `ingest` flow logic is similarly duplicated.
- Files: `packages/companies-house/src/companies_house/cli.py` (lines 168-216, substring match), `packages/companies-house-abm/src/companies_house_abm/cli.py` (lines 176-251, segment match via `_segment_match`)
- Impact: Bug fixes or behaviour changes can be applied to one CLI but missed in the other; only the abm CLI uses the safer match.
- Fix approach: Extract a shared `check_company_in_source()` helper in `companies_house.ingest.xbrl` (preferred package home) and have both CLIs delegate to it.

**Simulation hard caps override configured population sizes:**
- Issue: `Simulation.initialize_agents()` enforces prototype caps `min(cfg.firms.sample_size, 1000)` (line 232) and `min(cfg.households.count, 5000)` (lines 240, 278) regardless of YAML configuration.
- Files: `packages/companies-house-abm/src/companies_house_abm/abm/model.py` lines 232-280, `packages/companies-house-abm/src/companies_house_abm/abm/config.py`
- Impact: Runtime population diverges from configured intent; calibration assumptions and benchmark comparisons (Python vs Rust) are based on capped values; `# cap for prototype` comment indicates this was meant to be temporary.
- Fix approach: Promote caps to explicit `SimulationConfig` fields (e.g. `max_firms`, `max_households`) with sensible defaults, and emit `logger.warning` when caps clamp configured values.

**Stray `print()` calls in library code:**
- Issue: Non-CLI library modules use bare `print()` for output instead of `logging`.
- Files: `packages/companies-house-abm/src/companies_house_abm/abm/evaluation.py:21,363`, `abm/historical.py:19`, `abm/calibration.py:37,194,292`
- Impact: Violates the project logging convention (CONVENTIONS.md), pollutes notebook/test stdout, and cannot be silenced via log level.
- Fix approach: Replace with `logger.info(...)` or move under `if __name__ == "__main__":` smoke-test blocks.

## Known Bugs

**False-positive remote ZIP company checks in `companies-house` CLI:**
- Symptoms: `companies-house check-company <id> --zip-source <url>` reports FOUND when `<id>` is a substring of any filename, even outside the company-number segment (e.g. matches a date-stamped filename containing the digits).
- Files: `packages/companies-house/src/companies_house/cli.py:204` (`any(company_id in name for name in names)` substring match)
- Trigger: Run remote `check-company` against an index whose filenames contain the searched digits in non-company positions.
- Workaround: Use `companies_house_abm check-company` (segment-accurate match at `cli.py:227-230`) or a local ZIP path.

## Security Considerations

**Insecure HTTP transport for Companies House bulk download:**
- Risk: `_BULK_URL_TEMPLATE` and SPARQL endpoints use `http://`, exposing ~400 MB downloads to MITM tampering; an attacker on path can inject arbitrary CSV rows that flow into ABM calibration.
- Files: `packages/uk-data/src/uk_data/adapters/companies_house.py:51-54`, `packages/uk-data/src/uk_data/adapters/land_registry.py:41`, `packages/uk-data/src/uk_data/adapters/historical.py:163-165`
- Current mitigation: User-Agent header set; no transport hardening, no checksum verification, no signed manifest.
- Recommendations: Switch to `https://`, verify TLS (default), reject HTTP downgrades, and (where the upstream provides one) verify file size/hash from a separate metadata endpoint.

**Tracked binary database artefact:**
- Risk: `accounts.db` (10 MB DuckDB file from 2023-12-03) sits at the repo root and is not in `.gitignore`; though `git ls-files` currently shows it untracked locally, it is at risk of being committed and may already exist in branches/forks.
- Files: `accounts.db` (root), `.gitignore` (line 149 only excludes `data/`)
- Current mitigation: Default DuckDB path is `~/.companies_house/data.duckdb` (outside repo), but no enforcement.
- Recommendations: Add `*.db`, `*.duckdb` to `.gitignore`; audit `git log --all -- accounts.db` for accidental commits; document canonical DB location in CONVENTIONS.md.

**Broad exception swallowing masks API/schema regressions:**
- Risk: Numerous `except Exception:` (often paired with silent fallbacks) prevent observability into upstream API changes; calibration drifts silently while appearing successful.
- Files: `packages/uk-data/src/uk_data/adapters/ons.py:161,216,236,391,417`, `adapters/historical.py:155,198,228,253`, `adapters/boe.py:159,229`, `adapters/land_registry.py:477`, `adapters/companies_house.py:130,274`, `packages/companies-house/src/companies_house/ingest/xbrl.py:53,97,180,387`, `analysis/benchmarks.py:123`, `storage/db.py:99`
- Current mitigation: Some paths log warnings; many do not.
- Recommendations: Narrow catches to `(urllib.error.URLError, json.JSONDecodeError, KeyError, polars.exceptions.PolarsError)`; always log with stack context; surface a `data_freshness` flag in adapter responses.

## Performance Bottlenecks

**Full in-memory CSV extraction for Companies House bulk ZIP:**
- Problem: `~400 MB` ZIP CSV is read fully into memory (`raw = csv_file.read()` then `io.BytesIO(raw)`) before `polars.read_csv`.
- Files: `packages/uk-data/src/uk_data/adapters/companies_house.py:162-165` (logic moved here from the legacy `data_sources/` shim)
- Cause: Eager bytes materialisation precludes streaming or chunked parsing.
- Improvement path: Stream the ZIP member to a `tempfile` (already used for download — extend to extraction) and pass the path to `polars.scan_csv()` for lazy/columnar reads; or use `polars.read_csv(buffer, batch_size=...)` with chunked iteration.

**ABM runtime capped below configured population sizes:**
- Problem: With caps at 1,000 firms / 5,000 households, large-population calibrations are silently downscaled; this also undercuts the value of the Rust extension benchmark.
- Files: `packages/companies-house-abm/src/companies_house_abm/abm/model.py:232,240,278`
- Improvement path: Profile hot paths in the simulation step loop, lift caps gated by an explicit config, support staged/parallel execution per sector.

## Fragile Areas

**External public-data adapters with permissive fallbacks:**
- Files: `packages/uk-data/src/uk_data/adapters/ons.py`, `adapters/boe.py`, `adapters/land_registry.py`, `adapters/historical.py`, `adapters/companies_house.py`, `adapters/epc.py`
- Why fragile: ONS/BoE/Land Registry/EPC return shapes evolve; broad `except Exception` blocks collapse distinct failures (network, schema, parsing) into a single fallback path. Test suite verifies fallback execution but not schema-drift detection.
- Safe modification: Add narrow exception types per call site; add response-shape assertions ("validate before parse") and emit structured warnings on shape mismatch.
- Test coverage: Partial — `tests/test_data_sources.py` and `packages/uk-data/tests/adapters/*` cover happy paths and one fallback per source, but no contract tests against recorded fixtures of historical responses.

**Deprecated FastAPI webapp still wired into CLI:**
- Files: `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`, `webapp/models.py`, `webapp/static/`, `cli.py:932-948` (`serve` command)
- Why fragile: `serve` emits `DeprecationWarning` and the FastAPI app title is `"Economy Simulator (deprecated FastAPI app)"`, but the static HTML/JS frontend, Pydantic request/response models, and route handlers continue to ship; users following old docs will still hit it. The webapp depends on `_config_to_params`/`_params_to_config` mappers that mirror the entire `ModelConfig` surface and must be kept in sync manually as the dataclass evolves.
- Safe modification: Maintain the param-mapping helpers via property-style tests (round-trip `config → params → config`).
- Test coverage: `tests/test_webapp.py` (180 lines) tests Pydantic validation and helper mapping only — **no FastAPI `TestClient` integration**, no route exercise, no static asset smoke test.

**Optional Rust extension import is environment-dependent:**
- Files: `packages/companies-house-abm/src/companies_house_abm/_rust_abm.cpython-313-darwin.so` (built artefact alongside the Python package), `packages/rust-abm/`
- Why fragile: The `.so` is committed/built into the package directory but is Python-version- and platform-specific (`cpython-313-darwin`). Anyone on a different Python version sees `ImportError` despite the file being present; CI tests across 3.10-3.13 must rebuild per matrix entry.
- Safe modification: Treat the extension as cache only — exclude `.so` from the workspace package directory, install via `make build-rust` in CI for the active Python version.
- Test coverage: Tests skip when the extension is absent, so coverage is implicitly weak on the Rust path.

## Scaling Limits

**ABM population capped at initialization:**
- Current capacity: 1,000 firms, 5,000 households (regardless of YAML config).
- Limit: Config defaults of `sample_size=50,000` and `count=10,000` are unreachable through `Simulation.initialize_agents()`.
- Scaling path: Lift caps behind explicit config; profile `model.py` step loop hotspots; leverage Rust extension for inner loops; consider sector-stratified parallel runs.

**`SimulationResult.firm_states` / `household_states` accumulate per-period snapshots in memory:**
- Current capacity: Acceptable for short runs (~80 periods × 1,000 firms).
- Limit: `list[list[dict[str, Any]]]` snapshots become memory-bound for long historical scenarios (`build_uk_2013_2024` at quarterly granularity over decades).
- Scaling path: Stream snapshots to Parquet via `SimulationDataCollector`; expose flag to disable per-agent snapshot retention.

## Dependencies at Risk

**External public statistical endpoints with evolving schemas:**
- Risk: ONS / BoE / HMRC / Land Registry / EPC adapters silently fall back on schema mismatches; calibration grows stale.
- Impact: Reproducibility erosion; published simulation outputs may have been built on degraded inputs.
- Migration plan: Add response-shape contract tests at parsing points in `packages/uk-data/src/uk_data/adapters/*.py`; record canonical fixtures and replay them in CI; emit `data_freshness` metadata on every adapter return.

**`mesa` framework upgrade churn:**
- Risk: `Simulation` extends `mesa.Model` and uses `mesa.agent.AgentSet`, `mesa.datacollection.DataCollector` — APIs that shifted between Mesa 2.x and 3.x.
- Impact: Pinning issues during dependency upgrades; test failures on broad version ranges.
- Migration plan: Pin `mesa` minor version in `packages/companies-house-abm/pyproject.toml`; add a focused upgrade-smoke test.

## Missing Critical Features

**No data-freshness / fallback-used reporting:**
- Problem: Adapters silently substitute fallbacks; callers (calibration, ABM, reports) receive no signal that results are degraded.
- Blocks: Reliable auditability of simulation inputs; provenance tracking for policy-analysis claims.

**No schema versioning for `CompanyFiling` / `COMPANIES_HOUSE_SCHEMA`:**
- Problem: 39-column schema has no version stamp persisted alongside Parquet/DuckDB rows.
- Blocks: Safe migrations when XBRL extraction adds columns; cannot distinguish pre/post-migration data.

**No deprecation timeline for legacy `data_sources/` shims and `webapp/`:**
- Problem: Both are flagged as "deprecated" in code/comments without target-removal version, blocking confident removal.
- Blocks: CHANGELOG hygiene; consumer migration planning.

## Test Coverage Gaps

**FastAPI webapp routes not exercised end-to-end:**
- What's not tested: `/api/simulate` and `/api/defaults` request/response cycle through `TestClient`; static asset serving.
- Files: `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`, `tests/test_webapp.py`
- Risk: Serialization, validation, and runtime regressions in routes pass unit tests focused only on parameter-mapping helpers (`_config_to_params`, `_params_to_config`).
- Priority: Medium (route is deprecated, but still shipping)

**Substring-match path in `companies-house` CLI `check-company`:**
- What's not tested: Remote-URL branch correctness for company-number-as-substring inputs.
- Files: `packages/companies-house/src/companies_house/cli.py:204`, `tests/test_ingest.py`
- Risk: False positives in operational workflows; bug remains undetected.
- Priority: High

**`uk-data` adapter contract drift:**
- What's not tested: Recorded-fixture replay for ONS/BoE/Land Registry/EPC adapters to catch upstream schema drift.
- Files: `packages/uk-data/tests/adapters/*` (mostly integration tests skipping when offline)
- Risk: Silent calibration degradation when upstreams change.
- Priority: Medium

**Rust extension parity:**
- What's not tested: Output equivalence between Python-only and Rust-backed simulation paths under identical seeds.
- Files: `packages/rust-abm/`, `scripts/run_benchmark.py`
- Risk: Behavioural divergence between back-ends; benchmark numbers without correctness anchor.
- Priority: Medium

---

*Concerns audit: 2026-04-26*
