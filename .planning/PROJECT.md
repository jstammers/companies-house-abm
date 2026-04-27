# EarningsAI Data Layer Refactor

## What This Is

This project restructures the `uk-data` package into a clearer two-layer API while preserving adapter breadth and improving time-series ergonomics. It also relocates very high-level historical helpers back into `companies_house_abm` where domain orchestration belongs.

## Core Value

Give ABM and analytics callers a stable, explicit, date-bounded data interface that separates low-level source adapters from high-level utility workflows.

## Context

- The repository already has a mapped brownfield architecture with `uk-data` as the canonical data package and `companies_house_abm` as the domain orchestrator.
- Existing codebase docs in `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STACK.md`, and `.planning/codebase/STRUCTURE.md` were used to scope this effort.
- Current concern: `uk-data` blends generic adapter mechanics with high-level historical/domain helpers, which increases coupling and blurs ownership.

## Requirements

### Validated

- [x] Canonical public data access exists in `uk-data` with multiple adapters and a `UKDataClient` facade.
- [x] `companies_house_abm` consumes public data and already contains domain-level calibration/historical logic.
- [x] Time-series retrieval is a core cross-package dependency and must remain backward compatible where reasonable.

### Active

- [ ] Split `uk-data` into a low-level generic adapter layer and a high-level utility layer.
- [ ] Support explicit `start_date` and `end_date` parameters for time-series interfaces.
- [ ] Move very high-level historical helper functions from `uk-data` back into `companies_house_abm`.

### Out of Scope

- End-user UI changes — no frontend scope in this initiative.
- New external data providers — refactor existing provider surface first.
- ABM macroeconomic model-behavior changes — this project focuses on data interface structure.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep `uk-data` as canonical source package | Existing package is already consumed across workspace and has stable adapter primitives | Accepted |
| Introduce strict low-level vs high-level layering inside `uk-data` | Reduces coupling and clarifies extension points | Accepted |
| Prefer explicit date-bounded time-series APIs over implicit limit behavior | Improves reproducibility and caller control | Accepted |
| Move domain-level historical orchestration into `companies_house_abm` | Keeps high-level economic semantics near ABM domain consumers | Accepted |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-27 after initialization*
