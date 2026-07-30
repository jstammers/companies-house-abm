# Stage 07 — Historical shocks and the U-curve (NB04)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S05, S06 |
| **Blocks** | S15 |
| **Requirements** | HST-01 … HST-05 |
| **Commit** | `feat(piketty-sim): add dated shocks and the U-curve notebook` |

> Specified to design depth. Numerical acceptance bands are pinned at the start of
> implementation, once the engine's calibrated behaviour on historical data is
> observable, and committed to §9 with the stage's work.

## 1. Purpose

Reproduce the most famous empirical object in *Capital in the Twenty-First
Century*: the U-shaped path of capital's share and the capital/income ratio across
the twentieth century — high before 1914, collapsing through two wars, inflation,
nationalisation and confiscatory taxation, then rebuilding after 1980.

The analytical value is not the replication but the counterfactual. Once the engine
can be driven with dated interventions, it becomes a counterfactual generator: we
can ask what the twentieth century would have looked like without the wars, or
without the post-1980 tax reversal, and see whether the observed U-curve requires
policy or falls out of shocks alone. That question is revisited at full strength in
the capstone.

This stage exists as a separate stage from S06 because it introduces a genuinely
new capability — historically dated, declarative interventions — that S08 through
S15 all reuse.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/engine/shocks.py` | create | declarative dated interventions |
| `src/piketty_sim/data/appendices.py` | create | Piketty book appendix tables |
| `src/piketty_sim/data/bundled/appendix_*.json` | create | pinned extracts |
| `notebooks/nb04_u_curve.py` | create | the U-curve and counterfactuals |
| `tests/test_engine_shocks.py` | create | shock semantics |
| `tests/test_data_appendices.py` | create | loader behaviour |

## 3. Design

### 3.1 Declarative shocks

Interventions are data, not code, so a notebook can toggle them individually and a
test can assert their arithmetic exactly:

```python
@dataclass(frozen=True)
class Shock:
    """A dated intervention applied to the wealth distribution."""
    name: str
    period: int
    kind: str          # "capital_destruction" | "inflation" | "tax_regime" | "nationalisation"
    magnitude: float   # interpretation depends on kind
    incidence: str = "proportional"   # "proportional" | "top_weighted" | "asset_specific"
    note: str = ""     # source/justification, surfaced in the notebook

def shock_hook(shocks: Sequence[Shock]) -> PeriodHook:
    """Compile shocks into a single engine period hook."""
```

`shock_hook` returns exactly the `PeriodHook` signature S05 defined, so the engine
needs no modification whatsoever — which is the point of having built that seam.

`incidence` matters analytically and is not decoration. Physical wartime
destruction of capital falls roughly proportionally on asset holders; inflation
falls hardest on nominal bond holders, who are not uniformly distributed across the
wealth distribution; nationalisation targets specific asset classes. Collapsing
these into a single proportional haircut would erase the distributional mechanism
the notebook is trying to show, so incidence is a first-class field with tested
behaviour per mode.

### 3.2 Historical scenario

A named scenario bundles a dated shock sequence with a time-varying parameter path,
since `r`, `g` and tax rates all changed over the century:

```python
@dataclass(frozen=True)
class HistoricalScenario:
    name: str
    start_year: int
    periods: int
    shocks: tuple[Shock, ...]
    r_path: tuple[float, ...] | None = None
    g_path: tuple[float, ...] | None = None

def build_europe_1900_2020() -> HistoricalScenario
def counterfactual(scenario, *, drop: Sequence[str]) -> HistoricalScenario
```

`counterfactual` returns the scenario with named shocks removed, which is how the
"no-war twentieth century" toggle works. Every shock's `magnitude` and `note` must
cite the appendix table or series it came from; a shock without sourcing is not
admissible, because the entire credibility of the counterfactual rests on the
baseline being defensible.

The repo has a loose precedent worth glancing at for shape — `HistoricalScenario`
and `build_uk_2013_2024()` in
`packages/companies-house-abm/src/companies_house_abm/abm/scenarios.py` — but it is
UK-housing-specific and must not be imported.

### 3.3 Appendix data

Piketty's technical appendices for each book are published as spreadsheets and are
what make *exact* figure replication possible, as opposed to approximate
reproduction from WID. `appendices.py` follows S04's loader contract exactly —
same schema, same `SourceDescriptor`, same cache/fallback order, same bundled JSON
snapshot — and adds an XLSX parsing path. Confirm redistribution terms before
committing extracts; if unclear, ship a derived series with citation rather than a
verbatim copy of the table.

### 3.4 NB04

Cells: the empirical U-curve for `beta` and capital's share, drawn with uncertainty
bands (pre-1914 series are uncertain and must not be drawn as confident lines);
the simulated path with the full shock sequence overlaid on the actual; a
per-shock toggle panel; the "no-war twentieth century" counterfactual side by side
with the actual; and an interrupted-time-series framing of the 1914 and 1980 breaks
in which the engine supplies the counterfactual trend rather than a fitted
extrapolation.

Fit is quantified, not asserted: report correlation and RMSE between simulated and
actual paths, so "the model reproduces the U-curve" is a number rather than a
visual impression.

The limitations callout must carry the **Acemoglu–Robinson critique**: that
treating `r > g` as a general law of capitalism understates the role of
institutions and political choice, and that the same data admit an
institutional reading. Given this notebook's whole method is to *impose* dated
political interventions to fit the curve, the critique is not a footnote — it is
arguably evidence for the objection, and the notebook should say so plainly rather
than defensively.

## 4. Requirements

- [ ] **HST-01** Dated interventions are declarative and applied through the hook seam.
- [ ] **HST-02** Appendix tables load with S04's snapshot, cache and fallback guarantees.
- [ ] **HST-03** NB04 reproduces the U-curve and quantifies simulated-versus-actual fit.
- [ ] **HST-04** Each shock is independently toggleable, including a no-war counterfactual.
- [ ] **HST-05** NB04 frames 1914 and 1980 as interrupted time series and carries the general-laws critique.

## 5. Tests

`tests/test_engine_shocks.py`

| ID | Test | Assertion |
|---|---|---|
| T07-1 | `test_capital_destruction_arithmetic` | A proportional destruction shock of magnitude 0.3 reduces every agent's wealth by exactly 30% in exactly the target period, and no other period. |
| T07-2 | `test_top_weighted_incidence` | Top-weighted incidence reduces the top decile's share while proportional incidence leaves it unchanged — the distributional distinction is real and tested. |
| T07-3 | `test_shock_hook_composes` | Multiple shocks in one period apply in declared order with the composed result. |
| T07-4 | `test_empty_shocks_is_identity` | A scenario with no shocks reproduces the S05 baseline **bitwise** at the same seed. Guards against the hook mechanism perturbing the random stream — the subtle failure that would silently invalidate every counterfactual comparison. |
| T07-5 | `test_counterfactual_drops_named_shocks` | `counterfactual(s, drop=["ww1"])` removes exactly that shock and leaves the rest identical. |
| T07-6 | `test_all_shocks_are_sourced` | Every shock in `build_europe_1900_2020()` has a non-empty `note`. |
| T07-7 | `test_shock_period_bounds` | A shock dated outside the horizon raises rather than being silently ignored. |

`tests/test_data_appendices.py`: offline snapshot load, schema conformance, and
metadata completeness, mirroring T04-1, T04-2 and T04-5.

`tests/test_notebooks.py`: NB04 inherits T06-1 … T06-7 automatically, plus
`test_nb04_core_logic_runs` executing a short scenario and asserting a finite
correlation against the actual series.

T07-4 is the load-bearing test. If adding a no-op hook changes the baseline
trajectory, then every "with shock versus without shock" comparison in the notebook
is confounded by an unrelated change in the random stream, and the counterfactual
means nothing.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_engine_shocks.py packages/piketty-sim/tests/test_data_appendices.py -v
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty && make test
uv run python -m marimo export script packages/piketty-sim/notebooks/nb04_u_curve.py
```

Pass criteria:

1. All commands exit zero; T07-4 passes, establishing that hooks do not disturb
   the random stream.
2. The simulated U-curve correlates with the actual `beta` series at or above the
   band pinned in §9. Pin the band by running the baseline scenario once and
   recording the value, having first satisfied yourself the scenario is defensible;
   do not tune shock magnitudes to hit a pre-chosen number and call the result a
   replication.
3. The no-war counterfactual differs materially and in the expected direction:
   removing capital destruction raises mid-century `beta` relative to the baseline.
4. Every shock's `note` cites a source, verified by reading them.
5. NB04 opened interactively, all toggles exercised, no cell errors.

## 7. Risks

- **Overfitting the century.** With enough dated shocks of free magnitude, any
  curve can be reproduced, and the exercise becomes circular. Mitigations: shock
  magnitudes must be sourced rather than fitted; the count of free parameters is
  stated explicitly in the notebook; and fit is reported numerically so a reader can
  judge whether the model is doing work.
- **Hooks perturbing the random stream.** Covered by T07-4.
- **Appendix licensing and format churn.** Handled by S04's fallback architecture;
  confirm redistribution terms before committing any extract.

## 8. Out of scope

Inheritance dynamics (S08) and tax schedules (S09), both of which this notebook
gestures at through crude shocks and which the later notebooks model properly.
NB04's tax-regime shock is a blunt instrument by design; S09 replaces it.

## 9. Pinned bands

*To be completed at implementation start.*

| Quantity | Band | Observed | Note |
|---|---|---|---|
| Correlation, simulated vs actual `beta` | — | — | baseline scenario, seed 42 |
| RMSE, simulated vs actual `beta` | — | — | same |
| Mid-century `beta`, no-war counterfactual | — | — | expected above baseline |
| Free shock parameters | — | — | count, stated in notebook |
