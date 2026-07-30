# Stage 12 — Education and intergenerational transmission (NB09)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S08 |
| **Blocks** | S13, S15 |
| **Requirements** | EDU-01 … EDU-04 |
| **Commit** | `feat(piketty-sim): add transmission model and mobility metrics` |

> Specified to design depth. Bands pinned at implementation start.

## 1. Purpose

Model the second transmission channel. S08 gave wealth a way to pass between
generations directly, through bequests; this stage adds the indirect route Piketty
emphasises in *Capital and Ideology* — unequal investment in children's education
reproducing position across generations even where wealth itself is taxed.

The mechanism matters because it explains why formally meritocratic societies with
substantial estate taxation still exhibit low mobility, and because it gives the
series its second policy lever: the progressivity of public education spending, as
distinct from the progressivity of taxation.

This stage also builds the mobility metrics the capstone needs, which is why it
blocks S13 and S15.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/engine/transmission.py` | create | Becker–Tomes-style human capital |
| `src/piketty_sim/metrics/mobility.py` | create | transition matrices, IGE, rank-rank |
| `src/piketty_sim/engine/demography.py` | modify | children inherit human capital at birth |
| `notebooks/nb09_education_mobility.py` | create | mobility and the Great Gatsby curve |
| `tests/test_metrics_mobility.py` | create | degenerate-case validation |
| `tests/test_engine_transmission.py` | create | mechanism behaviour |

## 3. Design

### 3.1 Transmission

Child human capital is formed from parental investment, public provision and luck,
subject to a credit constraint:

```
h_child = theta * h_parent + phi * public_spending(parent_rank) + epsilon
```

with `epsilon` a mean-zero shock and parental investment capped by the credit
constraint when parental resources are insufficient. Human capital then determines
labour income in the wealth engine, closing the loop: wealth buys education, which
buys income, which accumulates into wealth.

The credit constraint is the analytically important part. Without it, transmission
is a simple AR(1) in log human capital and public spending merely shifts the
intercept. With it, poor families cannot invest optimally even when the return to
investment is high, and public spending has a *distributional* effect rather than
only a level effect. That distinction is the entire policy argument, so the
constraint is not optional.

`public_spending(parent_rank)` implements the progressivity parameter: at zero
progressivity, spending is flat across the distribution; at positive progressivity,
spending is skewed toward lower-ranked families. Piketty's empirical observation
runs the other way in several countries — per-pupil public spending rising with
position in the academic hierarchy, which is regressive — so the parameter must
support negative values to represent that, and the notebook should show what
regressive public spending does to mobility.

### 3.2 Mobility metrics

```python
def transition_matrix(parent, child, *, n_quantiles: int = 5) -> np.ndarray
def intergenerational_elasticity(parent, child) -> float   # log-log regression slope
def rank_rank_slope(parent, child) -> float
def great_gatsby_point(panel) -> tuple[float, float]       # (inequality, immobility)
```

Three measures rather than one, because they disagree in informative ways: the
elasticity is sensitive to changes in dispersion between generations while the
rank-rank slope is not, and the transition matrix shows where in the distribution
mobility is concentrated — typically stickiness at both extremes with fluidity in
the middle, which a single scalar hides.

These have exact degenerate cases, which makes them properly testable: perfect
transmission gives an identity transition matrix, an elasticity of 1 and a
rank-rank slope of 1; random assignment gives a uniform matrix and both statistics
at 0. Any implementation that does not hit those exactly is wrong.

### 3.3 NB09

Cells: the mechanism; a parameter panel (parental elasticity, public spending level
and progressivity, credit constraint tightness); the transition matrix as a
heatmap; the three mobility statistics side by side; the effect of spending
progressivity on the elasticity; and the **Great Gatsby curve** — inequality on one
axis, immobility on the other — with the simulated economy plotted as a point that
moves as the sliders move, against the observed cross-country relationship.

The feedback into wealth is the closing cell: with transmission on, the stationary
wealth distribution is more concentrated than with transmission off at the same
parameters, because advantage now compounds through two channels instead of one.

## 4. Requirements

- [ ] **EDU-01** Human capital from parental investment, public spending and luck, with a credit constraint.
- [ ] **EDU-02** Transition matrices, IGE and rank-rank slope, validated on degenerate cases.
- [ ] **EDU-03** Increasing public-spending progressivity reduces the IGE.
- [ ] **EDU-04** NB09 places the economy on a Great Gatsby curve and feeds transmission back into wealth.

## 5. Tests

`tests/test_metrics_mobility.py`

| ID | Test | Assertion |
|---|---|---|
| T12-1 | `test_perfect_transmission_is_identity` | `child == parent` gives an identity transition matrix, IGE 1.0 and rank-rank 1.0, exactly. |
| T12-2 | `test_random_assignment_is_uniform` | Independent child and parent give a matrix of `1 / n_quantiles` within tolerance, IGE and rank-rank near 0. |
| T12-3 | `test_transition_rows_sum_to_one` | Every row sums to 1.0 to floating-point tolerance. |
| T12-4 | `test_ige_recovers_known_slope` | Data generated with a known slope recovers it within 0.02. |
| T12-5 | `test_rank_rank_invariant_to_dispersion` | Rescaling child dispersion changes the IGE but leaves the rank-rank slope unchanged — the documented difference between the measures. |
| T12-6 | `test_quantile_count_configurable` | Quintiles and deciles both work and are consistent. |

`tests/test_engine_transmission.py`

| ID | Test | Assertion |
|---|---|---|
| T12-7 | `test_transmission_off_reproduces_baseline` | Zero `parental_elasticity` reproduces S08's results bitwise at the same seed. |
| T12-8 | `test_progressive_spending_reduces_ige` | Increasing progressivity monotonically lowers the IGE across at least four points. EDU-03. `slow`. |
| T12-9 | `test_regressive_spending_raises_ige` | Negative progressivity raises it — the case Piketty documents empirically. |
| T12-10 | `test_credit_constraint_binds` | Tightening the constraint lowers investment for low-wealth families specifically, not uniformly. |
| T12-11 | `test_constraint_removal_neutralises_distribution` | With the constraint removed, public spending shifts the level of human capital but leaves the IGE close to unchanged — isolating the constraint as the source of the distributional effect. |
| T12-12 | `test_transmission_raises_concentration` | With transmission on, the stationary top-1% wealth share exceeds the transmission-off baseline. `slow`. |

T12-11 is the test that establishes the mechanism is working for the reason the
theory says, rather than producing the right sign for an incidental reason.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_metrics_mobility.py packages/piketty-sim/tests/test_engine_transmission.py -v
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty && make test
```

Pass criteria:

1. All commands exit zero; T12-1, T12-2, T12-7 and T12-11 pass specifically.
2. Earlier stages' pinned observations reproduce unchanged.
3. The simulated Great Gatsby point moves in the expected direction as
   progressivity increases, and the observed values are recorded in §9.
4. The IGE at default parameters is within the range reported in the empirical
   literature for the country being represented, or the divergence is explained in
   the notebook rather than passed over.
5. NB09 opened interactively; the heatmap and the moving Gatsby point both update
   sensibly.

## 7. Risks

- **Parameter identification.** The transmission model has several parameters and
  limited data to pin them. Mitigation: anchor `theta` to published
  intergenerational-elasticity estimates, treat the rest as explicitly exploratory,
  and report sensitivity rather than a single calibrated answer.
- **IGE versus rank-rank confusion.** Reporting one and calling it "mobility"
  invites misreading. All three measures are shown together, and T12-5 documents why.
- **Two channels becoming indistinguishable.** With both bequests and transmission
  active, attributing concentration to either requires switching one off. Keep both
  independently disableable — T12-7 depends on it, and so does any honest
  decomposition in the capstone.

## 8. Out of scope

Endogenous fertility, assortative mating, and schooling as a discrete choice. Each
would be defensible; none is necessary for the mechanism, and each adds parameters
that cannot be identified from the available data.

## 9. Pinned results

*To be completed at implementation.*

| Quantity | Expected | Observed |
|---|---|---|
| IGE, default parameters | — | — |
| IGE, high progressivity | lower | — |
| IGE, regressive spending | higher | — |
| Rank-rank slope, default | — | — |
| Top 1% share, transmission off / on | on higher | — |
