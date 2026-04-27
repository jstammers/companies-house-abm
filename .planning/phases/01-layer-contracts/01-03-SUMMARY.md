---
phase: 01-layer-contracts
plan: 03
status: complete
---

# Plan 01-03 Summary — Protocol Compliance Tests

## What was done

Created `tests/adapters/__init__.py` (package marker) and `tests/adapters/test_protocol_compliance.py` with 8 test cases verifying:

- All 6 source adapters (`ONS`, `BoE`, `HMRC`, `EPC`, `CompaniesHouse`, `LandRegistry`) satisfy `AdapterProtocol` via `isinstance` checks
- `AdapterProtocol` is exported from the public `uk_data.adapters` surface
- `AdapterProtocol` is `@runtime_checkable` (isinstance does not raise TypeError)
- `HistoricalAdapter` intentionally excluded — it is a workflow, not a source adapter

Also fixed a regression introduced by Plan 01-02: `client.py` iterated `self.adapters` (which includes `HistoricalAdapter`) in `list_entities()` and `list_events()`, calling `available_entity_types()` / `available_event_types()` unconditionally. Added `hasattr` guards so non-Protocol adapters are silently skipped.

## Test results

```
packages/uk-data/tests/adapters/test_protocol_compliance.py  8 passed
packages/uk-data/tests/  — only pre-existing test_companies_house_api.py failures remain (Pydantic datetime forward-ref issue, present before Phase 1)
```

## Files modified

- `tests/adapters/__init__.py` (created)
- `tests/adapters/test_protocol_compliance.py` (created)
- `packages/uk-data/src/uk_data/client.py` (hasattr guards in list_entities / list_events)
