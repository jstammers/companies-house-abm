# Requirements — piketty-sim

Requirement IDs are stable. Tick a box only when the implementing file exists,
its tests pass, and the owning stage's gate has been cleared. The "Implemented
in" column is filled in at tick time.

## Cross-cutting invariants

These are re-verified at **every** stage gate, not once. Their checkboxes are
therefore *not* owned by any single stage: they are ticked when the programme
finishes, and each stage's G1 check re-confirms them without claiming them. A stage
header listing an INV id (S01 lists three, S05 lists INV-03) means that stage is
where the invariant is first *established* and given an executable test — not that
later stages are exempt from it.

- [ ] **INV-01**: No module under `packages/piketty-sim/` imports
      `companies_house_abm` or `companies_house`.
- [ ] **INV-02**: The default test run (`make test`) completes with no network
      access; every network-touching test carries both `integration` and
      `network` markers.
- [ ] **INV-03**: Every simulation entry point accepts an explicit seed or
      `numpy.random.Generator`, and fixed-seed runs reproduce bit-for-bit.
- [ ] **INV-04**: Every public function and class carries a NumPy-style
      docstring; every module begins with `from __future__ import annotations`.
- [ ] **INV-05**: `make fix`, `make verify` and `make test` are clean before
      every commit; pre-commit hooks are never bypassed.

## Stage 01 — Package scaffold

- [ ] **PKG-01**: `packages/piketty-sim/` is a uv workspace member that
      `uv sync` resolves, exposing an importable `piketty_sim` package with
      `py.typed`.
- [ ] **PKG-02**: Ruff lints and formats the new package's `src`, `tests` and
      `notebooks` trees, with marimo-specific per-file ignores applied to the
      package's own notebook directory.
- [ ] **PKG-03**: `ty` type-checks the new package's `src` tree; the package's
      `tests` tree is excluded, consistent with existing packages.
- [ ] **PKG-04**: Root pytest collects `packages/piketty-sim/tests`, and
      `piketty_sim` appears in coverage reporting.
- [ ] **PKG-05**: `make test-piketty` and `make test-piketty-integration` exist
      and run the package's unit and integration tests respectively; `make test`
      and `make test-integration` include the package.
- [ ] **PKG-06**: Bundled package data under `src/piketty_sim/data/bundled/` is
      tracked by git despite the repository-wide `data/` ignore rule, and ships
      in the built wheel.
- [ ] **PKG-07**: The package declares no dependency on `companies_house_abm`;
      its only workspace dependency is `uk-data`, pinned via
      `[tool.uv.sources]`.
- [ ] **PKG-08**: `docs/piketty-sim-package.md` exists, is listed in
      `mkdocs.yml` nav, and `make docs` builds it; `docs/architecture.md` and
      `CLAUDE.md` describe the package and its coupling rule, including the
      documented exception to the uk-data data-retrieval layering rule.

## Stage 02 — Config and evaluation

- [ ] **CFG-01**: Engine parameters are expressed as frozen, nested dataclasses
      aggregated by `WealthEngineConfig`, with `field(default_factory=...)` for
      nested defaults.
- [ ] **CFG-02**: `config_to_dict`, `save_config` and `load_config` round-trip a
      `WealthEngineConfig` through YAML without loss.
- [ ] **CFG-03**: Configs are immutable; counterfactual variants are produced
      with `dataclasses.replace` and never by mutation.
- [ ] **CFG-04**: Default parameter values are economically neutral where a
      later stage owns the mechanism: zero tax rates, zero return
      scale-dependence, no endowment. Enabling a later mechanism requires
      changing a parameter, never editing engine code.
- [ ] **CFG-05**: `TargetStat`, `StatResult` and `EvaluationReport` provide
      declarative moment targets and weighted scoring, decoupled from any
      simulation result type; provenance of the copy-adaptation is recorded in
      the module docstring.
- [ ] **CFG-06**: `evaluate_stats(stats: dict[str, float], targets) ->
      EvaluationReport` scores a plain statistics mapping, so any producer —
      Python engine, Rust kernel or notebook cell — can be evaluated.

## Stage 03 — Inequality metrics

- [ ] **MET-01**: `lorenz_curve` returns cumulative population and value shares,
      anchored at (0, 0) and (1, 1), monotonically non-decreasing and convex for
      non-negative input.
- [ ] **MET-02**: `gini` matches closed-form values for the analytic cases
      (equality, single holder, uniform, lognormal, Pareto) within documented
      tolerance.
- [ ] **MET-03**: `top_share` and `wealth_shares` report Piketty's presentational
      classes — bottom 50%, middle 40%, top 10%, top 1% — summing to 1.
- [ ] **MET-04**: `fit_pareto_tail` recovers a known Pareto exponent from
      synthetic samples and reports the tail threshold, tail count and a
      standard error alongside the estimate.
- [ ] **MET-05**: `inverted_pareto_beta` implements Piketty's inverted-Pareto
      coefficient and is consistent with `top_share` on synthetic Pareto data.
- [ ] **MET-06**: Negative and zero values have documented, tested handling;
      Gini and Lorenz behaviour on inputs containing negative wealth is explicit
      rather than incidental.

## Stage 04 — Data layer

- [ ] **DAT-01**: Each source loader returns a `polars.DataFrame` with a
      declared, tested schema, and every row carries a `source_quality` value of
      `live`, `cached` or `static`.
- [ ] **DAT-02**: Every source has a pinned snapshot date and pinned request
      URLs recorded as module constants and surfaced in the returned frame's
      metadata.
- [ ] **DAT-03**: Loaders accept an optional `CanonicalStore`; on a live fetch
      they write a parquet cache, and on a subsequent call they read the cache
      instead of the network.
- [ ] **DAT-04**: Every loader supports `offline=True` and falls back to a
      bundled snapshot automatically when a live fetch fails, tagging the result
      `static`.
- [ ] **DAT-05**: Bundled snapshots are committed as JSON with metadata
      recording source URL, download date, licence and coverage.
- [ ] **DAT-06**: No loader downloads a bulk archive; requests are scoped to the
      series the notebooks consume.
- [ ] **DAT-07**: WID, JST, Maddison and WIID loaders exist and cover the
      countries and series the Arc A notebooks require.
- [ ] **DAT-08**: Series carrying wide historical uncertainty expose the
      information needed to render uncertainty bands, rather than point
      estimates alone.

## Stage 05 — Wealth engine

- [ ] **ENG-01**: `simulate_wealth(config, *, rng, record_every, period_hooks)`
      simulates a heterogeneous-agent wealth process and returns a `WealthPanel`.
- [ ] **ENG-02**: The per-period law of motion is decomposed into independently
      testable pure functions for returns, income and saving, taxes, and
      demography, so later stages replace a component without touching the loop.
- [ ] **ENG-03**: A `period_hooks` sequence allows notebooks to inject dated
      interventions without modifying engine code.
- [ ] **ENG-04**: `WealthPanel` exposes the final cross-section, a metric time
      series for any cross-sectional statistic, and a long-format polars frame.
- [ ] **ENG-05**: For a configuration with a stationary detrended distribution,
      the fitted tail exponent matches the closed-form killed-Kesten prediction
      `(1 - d) * E[A_hat ** alpha] = 1` within documented tolerance, and in the
      documented (downward) direction. Note the condition includes the survival
      factor: `E[A_hat ** alpha] = 1` is only the special case `d = 0`, and the
      default configuration is *not* that case — its multiplicative factor is
      mildly expansive and stationarity comes from turnover.
- [ ] **ENG-06**: Widening the gap between the mean return and the growth rate
      monotonically increases stationary top shares over the tested range.
- [ ] **ENG-07**: Enabling return scale-dependence — returns rising in wealth —
      thickens the tail relative to the scale-neutral baseline.
- [ ] **ENG-08**: `steady_state_beta`, `beta_path` and `alpha_from_r_beta`
      implement Piketty's two fundamental laws, with `beta_path` converging to
      `s/g` at the analytic rate.
- [ ] **ENG-09**: Memory use is bounded and documented: `record_every` controls
      panel size, and the reference notebook configuration runs within the
      documented time and memory budget.
- [ ] **ENG-10**: A national-income aggregate and the capital/income ratio `beta`
      are defined once in the engine and exposed on the panel, with capital income
      tracked separately from labour income. Every later use of "national income"
      or `beta` — the first fundamental law, the inheritance identity, revenue as a
      share of national income, and the calibration moments — refers to this one
      definition, and the distinction between saving out of labour income and
      saving out of national income is documented.

## Stage 06 — Arc A notebooks

- [ ] **NBA-01**: NB01 demonstrates that identical Gini coefficients can conceal
      different top shares, motivating a shares-first presentation, and fits
      synthetic tails.
- [ ] **NBA-02**: NB01 contrasts WID with WIID at the top of the distribution and
      explains the methodological disagreement.
- [ ] **NBA-03**: NB02 provides an interactive explorer for `alpha = r * beta`
      and for convergence of `beta` to `s/g`, including convergence half-life.
- [ ] **NBA-04**: NB02 includes a preset reproducing the twenty-first-century
      growth slowdown and its mechanical implication for `beta`.
- [ ] **NBA-05**: NB03 exposes the engine's parameters as interactive controls
      and displays the emergent tail on log-log axes alongside top-share
      trajectories.
- [ ] **NBA-06**: NB03 shows tail thickening under return scale-dependence and a
      sweep of fitted tail exponent against the `r − g` gap.
- [ ] **NBA-07**: Every notebook runs end-to-end offline and is exercised by a
      smoke test that loads it as a marimo app and exports it as a script.
- [ ] **NBA-08**: Every notebook ends with a "books claim vs. simulation shows"
      callout and a limitations note; NB02 covers the
      elasticity-of-substitution critique.
- [ ] **NBA-09**: Each notebook records the data snapshot date it relies on.

## Stage 07 — Historical shocks and the U-curve

- [ ] **HST-01**: Dated interventions — capital destruction, inflation episodes,
      tax-regime changes, nationalisation — are declarative objects applied
      through the engine's hook seam.
- [ ] **HST-02**: Piketty appendix tables load through the data layer with the
      same snapshot, caching and fallback guarantees as other sources.
- [ ] **HST-03**: NB04 reproduces the twentieth-century U-curve in capital's
      share and the capital/income ratio, and quantifies simulated-versus-actual
      fit.
- [ ] **HST-04**: NB04 supports toggling each shock independently, including a
      "no-war twentieth century" counterfactual.
- [ ] **HST-05**: NB04 frames the 1914 and 1980 breaks as interrupted time
      series with the engine as counterfactual generator, and includes the
      general-laws critique as an honest sidebar.

## Stage 08 — Demography and inheritance

- [ ] **OLG-01**: The engine supports an age structure with mortality, so agents
      are born, accumulate and die.
- [ ] **OLG-02**: Death transfers wealth as a bequest under a configurable
      estate-tax schedule and a configurable division rule, conserving wealth
      net of tax.
- [ ] **OLG-03**: The realised inheritance flow measured from the simulation
      reconciles with the accounting identity relating it to decedents' relative
      wealth, the mortality rate and the capital/income ratio.
- [ ] **OLG-04**: NB05 reproduces the U-shaped path of the inheritance flow and
      reports the share of inherited wealth in total wealth.
- [ ] **OLG-05**: NB05 includes a life-trajectory comparison between top labour
      income and top inherited wealth by cohort.
- [ ] **OLG-06**: Bequests are off by default, so Stage 05's seeded results are
      unchanged when the mechanism is disabled.

## Stage 09 — Fiscal layer

- [ ] **FIS-01**: Progressive schedules over arbitrary bracket sets apply to
      income, wealth and estates, with marginal and effective rates both
      exposed.
- [ ] **FIS-02**: A tax-and-transfer layer produces pre-tax and post-tax,
      post-transfer distributions from the same run.
- [ ] **FIS-03**: Revenue is accounted per instrument and reported relative to
      national income.
- [ ] **FIS-04**: Behavioural leakage — avoidance or capital flight — is a
      documented elasticity parameter, zero by default.
- [ ] **FIS-05**: NB06 exposes fully editable wealth-tax bands and reports the
      resulting steady-state distribution, revenue, and the rate at which the top
      share stabilises.
- [ ] **FIS-06**: NB10 reproduces the rise of a patrimonial middle class as a
      function of redistribution intensity, tracked through the three-class
      shares.
- [ ] **FIS-07**: All fiscal instruments are zero-rated by default, preserving
      earlier stages' seeded results.

## Stage 10 — Regimes

- [ ] **REG-01**: Named regime presets — ternary, slave, colonial, proprietarian,
      social-democratic, hypercapitalist — are constructors returning engine
      configurations, with documented sourcing for each parameter.
- [ ] **REG-02**: Each preset runs to a stationary state and presets can be
      compared side by side on identical metrics.
- [ ] **REG-03**: Compound-interest calculators for compensated abolition and the
      Haitian indemnity are implemented as auditable functions with cited
      inputs.
- [ ] **REG-04**: NB07 allows selecting a preset and then editing any parameter,
      supporting a "design your own regime" workflow.

## Stage 11 — Political cleavages

- [ ] **POL-01**: A voter population is constructible from a simulated wealth
      panel, carrying both an income and an education attribute.
- [ ] **POL-02**: A two-axis spatial voting model assigns votes by proximity to
      party positions and reports vote shares by income and education decile.
- [ ] **POL-03**: The model can reproduce a reversal of the education gradient in
      left voting as party positions move on the identity axis.
- [ ] **POL-04**: WPID data loads through the data layer and NB08 compares
      simulated gradients against it.
- [ ] **POL-05**: The voting model is small-N, rule-transparent and legible; it
      may use mesa, and if so mesa is an optional extra rather than a core
      dependency.

## Stage 12 — Education and transmission

- [ ] **EDU-01**: Child human capital is a function of parental investment,
      public spending and luck, subject to a credit constraint.
- [ ] **EDU-02**: Mobility metrics — quintile transition matrices,
      intergenerational elasticity and rank-rank slope — are implemented and
      validated against the degenerate cases of perfect transmission and pure
      randomness.
- [ ] **EDU-03**: Increasing the progressivity of public education spending
      reduces the intergenerational elasticity in the simulation.
- [ ] **EDU-04**: NB09 places the simulated economy on a Great-Gatsby-curve
      diagram and feeds transmission outcomes back into the wealth distribution.

## Stage 13 — Participatory socialism

- [ ] **PSO-01**: A universal capital endowment can be paid at a configurable age
      and funded from a configurable mix of wealth and inheritance taxation, with
      the budget identity enforced and reported.
- [ ] **PSO-02**: NB11 shows distributional dynamics over multiple generations
      and compares outcomes against both the status quo and the pure wealth-tax
      world of NB06.
- [ ] **PSO-03**: Endowment and funding parameters are zero by default.

## Stage 14 — Calibration and validation

- [ ] **CAL-01**: WID-derived target sets are declared as `TargetStat`
      collections with documented provenance and tolerances.
- [ ] **CAL-02**: A moments function maps a `WealthPanel` to the statistics
      dictionary the target sets score against.
- [ ] **CAL-03**: A grid sweep evaluates a parameter grid and ranks
      configurations by weighted score, reporting the best.
- [ ] **CAL-04**: A seed-stability harness reports run-to-run variation of key
      metrics across seeds at a given population size, and the documented
      workflow requires stability at small scale before scaling up.
- [ ] **CAL-05**: Calibration runs are reproducible from a committed
      configuration file plus a seed.

## Stage 15 — Capstone and Rust kernel

- [ ] **CAP-01**: NB12 composes the full model — heterogeneous households, age
      structure, labour and capital income, scale-dependent stochastic returns,
      inheritance, education transmission and endogenous policy — with regimes
      emerging from the political feedback loop rather than being imposed.
- [ ] **CAP-02**: The capstone answers its three experimental questions: whether
      war-scale shocks alone can produce twentieth-century equalisation; whether
      a regime transition retraces its path in reverse; and how sensitive
      outcomes are to the `r − g` gap.
- [ ] **CAP-03**: Validation discipline is followed and evidenced: small
      population first, minimum agents per stratum, seed stability demonstrated
      before scaling.
- [ ] **CAP-04**: An optional Rust kernel is a drop-in replacement behind the
      Python engine's signature, built out-of-workspace via maturin, and skipped
      cleanly when not built.
- [ ] **CAP-05**: Python and Rust kernels agree within documented numerical
      tolerance on matched inputs, and the speed-up is measured and recorded.

## Out of scope

- Any change to existing ABM behavioural logic, agents, markets or configuration.
- Migrating existing root-level notebooks into the new package.
- Adding non-UK data sources to `uk-data`.
- Publishing the package to an index, or deploying notebooks as hosted apps
  beyond documenting the local `marimo run` and WASM-export paths.
- Replacing the repo's existing calibration or sweep machinery.

## Traceability

| Stage | Requirement IDs |
|---|---|
| S01 | PKG-01 … PKG-08 |
| S02 | CFG-01 … CFG-06 |
| S03 | MET-01 … MET-06 |
| S04 | DAT-01 … DAT-08 |
| S05 | ENG-01 … ENG-10 |
| S06 | NBA-01 … NBA-09 |
| S07 | HST-01 … HST-05 |
| S08 | OLG-01 … OLG-06 |
| S09 | FIS-01 … FIS-07 |
| S10 | REG-01 … REG-04 |
| S11 | POL-01 … POL-05 |
| S12 | EDU-01 … EDU-04 |
| S13 | PSO-01 … PSO-03 |
| S14 | CAL-01 … CAL-05 |
| S15 | CAP-01 … CAP-05 |
| all | INV-01 … INV-05 |
