# Roadmap

## Overview

- Project: EarningsAI data-layer refactor for `uk-data` and `companies_house_abm`
- Phases: 4
- v1 requirements mapped: 10/10

| Phase | Name | Goal | Requirements |
|---|---|---|---|
| 1 | Layer Contracts | Define and enforce low-level adapter boundaries in `uk-data` | ADAPT-01, ADAPT-02 |
| 2 | Utility Surface | Build/refine high-level utility layer for helpers, upsert, query | UTIL-01, UTIL-02, UTIL-03 |
| 3 | Date-Bounded Series | Implement explicit `start_date`/`end_date` semantics and migration path | TS-01, TS-02, TS-03 |
| 4 | Historical Relocation | Move very high-level historical helpers into `companies_house_abm` and rewire callers | HIST-01, HIST-02 |

## Phase Details

### Phase 1: Layer Contracts

Goal: Formalize low-level adapter responsibilities and isolate source-specific logic.

**Requirements:** ADAPT-01, ADAPT-02
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Replace BaseAdapter ABC with @runtime_checkable AdapterProtocol; update all 6 source adapters and registry
- [x] 01-02-PLAN.md — Relocate HistoricalAdapter to uk_data/workflows/; update client.py imports
- [ ] 01-03-PLAN.md — Protocol compliance test module for all 6 source adapters

Success criteria:
1. Adapter contracts are documented and reflected in code structure.
2. High-level workflows no longer require direct source-specific adapter knowledge.
3. Existing adapter tests continue to pass or are updated with equivalent coverage.

### Phase 2: Utility Surface

Goal: Establish high-level utility APIs for series helpers and canonical upsert/query flows.

Success criteria:
1. Utility interfaces expose series-specific helper functions.
2. Upsert/query pathways are available from high-level utilities.
3. Call sites can use utilities without reaching into adapter internals.

### Phase 3: Date-Bounded Series

Goal: Replace implicit limit-only behavior with explicit date windows.

Success criteria:
1. Time-series APIs accept `start_date` and `end_date` parameters.
2. Date inclusion semantics are documented and validated.
3. Legacy limit behavior has a migration/deprecation path and test coverage.

### Phase 4: Historical Relocation

Goal: Move very high-level historical functions back into `companies_house_abm` and stabilize integration.

Success criteria:
1. Target historical modules/functions are relocated out of `uk-data`.
2. `companies_house_abm` imports/callers are updated to the new ownership.
3. Calibration/historical tests run without regression.
