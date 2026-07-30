# Stage 09 — Fiscal layer (NB06, NB10)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S08 |
| **Blocks** | S10, S13 |
| **Requirements** | FIS-01 … FIS-07 |
| **Commit** | `feat(piketty-sim): add progressive tax and transfer layer` |

> Specified to design depth. Numerical bands pinned at implementation start.

## 1. Purpose

Implement taxation and transfers properly, and use them for two notebooks: NB06,
Piketty's global progressive capital tax, and NB10, the twentieth-century rise of
the welfare state and the emergence of a patrimonial middle class.

Both books after the first treat progressive taxation as the decisive equalising
technology — the thing that actually bent the twentieth-century curve, as against
war damage alone. This stage is therefore where the series acquires its main policy
lever, and it is what makes S10's regimes and S13's endowment proposals expressible
as parameters rather than as new code.

Two notebooks share one stage because they share one mechanism: a progressive
schedule applied to a base, with revenue accounted and incidence measured. NB06
applies it to wealth, NB10 to income plus transfers.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/engine/taxes.py` | create | bracket arithmetic, incidence, revenue |
| `src/piketty_sim/engine/kesten.py` | modify | wire `apply_taxes` to the real implementation |
| `src/piketty_sim/engine/results.py` | modify | record pre-tax and post-tax series, revenue |
| `src/piketty_sim/data/oecd.py` | create | SOCX social expenditure, IDD redistribution |
| `notebooks/nb06_wealth_tax.py` | create | the global wealth tax |
| `notebooks/nb10_great_redistribution.py` | create | 1914–1980 and the middle 40% |
| `tests/test_engine_taxes.py` | create | arithmetic, conservation, incidence |

## 3. Design

### 3.1 Bracket arithmetic

One implementation serves every instrument, since a wealth tax, an income tax and
an estate tax are the same computation over different bases:

```python
def marginal_rate(base: float, brackets: Sequence[tuple[float, float]]) -> float
def tax_due(base: ArrayLike, brackets: Sequence[tuple[float, float]]) -> np.ndarray
def effective_rate(base: ArrayLike, brackets) -> np.ndarray
```

Brackets are `(threshold, marginal_rate)` pairs sorted ascending, as declared in
S02. `tax_due` is vectorised over the whole population and computes liability
band by band, so the marginal rate above a threshold applies only to the excess —
the standard construction, and the one people get wrong by applying the top
marginal rate to the whole base.

Exposing both marginal and effective rates is a pedagogical requirement, not a
convenience: the gap between them is the single most misunderstood thing about
progressive taxation, and NB06 shows it directly.

An empty bracket tuple yields zero liability everywhere, which is what makes
FIS-07 hold and what keeps every earlier stage's seeded results intact.

### 3.2 Instruments and the period

Applied in `apply_taxes`, at the point in the period order S05 fixed — after
returns and saving, before demography:

- **Annual wealth tax** — progressive over wealth. Piketty's illustrative schedule is,
  broadly, nothing below a threshold, then a low single-digit rate, rising steeply for
  the largest fortunes — **[CITE]**, to be replaced with the exact bands from the cited
  source. Nothing depends on getting this right from memory, because the bands are the
  notebook's editable input, never a hard-coded constant.
- **Capital income tax** — flat rate on the return component.
- **Labour income tax** — progressive over labour income.
- **Transfers** — a per-capita payment, optionally financed from revenue.
- **Estate tax** — progressive, replacing S08's flat placeholder.

**Revenue accounting** is per instrument and must balance: the sum of liabilities
collected equals recorded revenue, and pre-tax wealth minus revenue plus transfers
equals post-tax wealth. This conservation check is the main correctness guard, and
it is worth stating in code as an assertion during development, because a tax that
quietly destroys wealth instead of transferring it will still produce a
plausible-looking equalisation.

### 3.3 Behavioural leakage

`TaxConfig.avoidance_elasticity`, zero by default. A single elasticity reducing the
declared base in response to the marginal rate, standing in for avoidance,
evasion and capital flight. It is deliberately crude and explicitly labelled as
such: NB06's honest answer to "would a global wealth tax actually raise this?" is
that the revenue estimate is highly sensitive to a parameter we cannot pin down,
and the notebook should let the reader move it and watch the projection change
rather than presenting a single confident number. Piketty's own argument for a
*global* tax is precisely that coordination shrinks this elasticity.

### 3.4 Pre-tax versus post-tax distributions

FIS-02 requires both from the same run. The panel records the distribution before
and after the fiscal layer each period, which is what makes fiscal-incidence
analysis possible — the redistribution achieved is the difference between two
distributions of the same population, not a comparison across two runs.

This also mirrors how WID publishes pre-tax and post-tax series, so NB10's
comparison against data is like-for-like.

### 3.5 The notebooks

**NB06 — the global wealth tax.** Fully editable bands via an array control;
resulting stationary distribution, revenue as a share of national income, and the
rate at which the top share stabilises. That last quantity is the interesting one:
there is a tax rate at which the `r > g` divergence force is exactly offset, and
finding it interactively is the notebook's payoff. Includes the leakage slider and
an explicit statement of what the model does not capture.

**NB10 — the Great Redistribution.** The century-long rise of tax-to-national-income
from a low base to a large fraction — **[CITE]**, magnitudes to be taken from the
OECD/appendix series rather than quoted here — framed through the
three-class presentation of *A Brief History of Equality*: bottom 50, middle 40,
top 10. The target phenomenon is the emergence of a **patrimonial middle class** —
the middle 40%'s wealth share rising from very little to something substantial —
as a function of redistribution intensity. Loads WID pre-tax and post-tax series
and OECD social expenditure for grounding.

## 4. Requirements

- [ ] **FIS-01** Progressive schedules over income, wealth and estates; marginal and effective rates exposed.
- [ ] **FIS-02** Pre-tax and post-tax, post-transfer distributions from one run.
- [ ] **FIS-03** Revenue accounted per instrument, reported relative to national income.
- [ ] **FIS-04** Leakage elasticity documented, zero by default.
- [ ] **FIS-05** NB06: editable bands, distribution, revenue, stabilising rate.
- [ ] **FIS-06** NB10: patrimonial middle class as a function of redistribution intensity.
- [ ] **FIS-07** All instruments zero-rated by default.

## 5. Tests

`tests/test_engine_taxes.py`

| ID | Test | Assertion |
|---|---|---|
| T09-1 | `test_bracket_arithmetic_hand_computed` | For brackets `((100, 0.10), (200, 0.20))`: base 50 owes 0; base 150 owes 5.0; base 300 owes 30.0. Hand-verified, exact. |
| T09-2 | `test_marginal_vs_effective` | At base 300 with the above schedule, marginal is 0.20 and effective is 0.10 — the gap is real and correctly reported. |
| T09-3 | `test_empty_brackets_zero_liability` | An empty tuple yields exactly zero for every base. |
| T09-4 | `test_defaults_reproduce_baseline_bitwise` | Default config reproduces S05/S08 baselines bitwise. Enforces FIS-07 and protects all earlier pinned bands. |
| T09-5 | `test_revenue_conservation` | Post-tax wealth plus revenue minus transfers equals pre-tax wealth, to floating-point tolerance, every period. |
| T09-6 | `test_threshold_boundary` | A base exactly at a threshold is taxed per the documented convention, and the convention is stated in the docstring. |
| T09-7 | `test_progressive_tax_reduces_top_share` | Raising wealth-tax progressivity monotonically lowers the stationary top-1% share across at least four points. |
| T09-8 | `test_stabilising_rate_exists` | There is a wealth-tax rate at which the top-1% share is stationary rather than trending, located by bisection — the quantity NB06 is built around. `slow`. |
| T09-9 | `test_leakage_reduces_revenue` | Positive `avoidance_elasticity` strictly reduces revenue at a given schedule, and zero elasticity leaves it unchanged. |
| T09-10 | `test_transfers_raise_bottom_share` | A per-capita transfer raises the bottom-50% share. |
| T09-11 | `test_middle_40_responds_to_redistribution` | Increasing redistribution intensity raises the middle-40% wealth share — NB10's central claim, tested. |
| T09-12 | `test_estate_brackets_supersede_flat_rate` | Progressive estate schedule reproduces S08's behaviour when given a single equivalent band. |

`tests/test_data_oecd.py`: offline, schema and metadata, mirroring S04.

NB06 and NB10 inherit the parametrised notebook battery plus core-logic tests.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_engine_taxes.py -v
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty && make test
```

Pass criteria:

1. All commands exit zero; T09-1, T09-4 and T09-5 pass specifically — hand-verified
   arithmetic, untouched baseline, and conservation.
2. S05's and S08's pinned observations reproduce unchanged.
3. The stabilising rate is located and recorded in §9, with the observation that it
   is the rate at which taxation exactly offsets the `r − g` divergence force.
4. Revenue at Piketty's illustrative schedule is reported as a share of national
   income and sanity-checked for order of magnitude against published estimates,
   with any discrepancy explained rather than absorbed.
5. Both notebooks opened interactively; the band editor in NB06 accepts arbitrary
   schedules without error, including degenerate ones (single band, zero rates).

## 7. Risks

- **Wealth destruction masquerading as redistribution.** A tax that subtracts
  without accounting looks like successful equalisation in every chart. T09-5 is the
  guard and should be treated as non-negotiable.
- **Revenue projections read as forecasts.** A simulated revenue number depends
  entirely on an unknowable behavioural elasticity. NB06 must present a range across
  the leakage slider, and state plainly that the point of the exercise is the
  distributional mechanism, not a fiscal forecast.
- **Bracket edge cases.** Off-by-one at thresholds, unsorted input, negative bases
  after a bad shock. Cover each explicitly; T09-6 documents the boundary convention.
- **Two notebooks in one stage.** If NB10 threatens to delay the gate, land NB06
  first and split NB10 into its own follow-on commit within the stage. The gate
  requires both before S10 begins.

## 8. Out of scope

Regime presets (S10), universal endowments (S13), and any general-equilibrium
response of `r` to taxation — the return process stays exogenous throughout the
series, which is a real limitation and must be stated in both notebooks' limitations
callouts.

## 9. Pinned observations

*To be completed at implementation.*

| Quantity | Expected | Observed | Note |
|---|---|---|---|
| Top-share-stabilising wealth-tax rate | — | — | T09-8, seed 42 |
| Revenue at illustrative schedule, share of national income | — | — | zero leakage |
| Revenue at same schedule, leakage 0.5 | — | — | sensitivity |
| Middle-40% share, no redistribution | — | — | NB10 baseline |
| Middle-40% share, high redistribution | — | — | NB10 |
