# Requirements

## v1 Requirements

### Adapter Layer

- [x] **ADAPT-01**: Developer can use a low-level adapter interface in `uk-data` that is source-agnostic and focused on fetch/translate primitives.
- [x] **ADAPT-02**: Developer can add a new source adapter without modifying high-level utility business logic.

### Utility Layer

- [ ] **UTIL-01**: Developer can call a high-level utility interface for series-specific helper functions without direct adapter coupling.
- [ ] **UTIL-02**: Developer can upsert normalized series data through utility-layer workflows.
- [ ] **UTIL-03**: Developer can query normalized series data through utility-layer workflows.

### Time-Series API

- [ ] **TS-01**: Caller can request time-series data with explicit `start_date` and `end_date` parameters.
- [ ] **TS-02**: Date-range semantics are documented and consistently applied across utilities and adapters.
- [ ] **TS-03**: Existing limit-based call paths have migration behavior defined (compatibility shim or explicit deprecation).

### Historical Ownership

- [ ] **HIST-01**: Very high-level historical helper functions are located in `companies_house_abm`, not `uk-data`.
- [ ] **HIST-02**: ABM code paths use the relocated historical helpers with no functional regression.

## v2 Requirements (Deferred)

- [ ] **V2-01**: Unified paging/cursor abstractions for all external sources.
- [ ] **V2-02**: Advanced caching policy controls per utility function.

## Out of Scope

- UI or dashboard changes.
- New external data-source integrations.
- Changes to ABM behavioral economics logic.

## Traceability

| Requirement | Phase |
|---|---|
| ADAPT-01 | 1 |
| ADAPT-02 | 1 |
| UTIL-01 | 2 |
| UTIL-02 | 2 |
| UTIL-03 | 2 |
| TS-01 | 3 |
| TS-02 | 3 |
| TS-03 | 3 |
| HIST-01 | 4 |
| HIST-02 | 4 |
