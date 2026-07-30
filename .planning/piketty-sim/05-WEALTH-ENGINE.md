# Stage 05 — The wealth engine

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S02, S03 |
| **Blocks** | S06, S07, S08, S14, S15 |
| **Requirements** | ENG-01 … ENG-10, INV-03 (determinism established here) |
| **Commit** | `feat(piketty-sim): add Kesten wealth engine and aggregate laws` |

## 1. Purpose

Build the generative core of the whole series: a heterogeneous-agent wealth
accumulation process whose stationary distribution has a Pareto upper tail, and
whose tail index depends on the gap between the return on wealth and the growth
rate. This is the mechanism behind Piketty's `r > g` argument, and it is the
module every later notebook imports.

This is the critical path of the programme. It also has the strongest available
verification: the process is a Kesten process, and Kesten processes have a
**closed-form prediction for the tail index**. So rather than eyeballing a
log-log plot and declaring a power law, we predict the exponent analytically and
test that the simulation reproduces it. §4 works that out.

Nothing comparable exists in the repository. The ABM's `Household._save()` is
`self.wealth += self.income - self.consumption`: no return on wealth, no capital
income, no stochastic shock, and therefore no divergence channel at all.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/engine/__init__.py` | create | re-export the public surface |
| `src/piketty_sim/engine/results.py` | create | `WealthPanel` |
| `src/piketty_sim/engine/kesten.py` | create | `simulate_wealth` and the component laws |
| `src/piketty_sim/engine/aggregates.py` | create | the two fundamental laws |
| `src/piketty_sim/__init__.py` | modify | re-export `simulate_wealth`, `WealthPanel` |
| `tests/test_engine_kesten.py` | create | determinism, tail theory, monotonicity |
| `tests/test_engine_aggregates.py` | create | the two laws, analytically |

## 3. Design

### 3.1 The law of motion

Working in levels, for agent `i` in period `t`:

```
w[i, t+1] = retention * (1 + r[i, t]) * w[i, t]  +  s * y[i] * (1 + g) ** t
```

This is a Kesten process `w' = A w + B` with a multiplicative factor
`A = retention * (1 + r)` and an additive term `B` from saved labour income. The
two terms are what produce a Pareto tail: multiplicative shocks alone give a
lognormal that spreads forever, and the additive term is what pins the lower end
and turns the stationary law into a power law.

`retention` is the fraction of gross wealth carried into the next period — one
minus the drawdown of wealth for consumption. Together with population turnover it
is what makes the process stationary; without either, `r > g` means wealth grows
without bound relative to income, which is Piketty's divergence force in its pure
form and has no stationary distribution to measure.

Note carefully that at the default parameters retention alone is **not** enough.
§4 shows the detrended log-drift is `m = +0.0043`, still mildly expansive, so
stationarity at the defaults depends on `death_rate = 0.02` as well. Descriptions
of the default configuration as having a "contractive" multiplicative factor are
wrong; the correct statement is that the *killed* process is stationary via
`(1 - d) * E[A_hat ** alpha] = 1`.

Component functions, each independently testable and each an explicit seam for a
later stage:

```python
def apply_returns(wealth, cfg, rng) -> tuple[np.ndarray, np.ndarray]
    """Return (new_wealth, capital_income) — the latter feeds national income."""
def apply_income_and_saving(wealth, income, cfg, t) -> np.ndarray   # additive
def apply_taxes(wealth, cfg) -> np.ndarray               # no-op by default; S09
def apply_demography(wealth, cfg, rng, *, ages=None) -> np.ndarray  # reset now; S08 OLG
```

`apply_demography` takes `ages` as an optional keyword defaulting to `None`, because
S05 has no age vector — reset mode does not need one. S08 introduces ages and passes
them; keeping the parameter optional now means S08 extends the signature rather than
changing it.

**Reset semantics, which materially affect the fitted tail index.** When an agent
exits in `"reset"` mode, the replacement is drawn *in detrended units* and then
expressed in period-`t` levels — that is, the replacement's wealth is
`draw * (1 + g) ** t`, not a fixed level draw. The distinction matters: a fixed
level draw becomes negligible relative to a growing economy, so the additive floor
that makes the tail Pareto would decay away and the measured `alpha` would drift with
the horizon. The replacement draw is `Lognormal(0, initial_wealth_sigma)` scaled to
mean labour income, and the replacement also receives a fresh permanent-income draw
from `IncomeConfig`. Both choices are tested for by T05-13 and are prerequisites for
§4's prediction holding at any horizon.

The per-period order is part of the contract, because later stages insert at
these points and the ordering changes the arithmetic: **returns, then income and
saving, then taxes, then demography, then user hooks.** Wealth taxes are
therefore assessed on post-return, post-saving wealth, which matches how an
annual wealth tax is levied on an end-of-year balance.

### 3.2 Return process: lognormal gross factor

The gross return factor is lognormal, moment-matched to the configured mean and
standard deviation of the net return:

```
sigma_A ** 2 = log(1 + r_std ** 2 / (1 + r_mean) ** 2)
mu_A        = log(1 + r_mean) - sigma_A ** 2 / 2
1 + r[i, t] = exp(mu_A + sigma_A * z[i, t]),   z ~ N(0, 1)
```

Two reasons for lognormal rather than a normal draw on `r`. First, the gross
factor is positive by construction, so wealth cannot go negative through a return
shock and the `r_floor` truncation is not needed on the default path — truncation
would bias the tail, which is precisely what we are trying to measure. Second, it
makes `log A` exactly normal, which is what gives us the closed-form tail index in
§4 instead of a numerical approximation.

**Return scale-dependence** (Piketty's observation that larger portfolios earn
higher returns) shifts the mean of the log return with relative wealth:

```
mu[i, t] = mu_A + scale_elasticity * (log w[i, t] - log median(w[:, t]))
```

Zero by default, so the baseline is the clean textbook process and any tail
thickening is visibly attributable to switching it on.

`wealth_retention` is declared by S02 with a default of `0.98`. The reason it is not
`1.0` is §4: with retention exactly 1, `r > g` and no turnover, the process has no
stationary distribution. Changing that default — or `death_rate` — invalidates this
stage's acceptance bands and requires re-deriving them.

### 3.3 `WealthPanel`

```python
@dataclass
class WealthPanel:
    wealth: np.ndarray            # (n_recorded, n_agents)
    income: np.ndarray            # (n_recorded, n_agents), labour income
    capital_income: np.ndarray    # (n_recorded, n_agents), return flow on wealth
    recorded_periods: np.ndarray  # (n_recorded,)
    config: WealthEngineConfig

    def final_cross_section(self) -> np.ndarray
    def metric_series(self, fn: Callable[[np.ndarray], float]) -> np.ndarray
    def to_polars(self) -> pl.DataFrame     # long format, altair-ready
    def detrended(self) -> np.ndarray       # wealth / (1 + g) ** t
    def national_income(self) -> np.ndarray # (n_recorded,) aggregate, see below
    def beta(self) -> np.ndarray            # (n_recorded,) wealth / national income
```

`metric_series` is the composition point with S03: `panel.metric_series(gini)` or
`panel.metric_series(lambda w: top_share(w, 0.01))` gives a trajectory of any
cross-sectional statistic, so the engine never needs to know which metrics exist.

`detrended` matters analytically, not cosmetically. In levels, wealth grows with
`g` forever and has no stationary distribution; in units of contemporaneous
average labour income it does. Every stationarity and tail claim in this document
is about the detrended series, and `detrended()` is what the tests and notebooks
use so that distinction is explicit rather than assumed.

### 3.3a National income and `beta` — defined once, here

Four separate requirements depend on a national-income aggregate — ENG-08's
`alpha = r * beta`, S08's inheritance identity `b_y = mu * m * beta`, S09's
revenue-relative-to-national-income (FIS-03), and S14's `beta` moment (CAL-01) — so
it is defined here and nowhere else:

```
national_income[t] = sum_i labour_income[i, t] + sum_i capital_income[i, t]
beta[t]            = sum_i wealth[i, t] / national_income[t]
```

Capital income is the return flow, `(r[i, t]) * w[i, t]`, which is why
`apply_returns` returns it separately rather than folding it into the wealth update.
This is a closed economy with no depreciation and no government production, so
national income is simply labour plus capital income — an approximation, and one the
notebooks must state, since Piketty's national income is net of capital depreciation.

**Two distinct quantities are both called `s`, and conflating them is a real hazard
because NB02 and NB03 put both on sliders.** They are not the same number and must
not be wired to the same control:

| Symbol | Where | Meaning |
|---|---|---|
| `SavingsConfig.rate` | the engine | micro: saved share of an agent's **labour** income |
| the `s` argument of `steady_state_beta` / `beta_path` | `aggregates.py` | macro: saving out of **national** income, as in Piketty's second law |

`aggregates.py` deliberately takes its `s` as a bare function argument rather than
reading it from the config, precisely so the two cannot be silently unified. A
notebook wishing to relate them must compute the macro rate from a run — aggregate
saving over national income — rather than assuming they are equal.

### 3.4 Entry point

```python
def simulate_wealth(
    config: WealthEngineConfig,
    *,
    rng: np.random.Generator | None = None,
    record_every: int = 1,
    period_hooks: Sequence[PeriodHook] = (),
) -> WealthPanel:
    """Simulate a heterogeneous-agent wealth process."""
```

`rng` defaults to `np.random.default_rng(config.seed)`, matching the repo's
seeding convention. `period_hooks` are
`Callable[[np.ndarray, int, np.random.Generator], None]` applied last each
period, which is how S07 injects dated war and policy shocks without the engine
knowing anything about history.

**Memory budget** (ENG-09): the panel holds
`n_arrays * n_agents * ceil(periods / record_every) * 8` bytes, where `n_arrays` is
3 (wealth, labour income, capital income). Worked values:

| Config | Arithmetic | Size |
|---|---|---|
| **Default** (10 000 agents, 500 periods, `record_every=1`) | `3 × 10_000 × 500 × 8` | **120 MB** |
| Reference notebook (20 000 agents, 500 periods, `record_every=5`) | `3 × 20_000 × 100 × 8` | **48 MB** |

The default is far too large to hold casually in a notebook kernel, so
`simulate_wealth`'s docstring states the formula and the default `record_every`
warrants review during implementation: consider defaulting it to 5, or emitting a
warning above a size threshold. Long runs and sweeps must record sparsely. T05-14
asserts the reference configuration stays under 64 MB.

(An earlier draft of this section stated 16 MB for the reference configuration and
counted only two arrays. Both were wrong — recompute rather than trusting a quoted
figure.)

### 3.5 `aggregates.py` — the two fundamental laws

Deterministic, agent-free, and used by NB02:

```python
def alpha_from_r_beta(r: float, beta: float) -> float
    """First law: capital's share of income, alpha = r * beta."""

def steady_state_beta(s: float, g: float) -> float
    """Second law: the asymptotic capital/income ratio, s / g."""

def beta_path(beta0: float, s: float, g: float, periods: int) -> np.ndarray
    """Iterate beta[t+1] = (beta[t] + s) / (1 + g)."""

def convergence_half_life(g: float) -> float
    """Periods for a deviation from steady state to halve: log(2) / log(1 + g)."""
```

The recursion's fixed point is `s / g`, and the deviation from it contracts by a
factor `1 / (1 + g)` per period — so the half-life is `log(2) / log(1 + g)`,
independent of `s` and of the starting point. At `g = 0.02` that is 35.0 periods,
which is the concrete fact NB02 uses to make the point that low growth means both
a higher steady-state capital/income ratio *and* a slower approach to it.

## 4. Analytic acceptance criterion: the tail index

This section is the stage's backbone. Detrend by dividing through by
`(1 + g) ** t`; the detrended multiplicative factor is

```
A_hat = retention * (1 + r) / (1 + g)
log A_hat ~ Normal(m, v ** 2)
m = log(retention) + mu_A - log(1 + g)
v = sigma_A
```

For a Kesten process with a per-period survival probability `1 - d` (agents exit
at rate `d` and are replaced at the initial draw), the stationary upper tail is
Pareto with index `alpha` solving

```
(1 - d) * E[A_hat ** alpha] = 1
```

With `log A_hat` normal, `E[A_hat ** alpha] = exp(alpha * m + alpha ** 2 * v ** 2 / 2)`,
so `alpha` is the positive root of
`alpha ** 2 * v ** 2 / 2 + alpha * m + log(1 - d) = 0`:

```
alpha = (-m + sqrt(m ** 2 - 2 * v ** 2 * log(1 - d))) / v ** 2
```

Sanity checks this satisfies: at `d = 0` it reduces to `alpha = -2 * m / v ** 2`,
the classical condition, which is positive only when `m < 0` — contraction on
average in logs, the standard stationarity requirement. As `m` rises toward zero
(a wider `r − g` gap) `alpha` falls and the tail fattens. As return volatility `v`
rises with `m` fixed, `alpha` falls. Both are Piketty's claims, in closed form.

**The stationarity rule NB03 must implement.** Read straight off the formula, in two
tiers — and note the first tier is *not* simply `m >= 0`:

1. **Non-stationary (hard warning, fitted `alpha` is meaningless).** Only when
   `death_rate == 0` **and** `m >= 0`. When `death_rate > 0` the term
   `-2 * v ** 2 * log(1 - d)` is strictly positive, so the discriminant exceeds
   `m ** 2`, the square root exceeds `abs(m)`, and the numerator is positive for any
   sign of `m`. Turnover alone guarantees a stationary tail. This is why the default
   configuration is stationary despite `m = +0.0043`, and why a rule keyed on
   `m >= 0` alone would fire spuriously on the shipped defaults.
2. **Stationary but pathological (caution).** When `alpha <= 1` the stationary
   distribution has infinite mean; sample top shares will be wildly seed-dependent
   and any reported average is not meaningful. Warn separately.

**Pinned reference configuration.** Defaults from S02 plus
`wealth_retention = 0.98`: `r_mean = 0.05`, `r_std = 0.10`, `g = 0.02`,
`death_rate = 0.02`.

| Quantity | Value |
|---|---|
| `sigma_A ** 2` | 0.0090292 |
| `mu_A` | 0.0442756 |
| `m` | 0.0042703 |
| `alpha` (predicted) | **1.695** |
| `b = alpha / (alpha - 1)` | 2.44 |

A tail index near 1.7 is in the vicinity of published estimates for wealth
distributions in advanced economies, but treat that as a loose plausibility note and
**nothing more**. It is not independent evidence: the defaults were chosen, `alpha`
was derived from them, and the derived value was then judged plausible — which is
circular. Published wealth-tail estimates also vary substantially by country, period
and whether the underlying source is estate, survey or rich-list data. Before this
sentence is used to justify any parameter choice, replace it with a specific cited
estimate for a specific country and method, or delete it. S14 is where the defaults
get confronted with data properly.

**Second reference case, exact formula.** With `death_rate = 0` and
`wealth_retention = 0.97`, `m = -0.0059864` and `alpha = -2 * m / v ** 2 = 1.326`.
This case tests the classical `d = 0` branch with no killing-model approximation,
so it carries a tighter tolerance.

**Tolerances, calibrated against a trial run.** The gap between prediction and fit
comes from finite-sample effects, not from the tail condition being approximate:
`(1 - d) * E[A_hat ** alpha] = 1` is the standard discrete-time condition for a
killed random-difference equation, and applies exactly here. What biases the *fitted*
value downward is (a) the Hill estimator's well-known finite-sample bias and (b)
contamination of the fitted region by recently regenerated agents, whose wealth is
not yet drawn from the stationary tail. Both push the same way, and a prototype run
confirms they do:

| Case | Predicted | Fitted (prototype) | Gap | Band |
|---|---|---|---|---|
| Reference, `d = 0.02`, retention 0.98 | 1.695 | 1.532 | −0.163 | **±0.20** |
| `d = 0`, retention 0.97 | 1.326 | 1.259 | −0.067 | **±0.10** |

Prototype conditions: 200 000 agents, 3 000 periods, detrended, single seed 42,
`tail_fraction = 0.05`, reset draws from `Lognormal(0, 1)`. These figures are
indicative — a prototype, not the implementation — but the **direction and rough
magnitude of the bias are reliable**, and the bands above are set from them rather
than guessed. The reference band is the wider of the two precisely because the
killing correction is the cruder approximation.

Two rules when a run lands outside its band. First, check the sign: the bias is
expected to be *negative*, so a fitted value **above** the prediction is a stronger
signal of a bug than one below it. Second, **do not widen a band without
re-deriving** — an off-by-one in when mortality is applied relative to returns
shifts `alpha` in exactly this direction and magnitude, and that is the specific bug
these bands exist to catch. If widening is genuinely warranted, record the reason
and the new prototype evidence in §10.

## 5. Requirements

- [ ] **ENG-01** `simulate_wealth` returns a `WealthPanel`.
- [ ] **ENG-02** Law of motion decomposed into four independently testable functions.
- [ ] **ENG-03** `period_hooks` allow dated interventions without engine edits.
- [ ] **ENG-04** `WealthPanel` exposes final cross-section, metric series, long frame.
- [ ] **ENG-05** Fitted tail index matches the §4 closed form within tolerance.
- [ ] **ENG-06** Widening `r − g` monotonically raises stationary top shares.
- [ ] **ENG-07** Return scale-dependence thickens the tail versus baseline.
- [ ] **ENG-08** The two fundamental laws implemented; `beta_path` converges at the analytic rate.
- [ ] **ENG-09** Memory formula documented; reference config inside budget.
- [ ] **ENG-10** National income and `beta` defined once (§3.3a) and exposed on the panel; capital income tracked separately; the two senses of `s` documented.

## 6. Tests

`tests/test_engine_kesten.py`

| ID | Test | Assertion |
|---|---|---|
| T05-1 | `test_determinism_same_seed` | Two runs at one seed produce bitwise-identical wealth arrays (`np.array_equal`). |
| T05-2 | `test_different_seed_differs` | A different seed produces a different panel, guarding against an accidentally fixed draw. |
| T05-3 | `test_panel_shapes` | Shapes follow `record_every`; `recorded_periods` matches the recorded axis. |
| T05-4 | `test_tail_index_matches_theory_with_mortality` | Reference config: fitted `alpha` within **0.20** of **1.695**, and *below* it (the bias direction is asserted, not just the magnitude). `slow`. |
| T05-5 | `test_tail_index_matches_theory_no_mortality` | `d = 0`, retention 0.97: fitted `alpha` within **0.10** of **1.326**. `slow`. |
| T05-6 | `test_top_share_monotone_in_r_minus_g` | Sweeping `r_mean` upward with `g` fixed gives non-decreasing stationary top-1% share across at least five points. `slow`. |
| T05-7 | `test_scale_elasticity_thickens_tail` | Positive `scale_elasticity` lowers fitted `alpha` and raises the top-1% share versus the baseline at the same seed. |
| T05-8 | `test_explosive_config_does_not_converge` | With retention 1.0 and `d = 0` under `r > g`, the detrended top share keeps rising rather than settling — documenting that this configuration has no stationary distribution instead of silently reporting a meaningless fitted exponent. |
| T05-9 | `test_period_hooks_called` | A recording hook is invoked once per period with the wealth array, the period index and the generator; mutations it makes persist. |
| T05-10 | `test_taxes_and_demography_neutral_at_defaults` | `apply_taxes` is the identity at default config; with `death_rate = 0`, `apply_demography` leaves wealth untouched. Protects CFG-04 at the engine level. |
| T05-11 | `test_metric_series_composes` | `panel.metric_series(gini)` has length equal to the recorded axis and values in `[0, 1]`. |
| T05-12 | `test_to_polars_round_trip` | Long frame has `n_recorded * n_agents` rows, expected columns, and no nulls. |
| T05-13 | `test_detrended_removes_growth` | With `r_std = 0` and no mortality, detrended mean wealth is constant to floating-point tolerance while level mean wealth grows. |
| T05-14 | `test_memory_budget_documented` | The reference notebook config's panel is under 64 MB via `panel.wealth.nbytes + panel.income.nbytes + panel.capital_income.nbytes`. |

`tests/test_engine_aggregates.py`

| ID | Test | Assertion |
|---|---|---|
| T05-15 | `test_alpha_identity` | `alpha_from_r_beta(0.05, 6.0) == pytest.approx(0.30)`. Use `approx`, not `==`: in IEEE 754 `0.05 * 6.0` is `0.30000000000000004`, so the exact comparison fails. |
| T05-16 | `test_steady_state_beta` | `steady_state_beta(0.10, 0.02) == 5.0`. |
| T05-17 | `test_beta_path_converges_to_steady_state` | From several starting points, `beta_path` approaches `s / g` and the final value is within 1e-6 over a long horizon. |
| T05-18 | `test_beta_path_contraction_rate` | Successive deviations from `s / g` shrink by exactly `1 / (1 + g)`. |
| T05-19 | `test_half_life` | `convergence_half_life(0.02) ≈ 35.0`; the path's deviation halves in that many periods. |
| T05-20 | `test_low_growth_raises_beta` | Halving `g` roughly doubles the steady state — the mechanical core of NB02's slowdown preset. |

Tests T05-4, T05-5 and T05-6 carry `@pytest.mark.slow`. They must still run in the
default suite (`make test` excludes only `integration`), so they need to be
tolerable: budget under 60 seconds each, and prefer fewer periods with more agents
since the tail estimate is limited by cross-sectional tail count, not by run
length once stationarity is reached.

## 7. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_engine_kesten.py -v
uv run pytest packages/piketty-sim/tests/test_engine_aggregates.py -v
make test-piketty
make test
```

Pass criteria:

1. All commands exit zero, including the three `slow` theory tests.
2. The closed form and the simulation agree, checked by hand and recorded in the
   commit body:
   ```bash
   uv run python -c "
   import numpy as np
   from dataclasses import replace
   from piketty_sim.config import WealthEngineConfig
   from piketty_sim.engine import simulate_wealth
   from piketty_sim.metrics import fit_pareto_tail, gini, top_share
   cfg = replace(WealthEngineConfig(), n_agents=50_000, periods=2_000)
   p = simulate_wealth(cfg, record_every=100)
   w = p.detrended()[-1]
   f = fit_pareto_tail(w, tail_fraction=0.05)
   print(f'alpha={f.alpha:.3f} (predicted 1.695)  b={f.inverted_beta:.2f}')
   print(f'gini={gini(w):.3f} top1={top_share(w, 0.01):.3f} top10={top_share(w, 0.10):.3f}')"
   ```
   Record the observed `alpha`, Gini and top shares in this document under a
   "Pinned observations" note, committed with the stage. These become the reference
   values that later stages' regression tests compare against.
3. Stationarity is real, not assumed: the top-1% share over the last quarter of a
   reference run has a coefficient of variation under 0.05. If it does not, the run
   is too short and the horizon must be extended before pinning anything.
4. `rg -e 'from companies_house' -e 'import companies_house' packages/piketty-sim/` returns nothing.
5. Coverage of `engine/` at or above 90%.

## 8. Risks

- **Mistaking a lognormal for a power law.** A purely multiplicative process gives
  a lognormal that looks straight-ish on log-log axes over a limited range. The
  additive term is what makes the tail genuinely Pareto, and the §4 prediction is
  what distinguishes "looks linear" from "has the predicted exponent". T03-14
  already documents that the Hill estimator will happily fit a lognormal, so the
  numerical agreement in T05-4 is the real evidence.
- **Ordering bugs inside the period.** Applying mortality before returns rather
  than after shifts the effective survival probability and moves `alpha`. The
  documented order in §3.1 and the tight bands in T05-4/T05-5 are the guard;
  §4 explicitly warns against widening a band to accommodate this.
- **Non-stationary configurations.** Users will drag sliders into the explosive
  region, and a fitted exponent there is meaningless. T05-8 pins the behaviour, and
  NB03 must display a stationarity warning computed from the config rather than
  guessed, using the **two-tier rule** below.
- **Slow tests eroding the suite.** This stage adds three `slow` tests, but the
  programme schedules about twelve across all stages (T05-4/5/6, T08-5, T09-8,
  T10-2/3/4, T12-8/12, T13-6, T14-9), all of which run in the default suite since
  `make test` excludes only `integration`. Three at a minute each is fine; twelve is
  a five-minute default suite and a real tax on the G3 gate. **Programme-level
  policy:** keep each `slow` test under 60 seconds, and if the default suite exceeds
  roughly three minutes, introduce a `slow`-excluded fast target
  (`pytest -m "not integration and not slow"`) for local iteration while keeping the
  full suite as the gate. Do not silently drop the theory tests — they are the
  strongest verification the programme has. Keep the theory tests to the two reference cases
  plus the monotonicity sweep, and put anything more exploratory in the S14
  calibration harness where it belongs.

## 9. Out of scope

Age structure, bequests and estate taxation (S08); progressive tax schedules and
transfers (S09); dated historical shocks (S07, which uses the `period_hooks` seam
this stage provides). Those are why the component functions and hook mechanism
exist now, but this stage implements none of them.

## 10. Pinned observations

*To be completed during implementation, per gate item 2.*

The "prototype" column below records a throwaway pre-implementation run used only to
set the §4 bands. Replace the "observed" column with real values from the
implemented engine at the gate; if they differ materially from the prototype,
investigate before adjusting anything.

| Quantity | Predicted | Prototype | Observed | Seed / config |
|---|---|---|---|---|
| `alpha`, reference | 1.695 | 1.532 | — | 42, defaults, 200k × 3000 |
| `alpha`, `d = 0` | 1.326 | 1.259 | — | 42, retention 0.97 |
| Gini, reference | — | — | — | 42 |
| Top 1% share, reference | — | — | — | 42 |
| Top 10% share, reference | — | — | — | 42 |
