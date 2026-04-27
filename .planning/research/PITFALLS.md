# Pitfalls Research

## Pitfall 1: Layer Bleed-Through

- Warning signs: utility functions directly encode source-specific quirks.
- Prevention: keep source translation in adapters; utility layer only composes canonical outputs.
- Phase to address: Phase 1.

## Pitfall 2: Ambiguous Date Semantics

- Warning signs: mixed inclusive/exclusive ranges and timezone ambiguity.
- Prevention: document and enforce interval semantics (`start_date <= t <= end_date`) and default timezone handling.
- Phase to address: Phase 2.

## Pitfall 3: Breaking Existing Callers

- Warning signs: failing tests in ABM calibration and data-source wrappers after signature changes.
- Prevention: introduce compatibility shims during migration, then remove in later cleanup phase.
- Phase to address: Phase 3.

## Pitfall 4: Historical Logic Ownership Drift

- Warning signs: macro historical utilities remain duplicated across `uk-data` and `companies_house_abm`.
- Prevention: single-owner rule for domain orchestration in `companies_house_abm`.
- Phase to address: Phase 3.
