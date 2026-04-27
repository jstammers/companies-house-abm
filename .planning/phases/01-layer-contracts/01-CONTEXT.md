# Phase 1: Layer Contracts - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Formalize the low-level adapter layer in `uk-data`: replace `BaseAdapter` ABC with a `typing.Protocol`, move `HistoricalAdapter` out of `adapters/` into `uk_data/workflows/`, and establish a crisp boundary rule for what belongs in a source adapter. Covers ADAPT-01 and ADAPT-02. Does NOT implement utility-layer APIs (Phase 2), date-bounded series (Phase 3), or ABM relocation (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Contract Form
- **D-01:** Replace the existing `BaseAdapter` ABC with a `typing.Protocol`. Adapters will no longer inherit from `BaseAdapter` — the Protocol defines the structural contract only.
- **D-02:** The Protocol should be `@runtime_checkable` so that compliance can be asserted in tests.
- **D-03:** The Protocol lives in `uk_data/adapters/base.py` (same location, different mechanism). The class name can stay `AdapterProtocol` or similar — downstream code types against it.

### HistoricalAdapter Treatment
- **D-04:** Move `HistoricalAdapter` out of `uk_data/adapters/` into `uk_data/workflows/`. Phase 4 will then move it from `uk_data/workflows/` into `companies_house_abm`.
- **D-05:** Update `UKDataClient` and any other importers to use the new `uk_data.workflows.historical` path. The "historical" key in `UKDataClient.adapters` dict should either be removed from the adapter registry or clearly marked as non-conforming to the Protocol.
- **D-06:** `HistoricalAdapter` does NOT need to implement the new Protocol (it's high-level orchestration, not a low-level source adapter).

### Boundary Definition
- **D-07:** A low-level adapter is responsible for: (1) fetching raw data from a single external source, (2) translating it into canonical models (`Entity`, `Event`, `TimeSeries`), and (3) operational concerns scoped to that source (retry, rate limiting, caching of raw responses). Nothing else.
- **D-08:** Cross-source routing, concept resolution, and domain aggregation are NOT adapter responsibilities. `ConceptResolver` stays in `uk_data/registry.py` as part of the client/routing layer.
- **D-09:** The boundary rule should be documented (docstring or inline comment on the Protocol) so ADAPT-02 is self-enforcing: "add a new adapter = implement this Protocol, touch nothing else."

### Test Strategy
- **D-10:** Add a new Protocol compliance test module (e.g., `tests/adapters/test_protocol_compliance.py`). For each registered adapter (ons, boe, hmrc, land_registry, companies_house, epc), assert that it satisfies the Protocol — either via `isinstance(adapter, AdapterProtocol)` with `runtime_checkable`, or via mypy/ty structural check.
- **D-11:** Existing adapter behavioral tests are left unchanged.

### Claude's Discretion
- Exact Protocol class name (`AdapterProtocol`, `SourceAdapter`, `UKDataAdapter`, etc.)
- Whether to keep `BaseAdapter` as a deprecated shim for one release or remove it immediately
- Internal module layout for `uk_data/workflows/` (single file vs subpackage)
- Whether the `HistoricalAdapter` entry is removed from `UKDataClient.adapters` dict or retained with a deprecation note

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Codebase Architecture
- `.planning/codebase/ARCHITECTURE.md` — overall package ownership and layer model
- `.planning/codebase/STACK.md` — tech stack and tooling constraints
- `.planning/codebase/STRUCTURE.md` — directory layout

### Key Source Files
- `packages/uk-data/src/uk_data/adapters/base.py` — current BaseAdapter ABC (to be replaced with Protocol)
- `packages/uk-data/src/uk_data/adapters/historical.py` — HistoricalAdapter to be relocated
- `packages/uk-data/src/uk_data/client.py` — UKDataClient that wires adapters together
- `packages/uk-data/src/uk_data/registry.py` — ConceptResolver (stays here, client layer)
- `packages/uk-data/src/uk_data/__init__.py` — public exports to keep stable

### Requirements
- `.planning/REQUIREMENTS.md` §ADAPT-01, §ADAPT-02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseAdapter` in `adapters/base.py`: already defines `fetch_series`, `fetch_entity`, `fetch_events`, `available_series`, `available_entity_types`, `available_event_types` — these method signatures become the Protocol surface
- `ConceptResolver` in `registry.py`: stays as-is, acts as routing layer above adapters
- All 6 source adapters (ons, boe, hmrc, land_registry, companies_house, epc) currently inherit `BaseAdapter` — they become Protocol-conforming without inheritance

### Established Patterns
- Adapters are instantiated in `UKDataClient.__init__` as a `dict[str, <adapter>]` — new Protocol type annotation goes here
- `_http.py` contains shared HTTP utilities (retry, get_json, get_text) — these stay in place, adapters import from it

### Integration Points
- `UKDataClient.adapters` dict: type annotation changes from `dict[str, BaseAdapter]` to `dict[str, AdapterProtocol]`
- `HistoricalAdapter` import in `client.py` needs updating to `uk_data.workflows.historical`
- `ConceptResolver` in `registry.py` types its adapter map against the new Protocol

</code_context>

<specifics>
## Specific Ideas

- User wants `HistoricalAdapter` in `uk_data/workflows/` (not `uk_data/utils/`) to make the "workflow orchestration" intent clear — this naming carries forward to Phase 4 when it gets moved to `companies_house_abm`.
- Protocol should be `@runtime_checkable` so compliance tests can use `isinstance` checks.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-layer-contracts*
*Context gathered: 2026-04-27*
