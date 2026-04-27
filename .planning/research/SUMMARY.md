# Research Summary

## Key Findings

- Keep `uk-data` as the canonical package, but enforce a strict two-layer structure: low-level adapters + high-level utilities.
- Explicit date-bounded time-series interfaces are mandatory to improve reproducibility and caller control.
- Very high-level historical orchestration belongs in `companies_house_abm` for better domain ownership.

## Recommended Direction

1. Formalize layer boundaries in `uk-data` and align module responsibilities.
2. Implement date-range parameters across high-level time-series APIs and pass through to adapters.
3. Move ABM-domain historical helpers from `uk-data` into `companies_house_abm`, then update imports/tests.

## Main Risks

- Compatibility breaks from changing time-series method signatures.
- Temporary duplication during module relocation.

## Mitigations

- Use phased migration with compatibility wrappers.
- Add requirement-to-phase traceability and verify all dependent call sites.
