# Stage 11 — Political cleavages (NB08)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S06 |
| **Blocks** | S15 |
| **Requirements** | POL-01 … POL-05 |
| **Commit** | `feat(piketty-sim): add spatial voting model and WPID loader` |

> Specified to design depth. Bands pinned at implementation start.

## 1. Purpose

Model the political mechanism *Capital and Ideology* uses to explain why rising
inequality since 1980 has not produced rising redistributive demand: the
transformation of left parties from representing low-education, low-income voters
into representing high-education voters — the "Brahmin left" — leaving a
"merchant right" of high-income voters and no party clearly representing the
bottom of both distributions.

This is the only notebook whose subject is not wealth accumulation, and it is the
one that makes the capstone a genuine agent-based model rather than a
microsimulation. Without a political mechanism, policy is exogenous and regimes are
imposed; with one, policy responds to the distribution that policy itself produced,
and regimes can be path-dependent and emergent.

It is also, deliberately, the smallest and most legible model in the series.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/politics/__init__.py` | create | public surface |
| `src/piketty_sim/politics/voters.py` | create | voter population from a `WealthPanel` |
| `src/piketty_sim/politics/spatial_voting.py` | create | two-axis proximity voting |
| `src/piketty_sim/data/wpid.py` | create | political cleavages database |
| `notebooks/nb08_brahmin_left.py` | create | the education-gradient reversal |
| `tests/test_politics.py` | create | degenerate cases, gradient reversal |

## 3. Design

### 3.1 Voters from the engine's population

```python
@dataclass(frozen=True)
class VoterPopulation:
    income: np.ndarray       # from the panel
    wealth: np.ndarray
    education: np.ndarray    # correlated with income, correlation configurable

def voters_from_panel(
    panel: WealthPanel, *, period: int = -1,
    education_correlation: float = 0.5, rng=None,
) -> VoterPopulation
```

Education is generated as a latent attribute correlated with income at a
configurable strength, because the whole phenomenon depends on income and education
being distinct axes that can be *separately* courted. Setting the correlation to 1
collapses them and, usefully, makes the mechanism disappear — which is itself a
diagnostic the notebook can demonstrate.

Building voters from a simulated panel rather than from scratch is what lets the
capstone close the loop: distribution produces voters, voters produce policy, policy
reshapes the distribution.

### 3.2 Two-axis spatial voting

Parties occupy positions on a redistribution axis and an identity/education axis;
voters have positions on both derived from their income and education ranks; each
voter supports the nearest party under a weighted distance, optionally with a noise
term so the model is probabilistic rather than knife-edged.

```python
@dataclass(frozen=True)
class Party:
    name: str
    redistribution: float    # in [0, 1]
    identity: float          # in [0, 1]

def vote_shares(
    voters: VoterPopulation, parties: Sequence[Party], *,
    axis_weights: tuple[float, float] = (1.0, 1.0),
    noise: float = 0.0, rng=None,
) -> pl.DataFrame      # party x income_decile x education_decile shares

def gradient_by_decile(shares, *, party: str, axis: str) -> pl.DataFrame
```

`gradient_by_decile` produces exactly the chart shape WPID publishes — vote share
for a party by decile of income, and separately by decile of education — so
simulated and empirical gradients can be plotted on the same axes. That
comparability is the point of matching their presentation.

**Mesa is optional** (POL-05). The core implementation is vectorised numpy, which is
sufficient for proximity voting and keeps the package's core dependency-light. Mesa
is declared as the `politics` extra from S01 and is used only if the model gains
genuine agent interaction — coalition formation, or parties repositioning in
response to results. Start without it; the source plan's instinct that this is "the
mesa notebook" is right only if the model becomes interactive, and starting simple
is the established principle.

### 3.3 The mechanism to demonstrate

POL-03 is the substantive requirement: moving the left party's position on the
identity axis toward the high-education pole flips the sign of its education
gradient — from drawing disproportionately on low-education voters to drawing
disproportionately on high-education voters — while its income gradient weakens.
The consequence the notebook draws out is that a multi-elite party system leaves
low-income, low-education voters without representation on the redistribution axis,
which is Piketty's explanation for stalled redistributive demand despite rising
inequality.

The notebook shows this as a controllable transition, with WPID's observed
post-1948 reversal alongside it, and is careful to present the model as one
mechanism consistent with the data rather than as a demonstration that this
mechanism is what happened.

## 4. Requirements

- [ ] **POL-01** Voter population constructible from a panel, with income and education.
- [ ] **POL-02** Two-axis proximity voting; shares by income and education decile.
- [ ] **POL-03** Education-gradient reversal reproducible by moving party position.
- [ ] **POL-04** WPID loads through the data layer; NB08 compares simulated to observed.
- [ ] **POL-05** Model small-N and legible; mesa optional, not a core dependency.

## 5. Tests

`tests/test_politics.py`

| ID | Test | Assertion |
|---|---|---|
| T11-1 | `test_single_party_takes_everything` | With one party, its share is exactly 1.0 in every decile. |
| T11-2 | `test_symmetric_parties_split_evenly` | Two parties placed symmetrically about a symmetric electorate each take 0.5 within sampling tolerance. |
| T11-3 | `test_shares_sum_to_one` | Shares sum to 1.0 in every decile cell. |
| T11-4 | `test_education_gradient_reverses` | Moving the left party's identity position across its range flips the sign of its education gradient. POL-03, tested directly. |
| T11-5 | `test_income_gradient_weakens_under_reversal` | In the same sweep, the income gradient weakens — the multi-elite outcome, not merely a relabelling. |
| T11-6 | `test_perfect_correlation_collapses_mechanism` | At `education_correlation = 1.0` the two gradients are indistinguishable and the reversal cannot occur, confirming the mechanism requires two genuine axes. |
| T11-7 | `test_zero_noise_is_deterministic` | With `noise = 0.0`, results are exactly reproducible and independent of the generator. |
| T11-8 | `test_axis_weights_matter` | Down-weighting the identity axis reduces its influence on shares monotonically. |
| T11-9 | `test_no_mesa_import_at_core` | Importing `piketty_sim.politics` does not import mesa, enforcing POL-05. |

`tests/test_data_wpid.py`: offline snapshot, schema, metadata, per S04.

NB08 inherits the notebook battery plus a core-logic test.

T11-6 is the most informative test here: it shows the model's mechanism depends on
the structural feature the book identifies, rather than being an artefact of
parameter choice.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_politics.py packages/piketty-sim/tests/test_data_wpid.py -v
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty && make test
uv run python -c "import piketty_sim.politics, sys; assert 'mesa' not in sys.modules; print('mesa not imported')"
```

Pass criteria:

1. All commands exit zero; T11-4, T11-6 and T11-9 pass specifically.
2. The reversal is demonstrated numerically and the gradient values recorded in §9.
3. Simulated gradients are visually comparable in shape to WPID's observed
   gradients. Shape only — no claim of quantitative fit, and the notebook says so.
4. NB08 opened interactively; party-position sliders produce a legible, continuous
   transition rather than a discontinuous jump.

## 7. Risks

- **Overclaiming.** A proximity-voting model reproducing a stylised fact is not
  evidence that this mechanism caused it. The notebook must frame it as "a mechanism
  sufficient to generate the pattern", and the limitations callout must list what is
  absent: parties do not reposition strategically, there is no turnout decision, no
  media, no organisation, and education is synthetic.
- **Synthetic education attribute.** The correlation is a free parameter with real
  influence on results. Report sensitivity across it rather than picking one value.
- **Scope creep into a full political model.** Strategic repositioning, coalition
  bargaining and endogenous party entry are all tempting and all out of scope here.
  The capstone adds a policy feedback loop; it does not need a theory of party
  competition.

## 8. Out of scope

Endogenous policy feedback into accumulation (S15). This stage produces vote shares
given a distribution; closing the loop is the capstone's contribution.

## 9. Pinned results

*To be completed at implementation.*

| Quantity | Expected | Observed |
|---|---|---|
| Education gradient, left party at low identity position | negative | — |
| Education gradient, left party at high identity position | positive | — |
| Income gradient, low identity position | — | — |
| Income gradient, high identity position | weaker | — |
