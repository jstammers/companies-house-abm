# Phase 3 Research: Date-Bounded Series

**Date:** 2026-04-27
**Phase:** 03-date-bounded-series
**Scope:** TS-01, TS-02, TS-03

## Research Objective

Determine how to introduce explicit `start_date` / `end_date` support across `uk-data` time-series fetch paths while preserving compatibility for existing `limit`-based callers.

## Current State (Observed)

1. `UKDataClient.get_series()` currently accepts `limit` only and forwards `**kwargs` through `ConceptResolver` to adapters.
2. Adapter implementations already apply slicing by `limit` in source-specific ways:
   - ONS (`ONSAdapter.fetch_series`) uses `fetch_sdmx_series(..., limit=...)`.
   - BoE (`BoEAdapter.fetch_series`) forwards `limit` to `fetch_bank_rate(limit)` for `IUMABEDR`.
   - Land Registry (`fetch_uk_hpi_history(..., limit=...)`) tail-slices after filtering/sorting.
3. Several adapters return point-in-time series (`HMRC`, some BoE and ONS fallback paths), which should accept date params but may naturally yield one-point data.
4. Existing tests validate `limit` behavior and concept resolution but do not assert date-window semantics.

## Recommended Design

### 1) Canonical time-window contract (TS-01, TS-02)

Adopt adapter-level keyword contract:

- `start_date: str | date | datetime | None`
- `end_date: str | date | datetime | None`
- inclusive boundaries (`>= start_date`, `<= end_date`)
- validation rule: `start_date <= end_date`

Apply consistently in:

- `UKDataClient.get_series(...)`
- `ConceptResolver.resolve_series(...)` pass-through
- `ONSAdapter.fetch_series(...)`
- `BoEAdapter.fetch_series(...)` (where historical rows exist)
- `LandRegistryAdapter.fetch_series(...)`

### 2) Shared utility for consistent filtering (TS-02)

Introduce reusable helper(s) in `uk_data.utils.timeseries` to avoid duplicated per-adapter date logic:

- parse/coerce date boundary inputs to UTC/date-safe comparable values
- apply inclusive observation filtering before/after adapter-specific fetches
- deterministic behavior for missing/invalid dates

This keeps semantics aligned and testable in one place.

### 3) Legacy `limit` migration path (TS-03)

Keep `limit` parameter for backward compatibility in Phase 3, but define precedence and behavior explicitly:

- If only `limit` is provided: existing behavior unchanged.
- If date window is provided and `limit` is omitted: return all points within window.
- If both are provided: filter by date window first, then apply `limit` to the filtered set (most recent N unless adapter contract specifies another ordering).

Add explicit deprecation/migration messaging in:

- docstrings (`UKDataClient.get_series`, adapter fetch methods)
- CLI help text (`ukd get-series`)
- release-facing docs/changelog note (if phase includes docs output)

## Testing Strategy

1. Unit tests for shared date-window helper:
   - accepts `date`, `datetime`, ISO string
   - inclusive boundaries
   - invalid date raises `ValueError`
   - inverted bounds raises `ValueError`
2. Adapter-level tests:
   - ONS mocked observations filtered by range
   - BoE mocked observations filtered by range for bank-rate series
   - Land Registry local fixture filtered by range
3. Client-level tests:
   - `get_series(..., start_date=..., end_date=...)` forwards and yields constrained series
   - compatibility path for `limit` remains green
4. Migration behavior tests:
   - both window + limit follows documented precedence

## Risks and Mitigations

1. **Risk:** Inconsistent date formats between adapters (`YYYYQ1`, `DD Mon YYYY`, ISO).
   **Mitigation:** Normalize comparisons via existing timestamp parsing utility and a single filter helper.

2. **Risk:** Silent semantic drift if each adapter filters differently.
   **Mitigation:** Centralize rules in `uk_data.utils.timeseries` and enforce with adapter tests.

3. **Risk:** Breaking callers that assume `limit`-only API.
   **Mitigation:** Keep `limit` behavior intact; treat date window as additive capability with documented precedence.

## Architectural Responsibility Map

- **Client/Resolver layer:** expose and route date-window parameters.
- **Adapter layer:** fetch source data and apply canonical date filtering contract.
- **Utility layer:** own date coercion + inclusive filtering implementation.
- **Tests/docs layer:** lock semantics and migration behavior.

## Implementation Constraints

- No new dependencies required.
- Follow existing Ruff/ty/pytest conventions.
- Keep adapters as source-focused units (no cross-source aggregation logic).

## Out of Scope

- New external data sources.
- ABM behavioral/modeling changes.
- UI/dashboard work.
