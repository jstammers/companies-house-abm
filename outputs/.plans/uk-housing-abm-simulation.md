# Deep Research Plan: UK Housing ABM Simulation

**Slug:** uk-housing-abm-simulation
**Date:** 2026-04-21
**Objective:** Investigate agent-based models (ABMs) for simulating UK housing market dynamics — house prices, mortgage lending, defaults — under external shocks, and propose a commercially viable simulation product for mortgage lenders, housing planners, investors, and central banks.

---

## Key Questions

1. **Existing ABMs for UK housing:** What ABMs have been built to model UK house prices, mortgage markets, and housing transactions? Who built them (academic, BoE, central banks)?
2. **Agent types & market mechanisms:** What agent types (households, banks, developers, investors, government) and market clearing mechanisms are used? How are expectations, search, and matching modelled?
3. **Mortgage & default modelling:** How do existing ABMs represent mortgage origination, LTV/LTI constraints, interest rate pass-through, affordability stress, and default/arrears?
4. **House Price Index (HPI) replication:** Can ABMs reproduce stylised facts of UK HPI — spatial heterogeneity, boom-bust cycles, mean reversion, regional divergence?
5. **External factor transmission:** How do ABMs transmit macro shocks (interest rates, unemployment, inflation, immigration, planning policy, Help to Buy, stamp duty changes) into housing outcomes?
6. **Calibration & validation:** What data sources (Land Registry, ONS, FCA PSD, BoE, English Housing Survey) and calibration methods are used? How is out-of-sample validation done?
7. **Commercial viability:** What scenario-planning tools exist commercially (Moody's, Oxford Economics, CoreLogic)? What gap does an ABM-based product fill? What are barriers to adoption (trust, explainability, speed)?
8. **Proposed model architecture:** Based on evidence, what agent types, market modules, data pipelines, and scenario interface would a viable product need?

## Evidence Needed

- Academic papers: UK housing ABMs (Baptista et al. / BoE staff papers, Ge / Axtell MASON models, Carro et al., Geanakoplos leverage cycle ABM, Pangallo et al.)
- Central bank working papers: BoE, ECB housing ABM work
- Existing commercial tools: Moody's Analytics HPA, Oxford Economics Housing Model, CoreLogic, Nationwide/Halifax HPI methodology
- UK housing data landscape: Land Registry Price Paid, ONS HPI, FCA PSD001/PSD007, English Housing Survey, BoE mortgage stats
- ABM platforms: MASON, Mesa, Agents.jl, FLAME, performance considerations for large-scale spatial ABM
- Regulatory context: PRA stress testing (mortgage portfolio), FPC macroprudential tools (LTV/LTI limits)

## Scale Decision

**Broad multi-domain research → 4 researcher subagents**

Rationale: This spans (a) academic ABM literature, (b) UK housing data & commercial tools, (c) mortgage/default modelling, (d) ABM engineering & calibration. Decomposition clearly helps.

## Task Ledger

| ID | Owner | Topic | Output File | Status |
|----|-------|-------|-------------|--------|
| T1 | researcher | UK housing ABM academic literature (papers, models, findings) | `uk-housing-abm-simulation-research-T1.md` | PENDING |
| T2 | researcher | UK housing data landscape, commercial scenario tools, regulatory context | `uk-housing-abm-simulation-research-T2.md` | PENDING |
| T3 | researcher | Mortgage/default modelling in ABMs, stress testing, macro shock transmission | `uk-housing-abm-simulation-research-T3.md` | PENDING |
| T4 | researcher | ABM calibration methods, validation approaches, platform/engineering considerations | `uk-housing-abm-simulation-research-T4.md` | PENDING |
| D1 | lead | Draft synthesis & model proposal | `outputs/.drafts/uk-housing-abm-simulation-draft.md` | PENDING |
| V1 | verifier | Citation verification | `outputs/.drafts/uk-housing-abm-simulation-cited.md` | PENDING |
| R1 | reviewer | Verification review | `uk-housing-abm-simulation-verification.md` | PENDING |

## Verification Log

| Check | Result | Date |
|-------|--------|------|
| Plan created | ✅ | 2026-04-21 |
| Evidence gathered | ✅ (18 queries, 7 fetches, direct mode) | 2026-04-21 |
| Draft written | ✅ | 2026-04-21 |
| Citations verified | ✅ (34 sources, all referenced) | 2026-04-21 |
| Review passed | ✅ PASS WITH NOTES (3 MINOR) | 2026-04-21 |
| Final artifacts on disk | ✅ (5/5 files confirmed) | 2026-04-21 |

## Decision Log

| Decision | Rationale |
|----------|-----------|
| 4 subagents | Topic spans academic lit, data/commercial landscape, mortgage modelling, and ABM engineering — each is a distinct research domain |
| Paper-style output to `papers/` | User wants a model proposal — this is a paper-style deliverable |
| Focus on UK specifics | User explicitly scoped to UK housing market, HPI, UK mortgage lending |
