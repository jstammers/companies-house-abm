---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-27T19:55:49.139Z"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 11
  completed_plans: 6
  percent: 55
---

# State

## Current Status

- Phase 01-layer-contracts: ✅ Complete (all 3 plans done).
- Phase 02-utility-surface: ✅ Complete (all 3 plans done).
- Phase 03-date-bounded-series: ✅ Complete (all 3 plans done).
- Phase 04-historical-relocation: 🔜 Next — HIST-01, HIST-02.

## Active Milestone

- Milestone 1: Data-layer refactor and ownership realignment

## Current Position

- Phase: 04-historical-relocation (not yet planned)
- Next action: discuss-phase 4 → plan-phase 4 → execute-phase 4

## Decisions

| Decision | Phase-Plan | Rationale |
|----------|-----------|-----------|
| AdapterProtocol as @runtime_checkable typing.Protocol | 01-01 | Structural contract; enables isinstance compliance tests |
| BaseAdapter kept as backwards-compat alias (no DeprecationWarning) | 01-01 | Avoid breaking existing imports without formal deprecation mechanism |
| Added explicit stub methods to adapters relying on ABC defaults | 01-01 | Required for isinstance checks with @runtime_checkable Protocol |
| HistoricalAdapter inheritance not modified in Plan 01 | 01-01 | Relocation is Plan 02 scope per CONTEXT.md D-04 |
| HistoricalAdapter relocated to uk_data.workflows.historical as plain class (no BaseAdapter) | 01-02 | D-04/D-06: it is high-level orchestration, not a low-level source adapter |
| adapters/__init__.py no longer exports HistoricalAdapter | 01-02 | D-05: not part of canonical low-level adapter surface |
| isinstance(adapter, AdapterProtocol) guard in client.py list_entities/list_events | 01-03 | HistoricalAdapter non-conforming; Protocol isinstance check is idiomatic and passes ty |
| New uk_data/utils/ subpackage (not in-place _http.py promotion) | 02-01 | Clean public surface; backward-compat shim in _http.py |
| DuckDB in-memory DELETE+INSERT on composite key for upsert | 02-02 | Avoids full Parquet read-merge-write; clean semantics |
| query_typed() with typed filters + raw sql= escape hatch | 02-03 | Usable without SQL knowledge; power users not blocked |
| Utilities are standalone functions, not UKDataClient methods | 02-01 | Usable without client instantiation; simpler import surface |
| Shared filter_observations_by_date_window utility enforces inclusive bounds and validation | 03-01 | Single source of truth for TS-02 semantics and threat mitigation |
| Optional date kwargs are only forwarded when explicitly set | 03-01 | Preserves legacy limit-only behavior without adding None kwargs |
| Adapters apply window filtering before limit slicing | 03-02 | Enforces TS-03 migration precedence consistently |
| CLI exposes --start-date/--end-date with migration guidance | 03-03 | User-facing migration path from implicit limit-only behavior |

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01-layer-contracts | 01 | ~15 min | 2/2 | 9 |
| 01-layer-contracts | 02 | ~7 min | 2/2 | 5 |
| 01-layer-contracts | 03 | ~10 min | 1/1 | 3 |
| 02-utility-surface | 01 | ~20 min | 4/4 | 7 |
| 02-utility-surface | 02 | ~10 min | 1/1 | 1 |
| 02-utility-surface | 03 | ~5 min | 1/1 | 1 |
| 03-date-bounded-series | 01 | ~55 min | 2/2 | 5 |
| 03-date-bounded-series | 02 | ~48 min | 2/2 | 6 |
| 03-date-bounded-series | 03 | ~31 min | 2/2 | 3 |

## Notes

- Pre-existing broader-repo test failures remain out of scope; phase-specific uk-data checks passed.
- Code review command unavailable in runtime (`gsd-code-review` not installed); treated as non-blocking.
- Phase 03 verification passed with no human-verification gaps.

## Accumulated Context

### Roadmap Evolution

- Phase 03.1 inserted after Phase 3: ONS dataset API migration: use dataset/edition/version/dimension/observation endpoints instead of legacy retrieval paths (URGENT)

**Planned Phase:** 03.1 (ons-dataset-api-migration-use-dataset-edition-version-dimens) — 2 plans — 2026-04-27T19:55:49.133Z
