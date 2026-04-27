---
status: complete
phase: 02-utility-surface
source:
  - 02-01-PLAN.md
  - 02-02-PLAN.md
  - 02-03-PLAN.md
started: 2026-04-27T12:54:59Z
updated: 2026-04-27T13:00:03Z
---

## Current Test

[testing complete]

## Tests

### 1. Public utility imports
expected: Importing utilities from `uk_data.utils` works in one place for HTTP and time-series helpers (`get_json`, `get_text`, `get_bytes`, `retry`, `encode_basic_auth`, `series_from_observations`, `point_timeseries`, `date_to_utc_datetime`).
result: pass

### 2. Backward compatibility for legacy HTTP imports
expected: Existing imports from `uk_data._http` continue to work without code changes (shim re-exports still resolve and behave the same).
result: pass

### 3. Canonical upsert deduplication
expected: Upserting canonical rows with duplicate `(source, entity_id, timestamp)` keys replaces prior rows and keeps one deduplicated record per key.
result: pass

### 4. Typed canonical querying
expected: `CanonicalStore.query_typed(...)` returns filtered data using `concept`, `entity`, `start`, and `end` and also supports `sql=` as a raw query escape hatch.
result: pass

### 5. Adapter/API helper consolidation remains functional
expected: EPC byte downloads, basic-auth header encoding, and Companies House client requests still work after moving shared logic into `uk_data.utils.http`.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[]
