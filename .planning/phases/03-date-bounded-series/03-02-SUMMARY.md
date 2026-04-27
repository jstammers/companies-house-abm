---
phase: 03-date-bounded-series
plan: 02
subsystem: api
tags: [ons, boe, land-registry, timeseries]
requires:
  - phase: 03-01
    provides: shared date-window filter and client/resolver passthrough contract
provides:
  - Date-window support across ONS, BoE, and Land Registry adapters
  - Filter-before-limit ordering for historical series paths
affects: [03-03 cli, downstream series consumers]
tech-stack:
  added: []
  patterns: [shared helper reuse, adapter consistency, filter-before-limit]
key-files:
  created: []
  modified:
    - packages/uk-data/src/uk_data/adapters/ons.py
    - packages/uk-data/src/uk_data/adapters/boe.py
    - packages/uk-data/src/uk_data/adapters/land_registry.py
    - packages/uk-data/tests/adapters/test_ons.py
    - packages/uk-data/tests/adapters/test_boe.py
    - packages/uk-data/tests/adapters/test_land_registry.py
key-decisions:
  - "Adapters request broader history only when date-window bounds are provided, then apply shared filter and tail limit."
  - "Point-series fallback paths remain unchanged while accepting optional date-window kwargs."
patterns-established:
  - "Apply window filtering before limit slicing in all historical adapter flows."
  - "Use shared utility function to normalize adapter-specific date formats."
requirements-completed: [TS-01, TS-02]
duration: 48min
completed: 2026-04-27
---

# Phase 3 Plan 2: Adapter Date-Window Adoption Summary

**ONS, BoE, and Land Registry adapters now consistently honor inclusive date windows with deterministic filter-before-limit semantics.**

## Performance

- **Duration:** 48 min
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments
- Added ONS SDMX path date-window handling using shared helper and post-filter limit slicing.
- Added BoE bank-rate windowing and filter-before-limit behavior while preserving fallback point behavior.
- Added Land Registry `uk_hpi_full` date-window support and propagated kwargs through adapter entrypoint.

## Task Commits
1. **Task 1: Implement date-window support in ONS and BoE adapters**
   - `d5c755b` test(03-02): add failing adapter date-window coverage
   - `91bdeb0` feat(03-02): apply shared date-window semantics in ONS and BoE adapters
2. **Task 2: Implement date-window support in Land Registry time-series path**
   - `2334341` test(03-02): add failing land registry date-window tests
   - `6e9b27c` feat(03-02): add date-window filtering to land registry history path

## Files Created/Modified
- `packages/uk-data/src/uk_data/adapters/ons.py` - date-window filtering and limit ordering in SDMX path
- `packages/uk-data/src/uk_data/adapters/boe.py` - bank-rate date-window filtering and limit ordering
- `packages/uk-data/src/uk_data/adapters/land_registry.py` - `fetch_uk_hpi_history` window support and adapter passthrough
- `packages/uk-data/tests/adapters/test_ons.py` - inclusive range + ordering tests
- `packages/uk-data/tests/adapters/test_boe.py` - inclusive range + ordering tests
- `packages/uk-data/tests/adapters/test_land_registry.py` - inclusive range + ordering tests

## Decisions Made
- Used helper-based filtering across all three adapters to satisfy T-03-04 and T-03-05 mitigations.
- Kept non-historical point-series handlers untouched to avoid unintended migration side effects.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Ready for Plan 03-03 CLI/user-facing migration messaging and compatibility lock-in.

## Self-Check: PASSED
- FOUND: packages/uk-data/src/uk_data/adapters/ons.py
- FOUND: packages/uk-data/src/uk_data/adapters/boe.py
- FOUND: d5c755b
- FOUND: 91bdeb0
- FOUND: 2334341
- FOUND: 6e9b27c
