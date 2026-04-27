---
phase: 01-layer-contracts
plan: 02
subsystem: uk-data/workflows
tags: [refactor, relocation, workflows, historical-adapter]
dependency_graph:
  requires: [AdapterProtocol, 01-01]
  provides: [uk_data.workflows.historical.HistoricalAdapter]
  affects: [uk_data.adapters.historical, uk_data.adapters.__init__, uk_data.client, uk_data.workflows]
tech_stack:
  added: []
  patterns: [package-relocation, workflow-orchestration-layer]
key_files:
  created:
    - packages/uk-data/src/uk_data/workflows/__init__.py
    - packages/uk-data/src/uk_data/workflows/historical.py
  modified:
    - packages/uk-data/src/uk_data/adapters/historical.py
    - packages/uk-data/src/uk_data/adapters/__init__.py
    - packages/uk-data/src/uk_data/client.py
decisions:
  - "HistoricalAdapter relocated from adapters/historical.py to workflows/historical.py as plain class (no BaseAdapter inheritance)"
  - "Module-level fetch functions remain in adapters/historical.py for backwards compatibility"
  - "adapters/__init__.py no longer exports HistoricalAdapter"
  - "client.py uses type: ignore[assignment] for historical key — HistoricalAdapter is non-conforming to AdapterProtocol"
metrics:
  duration: ~7 minutes
  completed: 2026-04-27
  tasks_completed: 2
  tasks_total: 2
---

# Phase 01 Plan 02: Relocate HistoricalAdapter to uk_data/workflows/ — Summary

**One-liner:** Relocate `HistoricalAdapter` from `uk_data/adapters/historical.py` to new `uk_data/workflows/historical.py` package as a plain class; update `client.py` and `adapters/__init__.py` to reflect the new location.

## What Was Done

### Task 1 — Create workflows/ package and relocate HistoricalAdapter (commit `84bb373`)

Created the new `uk_data/workflows/` subpackage:

- Created `packages/uk-data/src/uk_data/workflows/__init__.py` with docstring explaining the package is for high-level workflow orchestration (not low-level adapters; does not implement `AdapterProtocol`)
- Created `packages/uk-data/src/uk_data/workflows/historical.py` containing `class HistoricalAdapter:` (plain class, no `BaseAdapter` inheritance per D-06) that:
  - Imports helpers from `uk_data.adapters.historical` (`_HISTORICAL_SERIES_IDS`, `_REGISTRY`, `_observations`)
  - Provides `available_series()` and `fetch_series()` methods
  - Has a docstring noting it is high-level orchestration, not a low-level source adapter
- Removed `class HistoricalAdapter(BaseAdapter)` from `adapters/historical.py`
- Removed `from uk_data.adapters.base import BaseAdapter` and `from uk_data.models import series_from_observations` imports from `adapters/historical.py` (no longer needed there)
- Added relocation comment at top of `adapters/historical.py`
- All module-level fetch functions (`fetch_hpi_quarterly`, `fetch_bank_rate_quarterly`, etc.) remain in `adapters/historical.py`

### Task 2 — Update client.py and adapters/__init__.py (commit `b8d9965`)

- `packages/uk-data/src/uk_data/client.py`:
  - Changed `from uk_data.adapters.historical import HistoricalAdapter` to `from uk_data.workflows.historical import HistoricalAdapter`
  - Added `# type: ignore[assignment]` to the `"historical"` key in `self.adapters` dict with comment explaining it is non-conforming to `AdapterProtocol`
- `packages/uk-data/src/uk_data/adapters/__init__.py`:
  - Removed `from uk_data.adapters.historical import HistoricalAdapter` import
  - Removed `"HistoricalAdapter"` from `__all__`
  - Added comment: `# HistoricalAdapter relocated to uk_data.workflows.historical (not a low-level adapter)`

## Verification

```
from uk_data.workflows.historical import HistoricalAdapter  → OK
from uk_data.adapters.historical import fetch_hpi_quarterly → OK
HistoricalAdapter().available_series()[:3] → ['hpi', 'bank_rate', 'mortgage_rate']
UKDataClient().list_sources() → ['ons', 'boe', 'hmrc', 'land_registry', 'companies_house', 'epc', 'historical']
make verify → All checks passed (50 pre-existing warnings, 0 errors)
172 tests passed (test_historical_data, test_historical_integration, test_ingest, test_company_analysis)
```

## Deviations from Plan

None — plan executed exactly as written. Import ordering required placing `workflows.historical` import after adapter imports in `client.py` (ruff E402/I001 fix — auto-resolved during verify).

## Known Stubs

None — `HistoricalAdapter` is fully functional; it imports live helpers from `adapters.historical`.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries. Change is purely structural (package relocation).

## Self-Check: PASSED

- `packages/uk-data/src/uk_data/workflows/__init__.py` exists ✓
- `packages/uk-data/src/uk_data/workflows/historical.py` contains `class HistoricalAdapter:` ✓
- `packages/uk-data/src/uk_data/adapters/historical.py` does NOT contain `class HistoricalAdapter` ✓
- `packages/uk-data/src/uk_data/client.py` contains `from uk_data.workflows.historical import HistoricalAdapter` ✓
- `packages/uk-data/src/uk_data/adapters/__init__.py` does NOT export `HistoricalAdapter` in `__all__` ✓
- Commit `84bb373` exists ✓
- Commit `b8d9965` exists ✓
