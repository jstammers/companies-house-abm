# Codebase Concerns

**Analysis Date:** 2026-04-25

## Tech Debt

**Duplicated CLI ingest/check logic across two packages:**
- Issue: Ingestion and `check-company` command logic is duplicated with near-identical control flow in two CLIs, increasing drift risk.
- Files: `packages/companies-house/src/companies_house/cli.py`, `packages/companies-house-abm/src/companies_house_abm/cli.py`
- Impact: Bug fixes and behavior changes can be applied to one CLI but missed in the other.
- Fix approach: Extract shared command helpers into a common module (e.g., in `companies-house`) and call from both CLIs.

**Simulation uses hard caps that override configured scale:**
- Issue: Agent initialization enforces prototype caps (`min(sample_size, 1000)`, `min(count, 5000)`) even when config defaults are much larger.
- Files: `packages/companies-house-abm/src/companies_house_abm/abm/model.py`, `packages/companies-house-abm/src/companies_house_abm/abm/config.py`
- Impact: Runtime behavior diverges from configuration intent, making calibration/performance assumptions inconsistent.
- Fix approach: Make caps explicit config knobs and surface warnings when effective values differ from configured values.

## Known Bugs

**False positives for remote ZIP company checks in one CLI path:**
- Symptoms: `check-company` may report FOUND for remote ZIP indexes when `company_id` is only a substring in a filename.
- Files: `packages/companies-house/src/companies_house/cli.py` (remote URL branch), `packages/companies-house/src/companies_house/ingest/xbrl.py` (correct segment matcher exists)
- Trigger: Run `companies-house check-company <id> --zip-source https://...` against filenames that contain `<id>` outside the company-number segment.
- Workaround: Use `companies_house_abm` CLI `check-company` (segment-based match) or local ZIP check path.

## Security Considerations

**Insecure transport for Companies House bulk download URL template:**
- Risk: Bulk download endpoint is built with `http://`, allowing potential MITM tampering on untrusted networks.
- Files: `packages/companies-house-abm/src/companies_house_abm/data_sources/companies_house.py`
- Current mitigation: None in code; request uses a User-Agent header but no transport hardening.
- Recommendations: Switch `_BULK_URL_TEMPLATE` to `https://`, validate response source/content expectations, and reject downgrade.

## Performance Bottlenecks

**Full in-memory CSV extraction for large Companies House bulk ZIP:**
- Problem: ZIP CSV is read fully into memory before `polars.read_csv`, despite source files being very large.
- Files: `packages/companies-house-abm/src/companies_house_abm/data_sources/companies_house.py`
- Cause: `_parse_bulk_zip()` performs `raw = csv_file.read()` then wraps bytes in `io.BytesIO`.
- Improvement path: Use streaming CSV reads from ZIP member where possible, or chunked processing to reduce peak memory.

## Fragile Areas

**Broad exception swallowing around external data fetch/parsing:**
- Files: `packages/companies-house-abm/src/companies_house_abm/data_sources/ons.py`, `packages/companies-house-abm/src/companies_house_abm/data_sources/ons_housing.py`, `packages/companies-house-abm/src/companies_house_abm/data_sources/boe.py`, `packages/companies-house-abm/src/companies_house_abm/data_sources/companies_house.py`, `packages/companies-house/src/companies_house/ingest/xbrl.py`
- Why fragile: Multiple `except Exception` blocks collapse distinct failures into generic fallbacks, masking API/schema regressions.
- Safe modification: Narrow catches to expected exception classes and include structured error context for observability.
- Test coverage: Partial; fallback paths are tested heavily in `tests/test_data_sources.py`, but API schema-drift detection is limited.

## Scaling Limits

**ABM runtime capped below configured population sizes:**
- Current capacity: At initialization, firms are capped to 1,000 and households to 5,000.
- Limit: Config defaults (`sample_size=50,000`, `count=10,000`) are not fully realizable in standard run path.
- Scaling path: Add configurable scaling modes, profile hotspots in `packages/companies-house-abm/src/companies_house_abm/abm/model.py`, and support staged/parallel simulation execution.

## Dependencies at Risk

**External statistical endpoints with evolving schemas:**
- Risk: ONS/BoE/Land Registry response shape changes can silently degrade calibration due to permissive fallbacks.
- Impact: Model calibration may become stale while appearing successful.
- Migration plan: Add schema assertions/contract checks near parsing points in `packages/companies-house-abm/src/companies_house_abm/data_sources/*.py` and fail loudly in CI for unexpected payload shapes.

## Missing Critical Features

**No explicit calibration freshness/staleness reporting:**
- Problem: Data-source fallbacks are silent to callers; no surfaced metadata indicates whether results are live or fallback.
- Blocks: Reliable auditability of simulation inputs for reproducibility and policy-analysis confidence.

## Test Coverage Gaps

**Web API endpoint behavior not directly exercised end-to-end:**
- What's not tested: FastAPI endpoint contract for `/api/simulate` and `/api/defaults` (request/response integration path).
- Files: `packages/companies-house-abm/src/companies_house_abm/webapp/app.py`, `tests/test_webapp.py`
- Risk: Serialization/validation/runtime regressions in API routes can pass unit tests focused only on parameter mapping helpers.
- Priority: Medium

**Remote URL matching semantics for `companies-house` CLI `check-company`:**
- What's not tested: Segment-accurate matching in remote URL branch for `companies-house` CLI.
- Files: `packages/companies-house/src/companies_house/cli.py`, `tests/test_ingest.py`
- Risk: False-positive company presence checks in operational workflows.
- Priority: High

---

*Concerns audit: 2026-04-25*
