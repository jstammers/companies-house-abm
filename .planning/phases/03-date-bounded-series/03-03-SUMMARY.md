---
phase: 03-date-bounded-series
plan: 03
subsystem: docs
tags: [cli, migration, compatibility, tests]
requires:
  - phase: 03-01
    provides: client/resolver date-window API contract
  - phase: 03-02
    provides: adapter-level date-window behavior and precedence implementation
provides:
  - CLI date-window migration surface and user guidance
  - Compatibility tests for limit-only and combined window+limit paths
affects: [user workflows, roadmap progress, verification]
tech-stack:
  added: []
  patterns: [explicit migration messaging, compatibility-first evolution]
key-files:
  created: []
  modified:
    - packages/uk-data/src/uk_data/cli.py
    - packages/uk-data/tests/test_client.py
    - packages/uk-data/tests/test_client_integration.py
key-decisions:
  - "CLI only forwards date-window args when explicitly provided to avoid leaking Typer option objects."
  - "Migration contract is locked in unit tests and network-gated integration tests."
patterns-established:
  - "Limit-only path remains stable while window and window+limit paths are explicit and tested."
  - "User-facing command help documents precedence semantics directly at entry point."
requirements-completed: [TS-03, TS-02]
duration: 31min
completed: 2026-04-27
---

# Phase 3 Plan 3: CLI Migration and Compatibility Summary

**CLI now exposes explicit date-window parameters and migration semantics while preserving legacy limit-only behavior with regression-resistant tests.**

## Performance

- **Duration:** 31 min
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments
- Added `--start-date` and `--end-date` options to `ukd get-series` with migration guidance in help text/docstring.
- Ensured CLI only forwards explicit date-window inputs and keeps limit-only calls unchanged.
- Added compatibility tests covering limit-only, window-only forwarding, and combined window+limit acceptance.

## Task Commits
1. **Task 1: Add CLI migration surface for explicit date windows (TS-03)**
   - `e51f242` test(03-03): add failing migration-path date-window tests
   - `dc50e6a` feat(03-03): add CLI date-window options with migration semantics
2. **Task 2: Lock migration behavior with integration-oriented compatibility tests**
   - `44e829d` feat(03-03): lock migration contract tests for date-window and limit paths

## Files Created/Modified
- `packages/uk-data/src/uk_data/cli.py` - new date-window options, migration semantics, guarded forwarding
- `packages/uk-data/tests/test_client.py` - CLI forwarding and compatibility assertions
- `packages/uk-data/tests/test_client_integration.py` - combined window+limit integration acceptance check

## Decisions Made
- Kept integration test additions behind existing `integration` markers and reachability checks (T-03-09 accepted risk).
- Used deterministic unit tests for precedence/compatibility to avoid relying on network conditions.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Phase 3 implementation is fully staged for verifier review and roadmap completion.

## Self-Check: PASSED
- FOUND: packages/uk-data/src/uk_data/cli.py
- FOUND: packages/uk-data/tests/test_client.py
- FOUND: e51f242
- FOUND: dc50e6a
- FOUND: 44e829d
