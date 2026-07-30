# Stage 06 — Arc A notebooks (NB01–NB03)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S03, S04, S05 |
| **Blocks** | S07, S08, S11 |
| **Requirements** | NBA-01 … NBA-09 |
| **Commit** | `feat(piketty-sim): add Arc A notebooks NB01-NB03` |

## 1. Purpose

Deliver the first three notebooks, covering the analytical core of *Capital in the
Twenty-First Century*: the measurement toolkit, the two fundamental laws, and the
`r > g` wealth engine. This is the stage where the library becomes a teaching
artefact.

The pedagogical bet of the whole series is made concrete here: reactive execution
means dragging a slider re-runs the simulation and redraws the charts, so the
question "what if growth falls to 1%?" is answered by moving a control rather than
by reading a paragraph. That experience *is* the lesson, and it is why marimo
rather than a static document.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `notebooks/nb01_measuring_inequality.py` | create | measurement toolkit and its limits |
| `notebooks/nb02_fundamental_laws.py` | create | `alpha = r * beta` and `beta -> s / g` |
| `notebooks/nb03_r_greater_than_g.py` | create | the engine, interactively |
| `tests/test_notebooks.py` | create | parametrised smoke tests |
| `docs/piketty-sim-package.md` | modify | notebook index with run instructions |

## 3. Shared notebook conventions

Fixed now, because twelve notebooks are coming and consistency is what makes them
feel like a series rather than a folder.

**Structure.** Every notebook follows the same cell order: title and framing
(`mo.md`); a provenance cell printing the data snapshot date from
`snapshot_metadata`; a single parameter panel of `mo.ui` controls; the
data-loading cell; the simulation cell; chart cells; then the two required closing
callouts.

**One parameter panel.** All controls live in one cell near the top, not scattered
through the notebook. Readers should be able to see the whole control surface at
once, and reactivity handles propagation.

**Charts.** Altair only, built from polars frames via `WealthPanel.to_polars()` or
a loader frame. No matplotlib anywhere in this package — the existing root
notebooks use it, and that divergence is documented as deliberate policy in the
package docs page.

**Offline by default.** Data cells call loaders with `offline=True` unless a
control explicitly opts into a live fetch, so a notebook opened with no network
renders fully.

**No PEP 723 inline metadata.** As established in S01: the notebooks import
`piketty_sim`, which exists only in this workspace, so sandbox mode cannot resolve
it. Each notebook's header cell states the run command,
`uv run marimo edit packages/piketty-sim/notebooks/<name>.py` from the repo root.

**Two required closing callouts** (NBA-08), present in every notebook of the
series and checked by test:

1. *What the books claim vs. what the simulation shows* — including, explicitly,
   where the simulation fails to reproduce the claim.
2. *Limitations* — data caveats and live academic disputes.

**Uncertainty rendering.** Any series with `value_low` / `value_high` populated is
drawn as a shaded band, never as a confident line. Pre-1900 series in particular
carry wide error, and drawing them as point estimates would misrepresent the
evidence.

## 4. NB01 — Measuring inequality

**Concept.** The measurement toolkit Piketty builds on, and his argument for
reporting shares rather than synthetic indices.

**Cells.**

1. Distribution builder: sliders for a lognormal/Pareto mixture — lognormal
   `sigma`, Pareto tail index, mixing weight, population size.
2. Live Lorenz curve with the Gini printed alongside.
3. Class shares bar chart: bottom 50, middle 40, top 10, top 1.
4. **The dissociation demonstration** (NBA-01): two distributions with
   near-identical Ginis and materially different top-1% shares, shown side by side —
   lognormal(0, 1) against Pareto with tail index **1.46**, the value derived in S03
   §6 to make the Ginis coincide. The observed numbers come from S03's gate item 2,
   so the narrative quotes real computed values rather than asserting the phenomenon
   abstractly. This is the analytical justification for the shares-first presentation
   used throughout the series.
5. Log-log CCDF with the fitted tail overlaid, reporting `alpha` and the
   inverted-Pareto coefficient `b`, with the interpretation that average wealth
   above a threshold is `b` times that threshold.
6. Real data: WID wealth and income shares for GB, FR, US, DE, SE.
7. **WID versus WIID at the top** (NBA-02): the same country and year from both
   sources, with the gap made explicit. The narrative explains that WID combines
   fiscal, national-accounts and wealth-ranking data while WIID is survey-based,
   that surveys systematically miss the top tail, and that this disagreement is
   itself Piketty's methodological argument rather than a data quality problem to
   be averaged away.
8. Closing callouts. Limitations must state that the Hill estimator fits a tail
   index to any heavy-tailed sample and does not establish that the distribution
   *is* a power law rather than lognormal — the formal model-selection question S03
   deliberately deferred.

## 5. NB02 — The two fundamental laws

**Concept.** `alpha = r * beta` as an accounting identity, and `beta -> s / g` as
an asymptotic law.

**Cells.**

1. First law explorer: `r` and `beta` sliders producing capital's income share,
   with JST historical returns overlaid so the plausible range of `r` is visible
   rather than arbitrary.
2. Second law convergence: `beta_path` driven by `s`, `g` and `beta0` sliders, with
   the steady state `s / g` marked and the half-life annotated. At `g = 0.02` the
   half-life is 35 periods, which makes the point that low growth means both a
   higher steady state and a slower approach.
3. Decomposition of `g` into demographic and productivity components, using
   Maddison for the long-run growth record.
4. Historical panel (NBA-04): the twenty-first-century slowdown preset — growth
   falling while `r` stays comparatively stable — showing mechanically why `beta`
   rises. Presented as a preset button, not just slider positions, so the reader
   can get there in one click.
5. Closing callouts. Limitations must include (NBA-08) the
   **elasticity-of-substitution critique**: the second law's implication that a
   falling `g` raises capital's share depends on how easily capital substitutes for
   labour, and a substantial literature disputes Piketty's implicit assumption.
   The notebook states the objection rather than presenting the law as settled.

## 6. NB03 — `r > g` and the wealth engine

**Concept.** Why `r > g` is a divergence force, and why return *variance* plus
scale-dependence generates a Pareto tail.

**Cells.**

1. Parameter panel: `r_mean`, `r_std`, `g`, `s`, `wealth_retention`, `death_rate`,
   `scale_elasticity`, population size.
2. **Stationarity indicator.** Computed from the config, not guessed: display the
   drift `m = log(retention) + mu_A - log(1 + g)` and the predicted tail index from
   S05 §4, implementing S05's **two-tier stationarity rule** verbatim: a hard warning
   when `death_rate == 0` and `m >= 0` (non-stationary, fitted exponent meaningless),
   and a separate caution when `alpha <= 1` (stationary but infinite-mean, so top
   shares are wildly seed-dependent). Without this, a reader dragging sliders into
   either region sees a meaningless number presented as a result. Note the first
   condition requires **both** clauses — keying it on `m >= 0` alone fires on the
   shipped defaults, which are stationary via turnover.
3. Simulation via `simulate_wealth` at a notebook-scale config (20 000 agents,
   `record_every=5`, inside the S05 memory budget).
4. Cross-section evolution: distribution snapshots over time as small multiples or
   a ridgeline.
5. Log-log tail with fitted `alpha`, shown against the closed-form prediction —
   the notebook makes the theory-versus-simulation comparison visible, which is the
   single most convincing cell in the series.
6. Gini and top-share trajectories via `panel.metric_series`.
7. **Scale-dependence** (NBA-06): baseline versus positive `scale_elasticity` at
   the same seed, showing the tail thicken. This is Piketty's university-endowment
   observation — larger portfolios earn higher returns — and it amplifies
   concentration beyond what the `r − g` gap alone produces.
8. **Tail index against the `r − g` gap**: a small sweep via
   `dataclasses.replace`, plotted with the closed-form curve overlaid. Kept cheap
   enough to re-run interactively.
9. Comparison against WID top shares as a reality check, with the honest statement
   that this is not yet calibration — moment matching arrives in S14.
10. Closing callouts, plus a pointer to the downstream roadmap so a reader knows
    where inheritance, taxes and regimes are handled.

## 7. Requirements

- [ ] **NBA-01** NB01 demonstrates equal Gini with unequal top shares.
- [ ] **NBA-02** NB01 contrasts WID and WIID at the top and explains why.
- [ ] **NBA-03** NB02 provides both laws interactively, with half-life.
- [ ] **NBA-04** NB02 has a growth-slowdown preset.
- [ ] **NBA-05** NB03 exposes engine parameters with log-log tail and top-share trajectories.
- [ ] **NBA-06** NB03 shows scale-dependence thickening the tail and sweeps against `r − g`.
- [ ] **NBA-07** All notebooks run offline; smoke tests load and export each.
- [ ] **NBA-08** Both closing callouts in every notebook; NB02 covers the substitution critique.
- [ ] **NBA-09** Each notebook displays its data snapshot date.

## 8. Tests

`tests/test_notebooks.py`, parametrised over the notebook files so that adding a
notebook in a later stage automatically inherits the whole battery. This is why the
test is written generically now rather than per notebook.

| ID | Test | Assertion |
|---|---|---|
| T06-1 | `test_notebook_loads_as_marimo_app` | `importlib.util.spec_from_file_location` executes the module and it exposes `app`. Follows `tests/test_notebook.py:37`. |
| T06-2 | `test_notebook_exports_as_script` | `python -m marimo export script <nb>` exits zero, catching `MultipleDefinitionError` — the failure mode the existing repo test was written for. |
| T06-3 | `test_notebook_has_required_callouts` | Source contains both required closing sections, matched on stable marker strings agreed here: `## What the books claim` and `## Limitations`. Enforces NBA-08 across the series mechanically. |
| T06-4 | `test_notebook_declares_run_command` | Source contains `marimo edit`, so the header cell tells a reader how to run it. |
| T06-5 | `test_notebook_uses_no_matplotlib` | No notebook imports matplotlib, enforcing the altair policy. |
| T06-6 | `test_notebook_loads_offline` | Every loader call in the notebook source passes `offline=` explicitly — a lint-style guard against a notebook that silently needs network. |
| T06-7 | `test_notebook_shows_snapshot_date` | Source references `snapshot_metadata` or `snapshot_date` (NBA-09). |
| T06-8 | `test_nb03_core_logic_runs` | Replicates NB03's simulation at a tiny config (500 agents, 50 periods) and asserts the panel shape, a finite Gini and a finite fitted `alpha`. Mirrors the "run the notebook's core logic with a small config" pattern at `tests/test_notebook.py:73`. |
| T06-9 | `test_nb02_core_logic_runs` | `beta_path` at the notebook's preset values converges to `s / g`. |
| T06-10 | `test_nb01_dissociation_holds` | The two distributions NB01 uses do have near-equal Ginis (within 0.05) and top-1% shares differing by at least 1.5×. Guards the notebook's central claim against a future parameter edit quietly falsifying it. **Use Pareto tail index 1.46** — see S03 §6 item 2 for the derivation; 1.35 fails this test by construction, and the correct response to a failure here is to fix the parameter, never to widen the tolerance. |

T06-10 is the one to keep: it turns a narrative assertion into something CI
defends.

## 9. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty
make test
for nb in packages/piketty-sim/notebooks/nb0[123]*.py; do
  uv run python -m marimo export script "$nb" > /dev/null || echo "FAILED: $nb"
done
```

Pass criteria:

1. All commands exit zero and the export loop prints nothing.
2. Each notebook has been opened interactively at least once
   (`uv run marimo edit <nb>`), every control exercised across its range, and no
   cell errors. Automated tests cannot establish that a slider produces a sensible
   chart; a human looking at it can. Record in the commit body that this was done.
3. Offline verification: with `HTTPS_PROXY`/`HTTP_PROXY` set to an unroutable
   value, every notebook still exports and its core-logic test still passes.
4. NB03's stationarity indicator is correct at the boundary: set
   `wealth_retention = 1.0` and `death_rate = 0.0` with `r_mean > g` and confirm the
   warning appears; nudge either parameter back and confirm it clears.
5. `make docs` builds with the notebook index present.

## 10. Risks

- **Reactivity performance.** A slider that triggers a 20 000-agent, 500-period
  run on every drag makes the notebook feel broken. Mitigations: use marimo's
  debouncing on expensive controls, keep the interactive config small and offer a
  "high fidelity" button for the large run, and keep the `r − g` sweep coarse.
  Budget: no single reactive update over about two seconds.
- **`MultipleDefinitionError`.** Marimo requires each name to be defined in exactly
  one cell, which is easy to violate when copying cells between notebooks. T06-2
  catches it, which is exactly why the existing repo test was written.
- **Notebook drift from the library.** Notebooks that inline logic instead of
  importing it silently diverge from the tested modules. Rule: notebook cells
  compose library calls and build charts; they do not implement mechanisms. Any
  computation worth more than a few lines belongs in `piketty_sim` where it can be
  tested.
- **Marimo and `ty`.** The root `notebooks/` tree currently type-checks, so the new
  notebooks stay in scope. If altair or marimo stubs generate noise, add
  `"packages/piketty-sim/notebooks"` to `[tool.ty.src] exclude` — and if an
  override block is used instead, it must come after `[tool.ty.rules]`.

## 11. Out of scope

NB04 through NB12. The parametrised test design in §8 is what makes each of them a
small addition rather than a new testing problem.
