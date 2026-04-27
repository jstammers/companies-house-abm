# Phase 2 Context: Utility Surface

## Gray Areas Resolved

### 1. Utility module shape
**Decision:** New `uk_data/utils/` subpackage.

Structure:
```
uk_data/utils/
├── __init__.py      # re-exports: get_json, get_text, get_bytes, retry, clear_cache, series_from_observations, point_timeseries
├── http.py          # promoted from _http.py (rename only, no logic changes)
└── timeseries.py    # promoted from models/timeseries.py helpers (_parse_timestamp + factories)
```

`_http.py` and `models/timeseries.py` factories stay in place with re-imports from `utils/` for backward compat, so no adapter breaks.

### 2. Upsert semantics (UTIL-02)
**Decision:** DuckDB `INSERT OR REPLACE` on composite key.

- Composite PK: `(source, entity_id, timestamp)` for time-series rows
- `CanonicalStore.upsert(df)` loads Parquet into DuckDB in-memory, runs `INSERT OR REPLACE`, writes back to Parquet
- `CanonicalStore.query(sql)` stays as-is (raw SQL)

### 3. Query interface (UTIL-03)
**Decision:** Typed `query()` + raw SQL escape hatch.

```python
store.query(concept="bank_rate", entity="BoE", start="2020-01-01", end="2023-12-31")  # typed
store.query(sql="SELECT * FROM data WHERE source = 'boe'")  # raw escape hatch
```

### 4. Utility coupling
**Decision:** Standalone importable functions, no coupling to `UKDataClient`.

```python
from uk_data.utils.http import get_json
from uk_data.utils.timeseries import series_from_observations
```

`UKDataClient` does NOT need updating — adapters already import from `_http.py` / `models/timeseries.py`; backward-compat re-exports handle the transition.

## Implementation Notes

- Duplicate helpers to consolidate into `utils/`:
  - `_encode_basic_auth` — duplicated in `epc.py` and `api/client.py`
  - `_request_bytes` — duplicated in `epc.py` and `_http.py`
  - `_epc_event_timestamp` / `_transaction_event_timestamp` — both coerce `date → UTC datetime`; extract shared `date_to_utc_datetime(d)` helper into `utils/`
- `_parse_timestamp` in `models/timeseries.py` moves to `utils/timeseries.py` (private, but co-located with factories)
- All changes must pass `ty` type checker and ruff; existing adapter tests must stay green
