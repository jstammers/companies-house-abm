# Stage 03 — Inequality metrics

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S01 |
| **Blocks** | S05, S06 |
| **Requirements** | MET-01 … MET-06 |
| **Commit** | `feat(piketty-sim): add Lorenz, Gini, share and Pareto-tail metrics` |

## 1. Purpose

Build the measurement toolkit that every notebook in the series reports through.
This is entirely new code: the repository contains no Gini, no Lorenz curve, no
top-share and no tail-fitting utility. The only trace is an unimplemented planned
metric in `docs/abm-design.md:504`.

The stage also encodes a substantive point of Piketty's method. He is sceptical of
synthetic indices like the Gini, which compress the whole distribution into one
number and thereby hide what is happening at the top, and prefers reporting
**shares** of clearly-named groups. The module therefore treats distributional
shares as the primary output and the Gini as one summary among several — and NB01
demonstrates the failure mode directly by constructing distributions with equal
Ginis and different top shares.

Because these functions are pure, deterministic and analytically checkable, this
stage has unusually strong tests: nearly every function is verified against a
closed-form result rather than a regression snapshot. That matters, because every
later stage's acceptance criteria are expressed in terms of these metrics. If the
Gini is subtly wrong, every downstream band is wrong too.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/metrics/__init__.py` | create | flat re-export surface for notebook ergonomics |
| `src/piketty_sim/metrics/distribution.py` | create | Lorenz, Gini, shares |
| `src/piketty_sim/metrics/pareto.py` | create | tail fitting, inverted-Pareto coefficient |
| `src/piketty_sim/__init__.py` | modify | re-export the common names |
| `tests/test_metrics_distribution.py` | create | analytic verification |
| `tests/test_metrics_pareto.py` | create | estimator recovery and consistency |

## 3. Design

### 3.1 `metrics/distribution.py`

```python
Negatives = Literal["keep", "clip", "raise"]

def lorenz_curve(
    values: ArrayLike, *, negatives: Negatives = "keep"
) -> tuple[np.ndarray, np.ndarray]:
    """Return cumulative population share and cumulative value share."""

def gini(values: ArrayLike, *, negatives: Negatives = "keep") -> float:
    """Gini coefficient via the sorted-index formula."""

def top_share(values: ArrayLike, fraction: float) -> float:
    """Share of the total held by the top `fraction` of holders."""

def bottom_share(values: ArrayLike, fraction: float) -> float:
    """Share of the total held by the bottom `fraction` of holders."""

def wealth_shares(
    values: ArrayLike,
    *,
    cuts: Sequence[float] = (0.5, 0.9, 0.99),
) -> dict[str, float]:
    """Piketty's presentational classes: bottom 50, middle 40, top 10, top 1."""
```

`gini` uses the sorted-index identity
`G = (2 * sum(i * x_i) - (n + 1) * sum(x)) / (n * sum(x))` for `x` sorted
ascending with `i` one-based: O(n log n), numerically stable, and exact on the
degenerate cases.

`wealth_shares` returns keys named for what they are — `bottom_50`, `middle_40`,
`top_10`, `top_1` — because these labels are the vocabulary of *A Brief History of
Equality*, and the middle-40% share is the specific quantity that S09 tracks to
show a patrimonial middle class emerging. The default cut points produce exactly
those four groups; the `cuts` parameter generalises them.

### 3.2 Negative and zero values

Wealth distributions genuinely contain negative net worth, and this breaks the
textbook definitions: the Lorenz curve dips below zero and loses convexity, and
the Gini can exceed one. Rather than pretend otherwise, handling is explicit:

- `lorenz_curve` and `gini` accept a `negatives` policy — `"keep"` (default,
  faithful, may exceed the unit box), `"clip"` (floor at zero) or `"raise"`.
- The default is `"keep"`, so nothing is silently altered, and the docstrings
  state that convexity and the `[0, 1]` bound hold only for non-negative input.
- Total value of exactly zero returns `nan` rather than raising, so a metric
  series over a collapsing simulation degrades visibly instead of crashing a
  notebook mid-run.

This is MET-06, and it is worth the explicitness: silent clipping would quietly
distort every bottom-50% share once S08's bequest mechanics allow indebted agents.

### 3.3 `metrics/pareto.py`

```python
@dataclass(frozen=True)
class ParetoFit:
    alpha: float          # tail index
    inverted_beta: float  # Piketty's b = alpha / (alpha - 1)
    xmin: float           # threshold above which the fit was taken
    n_tail: int           # observations in the tail
    se_alpha: float       # asymptotic standard error, alpha / sqrt(n_tail)

def fit_pareto_tail(
    values: ArrayLike,
    *,
    tail_fraction: float = 0.10,
    xmin: float | None = None,
) -> ParetoFit:
    """Fit a power-law tail by the Hill (conditional MLE) estimator."""

def inverted_pareto_beta(alpha: float) -> float:
    """Piketty's inverted-Pareto coefficient."""

def ccdf(values: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Empirical complementary CDF, for log-log tail plots."""
```

The Hill estimator is `alpha = n_tail / sum(log(x_i / xmin))` over observations
above `xmin`, with asymptotic standard error `alpha / sqrt(n_tail)`. When `xmin`
is not supplied it is the `1 - tail_fraction` quantile.

The **inverted-Pareto coefficient** `b = alpha / (alpha - 1)` is chosen as a
first-class output because it is the quantity Piketty actually reports, and it has
a directly interpretable meaning that gives us a free consistency test: for a
Pareto tail, the average wealth of everyone above a threshold equals `b` times
that threshold. So `b` can be estimated two ways — from the fitted `alpha`, and
by directly computing mean-above-threshold divided by threshold — and the two must
agree. That is T03-11, and it validates the estimator and the interpretation
together.

`ccdf` exists because NB01 and NB03 both plot tails on log-log axes, and doing
the survival-function bookkeeping once, correctly, is better than twice in
notebook cells.

### 3.4 Sampling trap to avoid in tests

`numpy.random.Generator.pareto(a)` draws from the **Lomax** (Pareto type II)
distribution, supported on `[0, inf)` with survival `(1 + x)**(-a)` — not the
Pareto type I with survival `(x / xmin)**(-a)` that the analytic formulas below
assume. Tests must draw type I explicitly, either as `1.0 + rng.pareto(a)` or via
inverse transform `(1 - rng.random(n)) ** (-1 / a)`. Getting this wrong produces
tests that fail for a reason that has nothing to do with the code under test, so
the helper belongs in `tests/conftest.py` as a single fixture used everywhere.

## 4. Analytic reference values

These closed forms are the acceptance criteria. Pareto type I with tail index
`a > 1` and scale 1; `Phi` is the standard normal CDF.

| Quantity | Closed form |
|---|---|
| Gini, all values equal | `0` |
| Gini, one holder of `n` | `(n - 1) / n` |
| Gini, Uniform(0, 1) | `1 / 3` |
| Gini, Lognormal(mu, sigma) | `2 * Phi(sigma / sqrt(2)) - 1` |
| Gini, Pareto(a) | `1 / (2 * a - 1)` |
| Lorenz, Pareto(a) | `L(p) = 1 - (1 - p) ** ((a - 1) / a)` |
| Top share, Pareto(a) | `S(p) = p ** ((a - 1) / a)` |
| Inverted Pareto | `b = a / (a - 1)` |
| Mean above threshold y, Pareto(a) | `b * y` |

Sanity checks these encode: the top-share formula gives `S(p) = p` as `a → inf`
(perfect equality) and `S(p) → 1` as `a → 1` (total concentration), and the
Lognormal Gini rises monotonically from 0 with `sigma`.

Tolerances: exact cases (equality, single holder, Lorenz endpoints) assert
equality to floating-point precision. Sampled cases use `n = 200_000`, a fixed
seed, and an absolute tolerance of `0.005` for Gini and shares. Tail-index
recovery uses `n = 200_000` with `tail_fraction = 0.10` and an absolute tolerance
of `0.05` on `alpha`.

## 5. Requirements

- [ ] **MET-01** `lorenz_curve` anchored, monotone, convex on non-negative input.
- [ ] **MET-02** `gini` matches all five analytic cases within tolerance.
- [ ] **MET-03** `top_share` / `wealth_shares` give the four Piketty classes, summing to 1.
- [ ] **MET-04** `fit_pareto_tail` recovers a known exponent and reports threshold, count and standard error.
- [ ] **MET-05** `inverted_pareto_beta` consistent with `top_share` and with mean-above-threshold.
- [ ] **MET-06** Negative and zero handling documented and tested.

## 6. Tests

`tests/test_metrics_distribution.py`

| ID | Test | Assertion |
|---|---|---|
| T03-1 | `test_gini_equality_is_zero` | Exactly `0.0` for any constant array. |
| T03-2 | `test_gini_single_holder` | Exactly `(n - 1) / n`. |
| T03-3 | `test_gini_uniform` | `≈ 1/3` at n = 200 000, atol 0.005. |
| T03-4 | `test_gini_lognormal_closed_form` | Matches `2 * Phi(sigma / sqrt(2)) - 1` for sigma in {0.5, 1.0, 1.5}. |
| T03-5 | `test_gini_pareto_closed_form` | Matches `1 / (2a - 1)` for a in {1.5, 2.0, 3.0}. |
| T03-6 | `test_lorenz_endpoints_and_shape` | Starts (0,0), ends (1,1), non-decreasing, convex (non-negative second differences) on non-negative input. |
| T03-7 | `test_lorenz_pareto_closed_form` | Curve matches `1 - (1-p)**((a-1)/a)` at p in {0.1,…,0.9}. |
| T03-8 | `test_top_share_pareto_closed_form` | `top_share(x, p) ≈ p ** ((a-1)/a)`. |
| T03-9 | `test_wealth_shares_sum_to_one` | The four class shares sum to `1.0` within 1e-12, on both synthetic and degenerate inputs. |
| T03-10 | `test_negative_and_zero_policies` | `"clip"` floors at zero; `"raise"` raises; `"keep"` may exceed 1 and is documented; all-zero total returns `nan` without raising. |

`tests/test_metrics_pareto.py`

| ID | Test | Assertion |
|---|---|---|
| T03-11 | `test_inverted_beta_matches_mean_above_threshold` | `b` from the fitted alpha agrees with empirical mean-above-threshold over threshold, rtol 0.02. The key cross-validation of estimator and interpretation. |
| T03-11b | `test_inverted_beta_consistent_with_top_share` | On synthetic Pareto data, the fitted alpha reproduces `top_share(x, p) ≈ p ** ((a - 1) / a)` for p in {0.01, 0.10}, tying `pareto.py` and `distribution.py` together. Required by MET-05, which asks for consistency with `top_share` specifically — T03-11 alone only checks mean-above-threshold. |
| T03-12 | `test_hill_recovers_known_alpha` | Fitted alpha within 0.05 of true a in {1.5, 2.0, 2.5}. |
| T03-13 | `test_fit_reports_tail_metadata` | `xmin` equals the requested quantile, `n_tail ≈ tail_fraction * n`, `se_alpha ≈ alpha / sqrt(n_tail)`. |
| T03-14 | `test_lognormal_is_not_read_as_thin_pareto` | On lognormal data the fit still returns finite, positive values and does not raise — documenting that Hill fits *any* tail and that discriminating power-law from lognormal is a separate question, flagged for NB01's narrative. |
| T03-15 | `test_ccdf_is_monotone_decreasing` | `ccdf` is non-increasing, starts at 1, and has matching array lengths. |
| T03-16 | `test_fit_requires_enough_tail` | Too few tail observations raises a clear `ValueError` rather than returning a meaningless estimate. |

## 7. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_metrics_distribution.py packages/piketty-sim/tests/test_metrics_pareto.py -v
make test-piketty
make test
```

Pass criteria:

1. All commands exit zero; every analytic case in §4 has a passing test.
2. Manual spot check of the Gini/top-share dissociation that NB01 is built on —
   two distributions, near-equal Gini, materially different top 1%:
   ```bash
   uv run python -c "
   import numpy as np
   from piketty_sim.metrics import gini, top_share
   rng = np.random.default_rng(42)
   a = rng.lognormal(0.0, 1.0, 200_000)
   b = (1 - rng.random(200_000)) ** (-1 / 1.46)
   for name, x in (('lognormal', a), ('pareto', b)):
       print(f'{name:10s} gini={gini(x):.3f} top1={top_share(x, 0.01):.3f}')"
   ```
   **The Pareto tail index must be 1.46, not 1.35.** The closed forms in §4 fix this
   exactly: lognormal(0, 1) has Gini `2 * Phi(1 / sqrt(2)) - 1 = 0.5205`, and
   Pareto(a) has Gini `1 / (2a - 1)`, so matching Ginis requires
   `a = (1 / 0.5205 + 1) / 2 = 1.4606`. At `a = 1.35` the Gini is 0.5882 — a gap of
   0.068, which **fails** the 0.05 tolerance that NB01's T06-10 asserts. At
   `a = 1.46` the gap is 0.0003 and the top-1% shares still differ by roughly 2.5×
   (about 0.234 versus 0.092), comfortably clearing the 1.5× requirement.

   This is worth dwelling on because it is exactly the trap §8 warns about: the
   tempting fix on seeing T06-10 fail is to widen the tolerance, which destroys the
   claim the test exists to defend. The tolerance is right; the parameter was wrong.
   Record the observed numbers in the NB01 narrative.
3. Coverage of both metrics modules at or above 95%.
4. Runtime of the metrics test files under 30 seconds combined; if the 200 000-draw
   cases push past that, lower to 100 000 and widen tolerances to 0.008 rather
   than leaving a slow default suite.

## 8. Risks

- **Lomax-versus-Pareto sampling.** Discussed in §3.4; the shared fixture is the
  mitigation. This is the single most likely source of confusing test failures in
  the stage.
- **Convexity assertions on sampled data.** Empirical Lorenz curves from finite
  samples can show tiny non-convexities from floating-point noise. Assert with a
  small negative tolerance (`>= -1e-12`) rather than strict non-negativity.
- **Tolerance theatre.** Tolerances wide enough to pass anything prove nothing.
  The values in §4 are tight enough that a genuinely wrong formula fails; do not
  widen them to make a failing test pass without understanding why it failed.

## 9. Out of scope

Mobility metrics — transition matrices, intergenerational elasticity, rank-rank
slopes — belong to S12 and land in `metrics/mobility.py`. Formal
power-law-versus-lognormal model selection (likelihood-ratio testing in the
Clauset–Shalizi–Newman style) is deliberately deferred; T03-14 documents the
limitation so NB01 can discuss it honestly rather than overclaiming what the Hill
estimator establishes.
