# Stage 08 — Demography and inheritance (NB05)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S05, S06 |
| **Blocks** | S09, S12 |
| **Requirements** | OLG-01 … OLG-06 |
| **Commit** | `feat(piketty-sim): add OLG demography and inheritance flows` |

> Specified to design depth. Numerical bands pinned at implementation start.

## 1. Purpose

Give the engine a real demographic overlay: agents have ages, they die, and their
wealth passes to the next generation under an estate-tax schedule. This turns the
reset-based turnover of S05 into overlapping generations, and it unlocks the
mechanism Piketty treats as central to long-run concentration — inheritance.

The empirical target is the U-shaped path of the inheritance flow: roughly a tenth
or more of national income in the nineteenth century, collapsing to a small
fraction by mid-twentieth century, then rising again. If a model of wealth
inequality cannot produce that, it is missing the transmission channel that makes
wealth concentration self-perpetuating rather than merely persistent.

This stage is also the first to carry a strong **accounting identity** as an
acceptance test, which makes it unusually verifiable for a behavioural extension.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/engine/demography.py` | create | ages, mortality, bequests, estate tax |
| `src/piketty_sim/engine/kesten.py` | modify | route `apply_demography` to OLG when enabled |
| `src/piketty_sim/engine/results.py` | modify | record ages and bequest flows in the panel |
| `notebooks/nb05_inheritance.py` | create | inheritance flows and the rentier |
| `tests/test_engine_demography.py` | create | mortality, conservation, the identity |

## 3. Design

### 3.1 Age structure and mortality

`DemographyConfig.mode` switches from `"reset"` to `"olg"`. In OLG mode the panel
carries an age vector; mortality is age-dependent via a supplied hazard schedule
rather than a flat rate, because a flat hazard produces an exponential age
distribution with implausibly many very old agents, and the age profile of
decedents is precisely what determines the inheritance flow.

Mortality tables come in as a simple array of hazards by age band, sourced and
cited. Each death creates a bequest event; the population is held at constant size
by birth of a new agent, so cohort size effects are deliberately excluded at this
stage (fertility becomes a control in the notebook, but the default keeps the
population stationary so that distributional changes are attributable to
transmission rather than to demographic composition).

### 3.2 Bequests and estate taxation

On death: wealth is taxed under `TaxConfig.estate_tax_brackets` (declared in S02,
implemented properly in S09 — until then a flat rate suffices), then divided
according to `bequest_division`:

- `"single"` — one heir receives the whole estate, maximally concentrating.
- `"equal_split"` — divided among a configurable number of heirs, diluting.

The division rule is not a detail. Partible versus impartible inheritance is one of
the institutional variables *Capital and Ideology* treats as constitutive of a
regime, so S10's presets will vary it, and the mechanism must be in place and
tested here.

**Conservation is the invariant**: total wealth after a bequest event equals total
wealth before, minus estate tax collected. Any deviation is a bug, and it is easy
to introduce one when heirs are selected with replacement or when a dying agent's
wealth is both transferred and reset.

### 3.3 The inheritance-flow identity

Piketty decomposes the annual inheritance flow as a share of national income into

```
b_y = mu * m * beta
```

where `m` is the mortality rate, `beta` the wealth-to-income ratio, and `mu` the
ratio of average wealth of decedents to average wealth of the living. This is an
accounting identity, so a correct simulation must satisfy it: measure `b_y`
directly as realised bequests over national income, measure `mu`, `m` and `beta`
from the same run, and the two sides must agree within sampling error.

That is OLG-03 and it is the strongest test available in this stage — it validates
the mortality model, the bequest mechanics and the wealth accounting
simultaneously, and it will fail loudly if, for example, mortality is applied
before returns so that decedents' recorded wealth is stale.

`mu` above 1 is the interesting case and the reason the flow can be large: the
dying are older and therefore wealthier than the living on average. A model that
produces `mu` near 1 has failed to generate a realistic wealth-age profile, which
is itself worth surfacing in the notebook.

### 3.4 NB05

Cells: the mechanism explained; a parameter panel for `mu`-relevant controls
(mortality schedule, fertility, estate-tax rate, division rule); the simulated
inheritance-flow path against the historical U-shape; the share of inherited
wealth in total wealth; and a **"Rastignac's dilemma" calculator** comparing
lifetime resources from top labour income against top inherited wealth by cohort —
the device Piketty borrows from Balzac to make the stakes concrete, and which
answers "in which historical periods was it rational to marry into money rather
than work?" as a computed answer per cohort.

## 4. Requirements

- [ ] **OLG-01** Age structure with mortality; agents born, accumulate, die.
- [ ] **OLG-02** Bequests under an estate-tax schedule and a division rule, conserving wealth net of tax.
- [ ] **OLG-03** Measured inheritance flow reconciles with `b_y = mu * m * beta`.
- [ ] **OLG-04** NB05 reproduces the U-shaped flow and reports inherited share of total wealth.
- [ ] **OLG-05** NB05 includes the labour-versus-inheritance life-trajectory comparison.
- [ ] **OLG-06** Bequests off by default; S05's seeded results unchanged when disabled.

## 5. Tests

`tests/test_engine_demography.py`

| ID | Test | Assertion |
|---|---|---|
| T08-1 | `test_olg_disabled_reproduces_baseline` | With `mode="reset"`, the panel is **bitwise identical** to S05's baseline at the same seed. Directly enforces OLG-06 and protects every band pinned in S05. |
| T08-2 | `test_wealth_conserved_net_of_estate_tax` | Total wealth before and after a bequest event differs by exactly the estate tax collected, to floating-point tolerance. |
| T08-3 | `test_population_stationary` | Population size is constant across all periods in the default configuration. |
| T08-4 | `test_age_distribution_plausible` | Mean age and maximum age fall within bands implied by the supplied hazard schedule, and no agent exceeds the schedule's terminal age. |
| T08-5 | `test_inheritance_identity_holds` | Measured `b_y` agrees with `mu * m * beta` computed from the same run, within 5% relative. The stage's central test. `slow`. |
| T08-6 | `test_mu_exceeds_one` | Average decedent wealth exceeds average living wealth — the wealth-age profile is realistic rather than flat. |
| T08-7 | `test_equal_split_dilutes_concentration` | `equal_split` with several heirs yields a lower stationary top-1% share than `single` at the same seed. The institutional variable has the expected direction. |
| T08-8 | `test_estate_tax_reduces_inherited_share` | Raising the estate-tax rate monotonically reduces the inherited share of total wealth across at least four points. |
| T08-9 | `test_no_heir_selection_double_count` | Across a long run, the number of bequest events equals the number of deaths, and no agent receives an estate in the period it dies. |

NB05 inherits the parametrised notebook battery, plus `test_nb05_core_logic_runs`.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_engine_demography.py -v
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty && make test
```

Pass criteria:

1. All commands exit zero. T08-1 and T08-5 pass specifically — the first proves we
   have not disturbed the foundation, the second that the new mechanism is
   internally coherent.
2. The identity is demonstrated by hand and the numbers recorded in §9:
   ```bash
   uv run python -c "
   # measure b_y directly and via mu * m * beta on the same OLG run; print both
   # and the relative gap. Gap must be under 5%.
   "
   ```
3. The simulated inheritance flow is U-shaped over the historical scenario:
   mid-century trough materially below both the pre-1914 and the modern level.
   Direction and rough magnitude, not a fitted curve.
4. S05's pinned tail-index observations still reproduce unchanged, confirming the
   default path is untouched.
5. NB05 opened interactively; the Rastignac calculator produces sensible answers
   across cohorts.

## 7. Risks

- **Silent double counting.** Transferring a decedent's wealth *and* resetting the
  agent inflates total wealth; selecting heirs with replacement concentrates
  spuriously. T08-2 and T08-9 are the specific guards, and both failure modes are
  easy to write and hard to see in a chart.
- **Ordering within the period.** If mortality is evaluated before returns, the
  estate recorded is one period stale and `mu` is biased. T08-5 catches this, which
  is why the identity test is worth its runtime.
- **Flat hazard producing an implausible age profile.** Covered by T08-4 and T08-6;
  a flat rate is convenient but yields `mu` too close to 1 and understates the flow.
- **Scope creep into full life-cycle consumption.** A properly micro-founded
  buffer-stock consumption block is out of scope; the savings rate stays fixed. If
  that becomes limiting, HARK is the reference implementation to consult, but not in
  this stage.

## 8. Out of scope

Progressive estate schedules with multiple bands (S09 implements bracket
arithmetic; a flat rate suffices here), education and human-capital transmission
(S12), and universal endowments (S13).

## 9. Pinned observations

*To be completed at implementation.*

| Quantity | Expected | Observed | Note |
|---|---|---|---|
| `b_y` measured directly | — | — | OLG run, seed 42 |
| `mu * m * beta` | — | — | same run |
| Relative gap | < 5% | — | T08-5 |
| `mu` | > 1 | — | T08-6 |
| Inherited share of total wealth | — | — | baseline |
