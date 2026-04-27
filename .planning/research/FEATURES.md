# Features Research

## Table Stakes

- A clear low-level adapter contract per source (ONS, BoE, HMRC, etc.).
- A high-level utility surface that exposes series-centric helpers and query conveniences.
- Consistent time-series query semantics with explicit date bounds.
- Stable upsert/query behavior for canonical store interactions.

## Differentiators

- Thin convenience helpers for high-frequency economic indicators used by ABM calibration.
- Cross-source utility functions that resolve concepts and apply standard transforms.
- Deterministic historical snapshots based on explicit time windows.

## Anti-Features

- Source-specific custom behavior leaking directly into the shared utility API.
- High-level historical macro routines living in `uk-data` when they are ABM-domain concerns.

## Complexity and Dependencies

- Moderate complexity: mostly module boundary and API adjustments.
- Main dependency: coordinated changes across `uk-data` and `companies_house_abm` imports.
- Backward compatibility risk: existing callers that depend on limit-default behavior.
