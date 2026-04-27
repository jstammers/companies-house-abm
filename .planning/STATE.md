---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-04-27T14:00:00.000Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
  percent: 50
---

# State

## Current Status

- Phase 01-layer-contracts: ✅ Complete (all 3 plans done).
- Phase 02-utility-surface: ✅ Complete (all 3 plans done).
- Phase 03-date-bounded-series: 🔜 Next — TS-01, TS-02, TS-03.

## Active Milestone

- Milestone 1: Data-layer refactor and ownership realignment

## Current Position

- Phase: 03-date-bounded-series (not yet planned)
- Next action: discuss-phase 3 → plan-phase 3 → execute-phase 3

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

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01-layer-contracts | 01 | ~15 min | 2/2 | 9 |
| 01-layer-contracts | 02 | ~7 min | 2/2 | 5 |
| 01-layer-contracts | 03 | ~10 min | 1/1 | 3 |
| 02-utility-surface | 01 | ~20 min | 4/4 | 7 |
| 02-utility-surface | 02 | ~10 min | 1/1 | 1 |
| 02-utility-surface | 03 | ~5 min | 1/1 | 1 |

## Notes

- Pre-existing test failures in test_abm_evaluation.py, test_historical_simulation.py, test_companies_house_api.py — unrelated to adapter refactor.
- All uk-data adapter/client/storage/utils tests pass.
- ty exits 0 on new files; pre-existing epc.py/land_registry.py warnings unchanged.
