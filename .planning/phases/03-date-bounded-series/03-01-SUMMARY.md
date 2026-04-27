---
phase: 03-date-bounded-series
plan: 01
subsystem: api
tags: [timeseries, date-window, resolver, client]
requires:
  - phase: 02-utility-surface
    provides: utility layer conventions and shared helpers
provides:
  - Shared inclusive date-window filter utility
  - Client and resolver support for start_date/end_date forwarding
affects: [03-02 adapters, 03-03 cli]
tech-stack:
  added: []
  patterns: [window-then-limit, inclusive date bounds, typed kwargs passthrough]
key-files:
  created:
    - packages/uk-data/tests/test_timeseries_utils.py
  modified:
    - packages/uk-data/src/uk_data/utils/timeseries.py
    - packages/uk-data/src/uk_data/client.py
    - packages/uk-data/src/uk_data/registry.py
    - packages/uk-data/tests/test_client.py
key-decisions:
  - "Date-window validation is centralized in utils/timeseries.py and raises field-specific ValueError messages."
  - "Client and resolver only forward start/end kwargs when explicitly provided to preserve limit-only compatibility."
patterns-established:
  - "Use shared filter_observations_by_date_window for all adapter-level date slicing."
  - "Preserve existing caller behavior by omitting optional kwargs when unset."
requirements-completed: [TS-01, TS-02]
duration: 55min
completed: 2026-04-27
---

# Phase 3 Plan 1: Date-Window Contract Summary

**Canonical inclusive date-window semantics now flow from UKDataClient through ConceptResolver with reusable utility enforcement.**

## Performance

- **Duration:** 55 min
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments
- Added `filter_observations_by_date_window` with strict bound parsing, inverted-range checks, and inclusive behavior.
- Extended `UKDataClient.get_series` with `start_date`/`end_date` while preserving limit-only calls.
- Extended resolver signature and forwarding path for optional date-window kwargs.

## Task Commits
1. **Task 1: Add shared inclusive date-window utilities (TS-02)**
   - `c283575` test(03-01): add failing date-window utility tests
   - `c65b8c8` feat(03-01): implement inclusive date-window utility filtering
2. **Task 2: Extend client and resolver signatures to accept date windows (TS-01)**
   - `bba4200` test(03-01): add failing client date-window forwarding tests
   - `18a6009` feat(03-01): add get_series date-window parameters and forwarding
   - `93f1617` feat(03-01): forward optional date-window kwargs in resolver

## Files Created/Modified
- `packages/uk-data/src/uk_data/utils/timeseries.py` - shared date-window parsing and filtering helper
- `packages/uk-data/src/uk_data/client.py` - public API signature and optional kwargs forwarding
- `packages/uk-data/src/uk_data/registry.py` - resolver-level optional date-window forwarding
- `packages/uk-data/tests/test_timeseries_utils.py` - helper behavior tests
- `packages/uk-data/tests/test_client.py` - client forwarding and compatibility tests

## Decisions Made
- Kept the validation boundary in shared utility code to satisfy threat-model mitigation T-03-01.
- Maintained existing resolver selection behavior and avoided source-specific branches in TS-01 scope.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Ready for Plan 03-02 adapter adoption of shared helper semantics.

## Self-Check: PASSED
- FOUND: packages/uk-data/src/uk_data/utils/timeseries.py
- FOUND: packages/uk-data/src/uk_data/client.py
- FOUND: c283575
- FOUND: c65b8c8
- FOUND: bba4200
- FOUND: 18a6009
- FOUND: 93f1617
