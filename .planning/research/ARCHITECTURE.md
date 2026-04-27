# Architecture Research

## Target Component Boundaries

- `uk_data.adapters.*` remains low-level source integration.
- `uk_data.client` and utility modules become high-level series/query orchestration.
- `companies_house_abm.data_sources` owns ABM-level historical composition functions.

## Data Flow

1. Caller requests series data via high-level utility interface with `start_date` and `end_date`.
2. Utility resolves concept -> selects adapter -> fetches source data.
3. Utility normalizes into canonical `TimeSeries` and optionally upserts.
4. ABM-specific historical aggregations occur in `companies_house_abm`, not `uk-data`.

## Build Order

1. Define and enforce layer boundaries in `uk-data`.
2. Add explicit date-range support in high-level and adapter interfaces.
3. Relocate very high-level historical helpers to `companies_house_abm`.
4. Update call sites/tests and remove deprecated bridge code as needed.
