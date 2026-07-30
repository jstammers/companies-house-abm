# Simulating Piketty — Implementation Programme Overview

## Context

We are adding a new uv-workspace package, `packages/piketty-sim/`, that hosts a
series of twelve interactive [marimo](https://docs.marimo.io/) notebooks
translating the analytical content of Thomas Piketty's three major works —
*Capital in the Twenty-First Century* (2013), *Capital and Ideology* (2019) and
*A Brief History of Equality* (2021) — into runnable simulations backed by open
inequality data.

Each notebook pairs a concept from the books with (a) real data from open
inequality databases and (b) a generative simulation that reproduces the
mechanism bottom-up. The series is both a pedagogical artefact and a testbed for
wealth-dynamics machinery that is reusable in the wider ABM programme:
right-skewed wealth/income tails, stratified household populations,
overlapping-generation demographics and moment-matched calibration are shared
requirements with the consumer-ABM work, and public data is a lower-risk place
to harden them.

The unifying insight for the build is that all three books share **one
generative engine**: a heterogeneous-agent wealth accumulation process
(labour income + returns on wealth + inheritance − consumption − taxes),
embedded in a demographic overlay, whose parameters (`r`, `g`, `s`, return
heterogeneity, tax schedules, endowments) define the "regime". Books 2 and 3 are
largely re-parameterisations and political-economy wrappers around the engine
built for Book 1. The engine is therefore designed **once**, in Stage 05, and
extended through explicit seams thereafter.

## Architectural position

`piketty-sim` is the fifth workspace package, alongside `companies-house`,
`uk-data`, `companies_house_abm` and the out-of-workspace `rust-abm` crate.

**Coupling rules** (non-negotiable; enforced by a test in every stage gate):

1. `piketty-sim` **must not** import `companies_house_abm` or `companies_house`.
   The reusable code in the ABM package is ~120 genuinely generic lines; importing
   it would drag in mesa, fastapi and matplotlib along with the whole
   housing/mortgage model. Those lines are copy-adapted instead, with attribution
   in the module docstring.
2. `piketty-sim` **may** depend on `uk-data`, but only as a library, and only for
   source-agnostic infrastructure: `uk_data.storage.canonical.CanonicalStore` for
   the parquet/DuckDB cache and `uk_data.utils.http` for cached HTTP with retry.
   It must not add UK-specific concepts to its own data layer.
3. Nothing in the workspace may depend on `piketty-sim`. It is a leaf.
4. New data sources for this series (WID, WIID, JST, Maddison, WPID, OECD) live
   in `piketty_sim.data`, **not** in `uk-data`. This is a deliberate, documented
   exception to the repo's "raw data retrieval lives in uk-data" layering rule:
   `uk-data` is UK-scoped by name and by the design of its `CONCEPT_REGISTRY`,
   and its canonical `TimeSeries` model is single-valued-per-timestamp, which
   fits WID's (country × year × percentile × variable) cube poorly. The
   justification is recorded in `docs/architecture.md` as part of Stage 01.

## What already exists, and what does not

Verified by exploration of the current tree:

- **No inequality metrics exist anywhere in the repo.** There is no Gini, no
  Lorenz curve, no top-share, no percentile-share and no Pareto-tail fit. The
  only mention is an unimplemented planned metric in `docs/abm-design.md:504`.
  Everything in Stage 03 is new code.
- **The existing ABM household has no wealth dynamics.** `Household._save()` in
  `packages/companies-house-abm/src/companies_house_abm/abm/agents/household.py`
  is `self.wealth += self.income - self.consumption`: no return on wealth, no
  capital income, no multiplicative shock, and therefore no `r > g` channel at
  all. There is no age, no mortality, no bequest and no OLG structure anywhere
  in the package. The Piketty engine is genuinely new.
- **Reusable by copy-adaptation**: `TargetStat` / `StatResult` /
  `EvaluationReport` (`reporting/evaluation.py:41-162`) are model-agnostic
  moment-scoring classes; `config_to_dict` / `save_config` (`abm/config.py:349`)
  are generic dataclass helpers.
- **Reusable by import**: `CanonicalStore` (`uk_data/storage/canonical.py:15`,
  with `write_parquet` / `read_parquet` / `upsert` / `query_typed`) and
  `uk_data.utils.http` (`get_json`, `get_text`, `get_bytes`, `retry`,
  `clear_cache`).
- **Reusable as a pattern**: the notebook smoke-test style in
  `tests/test_notebook.py` (importlib load + assert `app`, then
  `marimo export script` to catch `MultipleDefinitionError`); the
  offline-fallback style of `uk_data`'s bundled JSON + `source_quality`
  metadata; and the optional-native-extension style of `packages/rust-abm`
  (maturin build, `pytest.importorskip`, `unresolved-import = "warn"`).

## Target module map

Every module the programme will create, and the stage that creates it. Stage
numbers marked `+` mean an earlier stage creates the file and the later stage
extends it through a declared seam.

```
packages/piketty-sim/
├── notebooks/
│   ├── nb01_measuring_inequality.py          S06
│   ├── nb02_fundamental_laws.py              S06
│   ├── nb03_r_greater_than_g.py              S06
│   ├── nb04_u_curve.py                       S07
│   ├── nb05_inheritance.py                   S08
│   ├── nb06_wealth_tax.py                    S09
│   ├── nb07_regimes.py                       S10
│   ├── nb08_brahmin_left.py                  S11
│   ├── nb09_education_mobility.py            S12
│   ├── nb10_great_redistribution.py          S09
│   ├── nb11_participatory_socialism.py       S13
│   └── nb12_full_piketty_economy.py          S15
├── src/piketty_sim/
│   ├── config.py                             S02  + S08 S09 S10 S12 S13
│   ├── evaluation.py                         S02
│   ├── metrics/
│   │   ├── distribution.py                   S03   Lorenz, Gini, top/class shares
│   │   ├── pareto.py                         S03   Hill fit, inverted-Pareto b
│   │   └── mobility.py                       S12   transition matrices, IGE, rank-rank
│   ├── engine/
│   │   ├── results.py                        S05   WealthPanel
│   │   ├── kesten.py                         S05   simulate_wealth + laws of motion
│   │   ├── aggregates.py                     S05   beta_path, steady_state_beta, alpha
│   │   ├── shocks.py                         S07   dated interventions, capital destruction
│   │   ├── demography.py                     S08   OLG, mortality, bequests, estate tax
│   │   ├── taxes.py                          S09   progressive schedules, incidence, revenue
│   │   ├── transmission.py                   S12   Becker–Tomes human capital
│   │   ├── endowments.py                     S13   universal capital endowment
│   │   └── policy_feedback.py                S15   voting → policy → accumulation
│   ├── regimes.py                            S10   named regime presets
│   ├── reparations.py                        S10   compound-interest calculators
│   ├── politics/
│   │   ├── voters.py                         S11   voter construction from a WealthPanel
│   │   └── spatial_voting.py                 S11   two-axis mesa voting model
│   ├── calibration/
│   │   ├── targets.py                        S14   WID-derived TargetStat sets
│   │   ├── moments.py                        S14   panel → stats dict
│   │   └── sweep.py                          S14   grid search + seed stability
│   ├── data/
│   │   ├── registry.py                       S04   source registry, pinned snapshot dates
│   │   ├── schema.py                         S04   shared frame contract + validation
│   │   ├── snapshots.py                      S04   bundled-fallback access
│   │   ├── wid.py                            S04   World Inequality Database
│   │   ├── jst.py                            S04   Jordà–Schularick–Taylor
│   │   ├── maddison.py                       S04   Maddison Project
│   │   ├── wiid.py                           S04   UNU-WIDER WIID (survey contrast)
│   │   ├── appendices.py                     S07   Piketty book appendix tables
│   │   ├── oecd.py                           S09   OECD SOCX / IDD
│   │   ├── wpid.py                           S11   political cleavages database
│   │   └── bundled/*.json                    S04 +  offline snapshot extracts
│   └── _rust.py                              S15   optional accelerator shim
├── tests/                                    every stage
└── packages/rust-piketty/                    S15   separate maturin crate
```

## Stage-gate protocol

The programme is a linear chain of gated stages. **No stage may start before
every stage it depends on is `DONE`.** A stage is `DONE` only when all seven
gates below pass. Each stage document restates its stage-specific commands under
"Verification gate"; these seven are universal.

| Gate | Criterion |
|---|---|
| **G1** | Every requirement ID owned by the stage is checked off in `REQUIREMENTS.md`, with the implementing file named. The five `INV-*` invariants are re-confirmed but not ticked — they belong to the programme, not to a stage, and are ticked only at the end. |
| **G2** | Every test in the stage's test table exists, is named as specified, and passes. |
| **G3** | `make fix && make verify && make test` are clean from the repo root. Never bypass hooks with `--no-verify`. |
| **G4** | The stage's own verification commands (in its document) pass, including any numerical acceptance bands. |
| **G5** | Coupling invariant holds: `rg -e 'from companies_house' -e 'import companies_house' packages/piketty-sim/` returns nothing. |
| **G6** | Documentation named in the stage's scope table is updated (package docs page, `docs/architecture.md`, `CLAUDE.md` as applicable). |
| **G6b** | If the stage document has a "Pinned observations" / "Pinned results" section, **every row is filled in** with values from a real run. This is not optional bookkeeping: stages S08, S09, S12, S13 and S15 each have a gate criterion reading "earlier stages' pinned observations reproduce unchanged", which is unenforceable — and silently passes — if the tables were left as em-dashes. A stage that skips its pinning breaks every downstream regression check. |
| **G7** | Work is committed with the stage's Conventional Commit subject and the stage row is ticked in `ROADMAP.md`. |

Two notes on G5, both of which have already caused a defect in this document:

- **Match imports, not mentions.** The pattern targets `import` statements
  deliberately. S02 requires copy-adapted modules to name their origin in a
  docstring, and that attribution necessarily contains the string
  `companies_house`. A grep for the bare string would make honest attribution fail
  the gate; a grep for imports does not. T01-5 implements the same import-scoped
  rule.
- **Use `-e`, not `\|`.** ripgrep uses Rust regex syntax, in which `\|` is a
  *literal pipe*, not alternation. An earlier draft of this table used
  `rg -l 'companies_house_abm\|companies_house'`, which matches nothing and
  therefore passes on any tree — a gate that could never fail. Verify any change to
  this command against a file that should match before trusting it.

Two further rules apply throughout:

- **Offline by default.** Nothing in the default test run may touch the network.
  Network-dependent tests carry both `@pytest.mark.integration` and
  `@pytest.mark.network` and are excluded by `make test`.
- **Determinism.** Every simulation entry point takes an explicit seed or
  `numpy.random.Generator`. Fixed-seed runs must be reproducible bit-for-bit
  within a stage; any change that intentionally alters a seeded trajectory must
  update the affected acceptance bands in the same commit and say so in the
  commit body.

## Document index

| Doc | Stage | Owns | Depends on |
|---|---|---|---|
| `REQUIREMENTS.md` | — | All requirement IDs and traceability | — |
| `ROADMAP.md` | — | Stage sequence, status, gate summary | — |
| `01-PACKAGE-SCAFFOLD.md` | S01 | Workspace member, root tooling wiring, docs | — |
| `02-CONFIG-EVALUATION.md` | S02 | `config.py`, `evaluation.py` | S01 |
| `03-METRICS.md` | S03 | `metrics/distribution.py`, `metrics/pareto.py` | S01 |
| `04-DATA-LAYER.md` | S04 | `data/` loaders, snapshots, registry | S01 |
| `05-WEALTH-ENGINE.md` | S05 | `engine/` core: Kesten process, aggregates | S02, S03 |
| `06-NOTEBOOKS-ARC-A.md` | S06 | NB01–NB03 | S03, S04, S05 |
| `07-HISTORICAL-SHOCKS.md` | S07 | `engine/shocks.py`, `data/appendices.py`, NB04 | S05, S06 |
| `08-DEMOGRAPHY-INHERITANCE.md` | S08 | `engine/demography.py`, NB05 | S05, S06 |
| `09-FISCAL-LAYER.md` | S09 | `engine/taxes.py`, `data/oecd.py`, NB06, NB10 | S08 |
| `10-REGIMES.md` | S10 | `regimes.py`, `reparations.py`, NB07 | S09 |
| `11-POLITICAL-CLEAVAGES.md` | S11 | `politics/`, `data/wpid.py`, NB08 | S06 |
| `12-EDUCATION-TRANSMISSION.md` | S12 | `engine/transmission.py`, `metrics/mobility.py`, NB09 | S08 |
| `13-PARTICIPATORY-SOCIALISM.md` | S13 | `engine/endowments.py`, NB11 | S09, S12 |
| `14-CALIBRATION.md` | S14 | `calibration/`, seed-stability harness | S05, S04 |
| `15-CAPSTONE-RUST.md` | S15 | NB12, `packages/rust-piketty/`, `_rust.py` | all |

## Progressive elaboration

Stages 01–06 are specified to implementation depth: signatures, acceptance bands
and test assertions are fixed. Stages 07–15 are specified to design depth: the
module boundaries, seams, requirements and gate structure are fixed, but exact
numerical acceptance bands and chart specifications are to be pinned at the
start of that stage, once the engine's real behaviour is observable.

**One exception inside the implementation-depth group.** S04's source URLs and
variable codes are deliberately *not* specified: they must be looked up against each
source's own documented download interface at implementation time, because
structured identifiers copied from memory or from a planning document are
untrustworthy. That means S04 cannot be completed from this document set alone —
it needs live access to the sources — and its T04-10 gate depends on data that must
be fetched first. Plan S04 as "confirm the interface, then implement", not as a pure
coding task. S04 §7 also flags an unresolved licensing question that could force a
fetch-only mode for a given source. Pinning a
band means running the seeded reference configuration, recording the result in
the stage document, and committing that document change with the stage's work.

Wherever a stage's empirical target comes from a published figure — a book
appendix table, a WID series, an inheritance-flow estimate — the test asserts
against **the value in the pinned data snapshot**, never against a number typed
from memory into a test file. Literature values are cross-checked against the
cited source during implementation and recorded in the snapshot metadata.

**This applies to the prose of these documents too, and they do not yet fully comply.**
Several stage documents quote empirical magnitudes as orientation without a page,
table or appendix reference: the scale of the historical inheritance flow (S08 §1),
the century-long rise in tax-to-GDP and the illustrative wealth-tax band structure
(S09 §1 and §3.2), the size of the proposed universal endowment (S13 §3.1), and the
plausible range for a wealth-tail index (S05 §4). Treat every such figure as
**unverified until cited**. The first task of each of those stages is to locate the
figure in the source and either cite it precisely or remove the claim; none of them
may become a test target in the meantime.

## Honest-limitations discipline

Every notebook ends with two required callouts, tested for presence:

1. **"What the books claim vs. what the simulation shows"** — an explicit
   comparison, including where the simulation fails to reproduce the claim.
2. **Limitations** — data caveats and, where relevant, the live academic
   disputes. Specifically: the elasticity-of-substitution critique of the second
   fundamental law (NB02), and the Acemoglu–Robinson objection to "general laws"
   of capitalism (NB04). Pre-1900 series carry wide uncertainty and must be
   rendered as shaded intervals, never as point estimates.

WID (fiscal/DINA) and WIID (survey-based) disagree at the top of the
distribution. That disagreement is itself Piketty's methodological argument —
surveys miss the top tail — and gets an explicit section in NB01 rather than
being smoothed over.
