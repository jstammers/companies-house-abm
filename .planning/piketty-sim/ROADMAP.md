# Roadmap — piketty-sim

## Overview

- Programme: a twelve-notebook marimo series simulating Piketty's wealth
  dynamics, hosted in a new, loosely-coupled workspace package.
- Stages: 15, strictly gated. See `00-OVERVIEW.md` for the seven universal gates.
- Requirements mapped: 90 across 15 stages, plus 5 cross-cutting invariants
  re-verified at every gate.

## Stage sequence

Status values: `todo`, `in progress`, `done`, `blocked`.

| # | Stage | Status | Goal | Requirements | Commit subject |
|---|---|---|---|---|---|
| S01 | Package scaffold | todo | A workspace member that the whole toolchain sees | PKG-01…08 | `chore(piketty-sim): scaffold workspace package and root wiring` |
| S02 | Config & evaluation | todo | Immutable parameter objects and model-agnostic moment scoring | CFG-01…06 | `feat(piketty-sim): add engine config and evaluation framework` |
| S03 | Inequality metrics | todo | The measurement toolkit the whole series reports through | MET-01…06 | `feat(piketty-sim): add Lorenz, Gini, share and Pareto-tail metrics` |
| S04 | Data layer | todo | Pinned, cached, offline-capable loaders for the empirical backbone | DAT-01…08 | `feat(piketty-sim): add WID, JST, Maddison and WIID loaders` |
| S05 | Wealth engine | todo | The reusable generative core: Kesten process and the two laws | ENG-01…09 | `feat(piketty-sim): add Kesten wealth engine and aggregate laws` |
| S06 | Arc A notebooks | todo | NB01–NB03: measurement, the laws, and `r > g` | NBA-01…09 | `feat(piketty-sim): add Arc A notebooks NB01-NB03` |
| S07 | Historical shocks | todo | NB04: the U-curve and war/policy counterfactuals | HST-01…05 | `feat(piketty-sim): add dated shocks and the U-curve notebook` |
| S08 | Demography & inheritance | todo | NB05: overlapping generations, mortality, bequests | OLG-01…06 | `feat(piketty-sim): add OLG demography and inheritance flows` |
| S09 | Fiscal layer | todo | NB06 and NB10: progressive taxation, transfers, incidence | FIS-01…07 | `feat(piketty-sim): add progressive tax and transfer layer` |
| S10 | Regimes | todo | NB07: inequality regimes as parameter sets; reparations arithmetic | REG-01…04 | `feat(piketty-sim): add regime presets and reparations calculators` |
| S11 | Political cleavages | todo | NB08: two-axis spatial voting and the education gradient | POL-01…05 | `feat(piketty-sim): add spatial voting model and WPID loader` |
| S12 | Education & transmission | todo | NB09: Becker–Tomes transmission and mobility metrics | EDU-01…04 | `feat(piketty-sim): add transmission model and mobility metrics` |
| S13 | Participatory socialism | todo | NB11: universal capital endowment | PSO-01…03 | `feat(piketty-sim): add universal endowment and funding mix` |
| S14 | Calibration | todo | Moment matching against WID with seed-stability discipline | CAL-01…05 | `feat(piketty-sim): add calibration targets, moments and sweep` |
| S15 | Capstone & Rust | todo | NB12 and the optional compiled kernel | CAP-01…05 | `feat(piketty-sim): add capstone ABM notebook and Rust kernel` |

## Dependency graph

```
S01 ──┬── S02 ──┐
      ├── S03 ──┼── S05 ── S06 ──┬── S07
      └── S04 ──┘                ├── S08 ── S09 ──┬── S10 ── S15
                                 │                └── S13
                                 ├── S11                ↑
                                 └── S12 ────────────────┘
                     S04+S05 ── S14 ─────────────────── S15
```

Read as: S01 unblocks the three foundation stages; S05 needs config and metrics;
S06 needs data as well; S08 and S09 form the fiscal/demographic spine that S10
and S13 build on; S11 and S12 are independent branches off S06 and S08; S14 can
proceed in parallel once the engine and data exist; S15 needs everything.

## Phase grouping

The stages cluster into four phases. Phases are a reporting convenience; the
gates are per stage.

**Phase 1 — Foundations (S01–S06).** Data pipeline first, then metrics, then the
engine. S05 is the critical path: everything downstream imports it. The engine is
unit-tested as a plain Python module, which marimo's pure-`.py` notebook format
makes straightforward.

**Phase 2 — Historical replication (S07–S09).** The highest
credibility-per-effort work: reproduce the famous figures, then run
counterfactuals. This is also where interrupted-time-series framing does real
analytical work on the 1914 and 1980 breaks.

**Phase 3 — Political economy (S10–S12).** New model types — voting,
transmission — reusing the population objects built earlier. Kept deliberately
small and legible.

**Phase 4 — Synthesis (S13–S15).** Proposals, calibration, then the capstone.
Rust is written only after the Python engine's API is frozen, as a drop-in
replacement behind the same signature.

## Success criteria for the programme

1. A reader with no Python environment can read the notebooks as narrative and,
   with `uv sync`, run every one of them offline.
2. The engine reproduces the qualitative claims of the books — a Pareto tail
   emerging from `r > g` plus return volatility, a U-shaped twentieth century,
   inheritance flows returning after mid-century collapse — and the notebooks
   state plainly where it does not.
3. Simulated top shares are moment-matched against WID within documented
   tolerance at the calibration stage.
4. The wealth engine, the OLG/inheritance layer and the optional compiled-kernel
   pattern are reusable by the wider ABM programme without modification, and no
   part of the series has coupled itself to the existing ABM.
5. Architecture decisions taken here are recorded in the repo's architecture
   documentation so the consumer-ABM work can pick them up.
