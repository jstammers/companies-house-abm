---
phase: 01-layer-contracts
plan: 01
subsystem: uk-data/adapters
tags: [refactor, protocol, adapter, contracts]
dependency_graph:
  requires: []
  provides: [AdapterProtocol, structural-adapter-contract]
  affects: [uk_data.adapters, uk_data.registry, uk_data.adapters.__init__]
tech_stack:
  added: []
  patterns: [typing.Protocol, runtime_checkable, structural-typing, duck-typing]
key_files:
  created: []
  modified:
    - packages/uk-data/src/uk_data/adapters/base.py
    - packages/uk-data/src/uk_data/adapters/ons.py
    - packages/uk-data/src/uk_data/adapters/boe.py
    - packages/uk-data/src/uk_data/adapters/hmrc.py
    - packages/uk-data/src/uk_data/adapters/epc.py
    - packages/uk-data/src/uk_data/adapters/companies_house.py
    - packages/uk-data/src/uk_data/adapters/land_registry.py
    - packages/uk-data/src/uk_data/adapters/__init__.py
    - packages/uk-data/src/uk_data/registry.py
decisions:
  - "AdapterProtocol defined as @runtime_checkable typing.Protocol replacing BaseAdapter ABC"
  - "All 6 source adapters are now plain classes satisfying the Protocol structurally (no inheritance)"
  - "BaseAdapter kept as backwards-compat alias at module level (no DeprecationWarning)"
  - "Added explicit stub methods to adapters that relied on ABC defaults"
  - "HistoricalAdapter inheritance untouched — it is out of scope (Plan 02 relocates it)"
metrics:
  duration: ~15 minutes
  completed: 2026-04-27
  tasks_completed: 2
  tasks_total: 2
---

# Phase 01 Plan 01: Replace BaseAdapter ABC with AdapterProtocol Protocol — Summary

**One-liner:** Replace `BaseAdapter` ABC with `@runtime_checkable` `typing.Protocol` named `AdapterProtocol`; all 6 source adapters become plain structural duck-typed classes.

## What Was Done

### Task 1 — Replace BaseAdapter ABC with AdapterProtocol Protocol (commit `37c85ab`)

Rewrote `packages/uk-data/src/uk_data/adapters/base.py`:
- Removed `from abc import ABC, abstractmethod` entirely
- Added `from typing import Protocol, runtime_checkable`
- Defined `AdapterProtocol` as a `@runtime_checkable` `typing.Protocol` with the full method surface: `fetch_series`, `available_series`, `available_entity_types`, `available_event_types`, `fetch_entity`, `fetch_events`
- Added boundary rule docstring (ADAPT-02): what belongs in an adapter vs. not
- Kept `BaseAdapter = AdapterProtocol` as a backwards-compat alias

### Task 2 — Remove inheritance from all 6 adapters; update `__init__.py` and `registry.py` (commit `9284d7c`)

For each of the 6 source adapters:
- Removed `from uk_data.adapters.base import BaseAdapter` import
- Changed class definition from `class XxxAdapter(BaseAdapter):` to `class XxxAdapter:`
- Added explicit stub methods for Protocol methods previously inherited from ABC defaults:
  - `ONSAdapter`: added `available_entity_types`, `available_event_types`, `fetch_entity`, `fetch_events`
  - `BoEAdapter`: added `available_entity_types`, `available_event_types`, `fetch_entity`, `fetch_events`
  - `HMRCAdapter`: added `available_entity_types`, `available_event_types`, `fetch_entity`, `fetch_events`
  - `EPCAdapter`: added `available_series`, `available_entity_types`, `fetch_entity`
  - `CompaniesHouseAdapter`: added `available_series`
  - `LandRegistryAdapter`: added `available_entity_types`, `fetch_entity`

Updated `adapters/__init__.py`:
- Added `AdapterProtocol` import alongside `BaseAdapter`
- Added `"AdapterProtocol"` to `__all__`

Updated `registry.py`:
- Changed `TYPE_CHECKING` import from `BaseAdapter` to `AdapterProtocol`
- Changed `ConceptResolver.adapters: dict[str, BaseAdapter]` to `dict[str, AdapterProtocol]`

## Verification

```
isinstance(ONSAdapter(), AdapterProtocol) → True
isinstance(BoEAdapter(), AdapterProtocol) → True
isinstance(HMRCAdapter(), AdapterProtocol) → True
isinstance(EPCAdapter(), AdapterProtocol) → True
isinstance(CompaniesHouseAdapter(), AdapterProtocol) → True
isinstance(LandRegistryAdapter(), AdapterProtocol) → True
```

Pre-commit hooks (ruff lint, ruff format, ty type-checker) all passed for both commits.

## Deviations from Plan

### Out of Scope — HistoricalAdapter Not Modified

`HistoricalAdapter` in `adapters/historical.py` still inherits from `BaseAdapter` — this is intentional. The plan explicitly scopes Task 2 to the 6 **source** adapters. `HistoricalAdapter` relocation to `uk_data/workflows/` is Plan 02's responsibility per the CONTEXT.md decisions (D-04, D-05).

## Known Stubs

None — all stub methods (`raise NotImplementedError` / `return []`) represent the correct semantics for adapters that do not support those operations. These are not UI stubs; they are appropriate Protocol conformance implementations.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. Changes are purely structural (typing/inheritance changes only).

## Self-Check: PASSED

- `packages/uk-data/src/uk_data/adapters/base.py` — exists, contains `@runtime_checkable` and `AdapterProtocol` ✓
- `packages/uk-data/src/uk_data/adapters/__init__.py` — exports `AdapterProtocol` in `__all__` ✓
- `packages/uk-data/src/uk_data/registry.py` — contains `dict[str, AdapterProtocol]` ✓
- Commit `37c85ab` exists ✓
- Commit `9284d7c` exists ✓
- `isinstance(ONSAdapter(), AdapterProtocol)` returns `True` ✓
- Zero adapter files (of the 6 source adapters) contain `(BaseAdapter)` ✓
