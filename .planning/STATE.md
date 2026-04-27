# State

## Current Status

- Phase 01-layer-contracts in progress — Plan 01 complete.
- Plan 01 (AdapterProtocol): ✅ Complete — AdapterProtocol @runtime_checkable Protocol defined; all 6 source adapters are plain structural classes; registry.py typed against AdapterProtocol.
- Next: Plan 02 — Relocate HistoricalAdapter to uk_data/workflows/.

## Active Milestone

- Milestone 1: Data-layer refactor and ownership realignment

## Current Position

- Phase: 01-layer-contracts
- Plan: 01 (complete) → 02 (next)
- Progress: 1/3 plans in Phase 1 complete

## Next Action

- Execute Phase 01, Plan 02: Relocate HistoricalAdapter to uk_data/workflows/; update client.py imports.

## Decisions

| Decision | Phase-Plan | Rationale |
|----------|-----------|-----------|
| AdapterProtocol as @runtime_checkable typing.Protocol | 01-01 | Structural contract; enables isinstance compliance tests |
| BaseAdapter kept as backwards-compat alias (no DeprecationWarning) | 01-01 | Avoid breaking existing imports without formal deprecation mechanism |
| Added explicit stub methods to adapters relying on ABC defaults | 01-01 | Required for isinstance checks with @runtime_checkable Protocol |
| HistoricalAdapter inheritance not modified in Plan 01 | 01-01 | Relocation is Plan 02 scope per CONTEXT.md D-04 |

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01-layer-contracts | 01 | ~15 min | 2/2 | 9 |

## Notes

- Pre-existing test failures in test_abm_evaluation.py and test_historical_simulation.py (Firm.unique_id AttributeError) — unrelated to adapter refactor.
- All adapter-layer tests pass.
