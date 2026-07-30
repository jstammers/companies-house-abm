# Stage 10 — Inequality regimes and reparations (NB07)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S09 |
| **Blocks** | S15 |
| **Requirements** | REG-01 … REG-04 |
| **Commit** | `feat(piketty-sim): add regime presets and reparations calculators` |

> Specified to design depth. Parameter values pinned at implementation start, each
> with a citation.

## 1. Purpose

Express the central claim of *Capital and Ideology* — that every inequality regime
is a political-ideological equilibrium rather than a natural outcome — as a set of
named parameterisations of the one engine built in S05 and extended through S09.

If the engine is right, then the trifunctional society of clergy, nobility and
third estate, the proprietarian order of 1900, the slave and colonial economies,
the post-war social-democratic settlement and post-1980 hypercapitalism are not
five different models. They are five parameter vectors: who may own what, how
concentrated ownership starts, how steeply it is taxed, how inheritance divides.
Demonstrating that is the whole point of the stage, and it is also the strongest
available test of whether the engine generalises or was quietly fitted to one
century of one continent.

The stage also carries the compound-interest arithmetic of compensated abolition
and the Haitian indemnity, which is the most arresting five lines of code in the
series.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/regimes.py` | create | named preset constructors and comparison |
| `src/piketty_sim/reparations.py` | create | compound-interest calculators |
| `src/piketty_sim/config.py` | modify | any regime field S02 did not anticipate |
| `notebooks/nb07_regimes.py` | create | preset comparison and free editing |
| `tests/test_regimes.py` | create | presets, ordering, comparison |
| `tests/test_reparations.py` | create | arithmetic, sensitivity |

## 3. Design

### 3.1 Presets as constructors

```python
def ternary_society() -> WealthEngineConfig
def proprietarian_1900() -> WealthEngineConfig
def slave_economy() -> WealthEngineConfig
def colonial_economy() -> WealthEngineConfig
def social_democratic() -> WealthEngineConfig
def hypercapitalist() -> WealthEngineConfig

REGIMES: Mapping[str, Callable[[], WealthEngineConfig]]

def compare_regimes(
    names: Sequence[str], *, periods: int, seed: int
) -> pl.DataFrame:
    """Run each named regime to stationarity and tabulate identical metrics."""
```

Every preset is a plain function returning a config, so a notebook can call it and
then `dataclasses.replace` any field — which is exactly the "design your own
regime" workflow REG-04 asks for. No preset may contain behaviour; if a regime
seems to need code, that is a signal the engine is missing a parameter, and the
right response is to add the parameter, not to special-case the regime.

**Every parameter value in every preset carries a citation** in a comment or a
`note` field: the appendix table, the WID series, or the passage it comes from.
This is the difference between a model of history and a set of numbers that produce
a pleasing chart. A preset with uncited parameters fails the gate.

Regimes differ along: initial wealth concentration; the tax schedules of S09;
`bequest_division` from S08 (partible versus impartible inheritance is a defining
institutional variable); return scale-dependence; and, for the slave and colonial
cases, the accounting treatment described next.

### 3.2 Slave and colonial regimes

These require honesty about what the model does and does not represent. In the
societies Piketty documents, enslaved human beings were recorded as capital, and
in some cases constituted a large share of total recorded private wealth. The
simulation can represent that accounting fact — a category of wealth held by one
group whose counterpart is another group's total exclusion from ownership — and it
must not present that representation as morally neutral bookkeeping.

Design decision: the slave and colonial regimes are implemented primarily as **data
exploration and accounting decomposition**, following the source plan, rather than
as a full behavioural simulation. We show the composition of recorded wealth and the
magnitude of the excluded population's zero share, using appendix data. The notebook
states explicitly that treating human beings as an asset class is the historical
record being described, not a modelling convenience, and that the exercise measures
the scale of expropriation rather than simulating an economy in any ordinary sense.

### 3.3 Reparations arithmetic

```python
@dataclass(frozen=True)
class CompoundResult:
    principal: float
    rate: float
    years: int
    value: float
    real_value: float | None   # deflated where a deflator is supplied

def compound(principal, rate, years, *, deflator=None) -> CompoundResult
def haitian_indemnity(*, rate: float, to_year: int) -> CompoundResult
def compensated_abolition(*, country: str, rate: float, to_year: int) -> CompoundResult
```

The pedagogical content is the sensitivity: the present value of a nineteenth-century
sum depends enormously on the assumed rate, and the honest presentation is a range
across plausible rates rather than one headline figure. The notebook therefore
renders a rate-versus-present-value curve, not a single number.

Historical inputs — the indemnity France extracted from Haiti as the price of
recognising its independence, and the sums European states paid *to slaveholders* as
compensation at abolition — must be taken from the book appendices with the figure,
currency, year and any subsequent renegotiation recorded in the snapshot metadata.
**Do not hard-code a remembered figure into a test.** Tests assert the arithmetic
and the sensitivity structure; the historical magnitudes come from the pinned data
and are verified against the cited source during implementation.

## 4. Requirements

- [ ] **REG-01** Six named presets, every parameter cited.
- [ ] **REG-02** Each runs to stationarity; side-by-side comparison on identical metrics.
- [ ] **REG-03** Compound-interest calculators with cited inputs, auditable.
- [ ] **REG-04** NB07 supports preset selection plus free parameter editing.

## 5. Tests

`tests/test_regimes.py`

| ID | Test | Assertion |
|---|---|---|
| T10-1 | `test_all_presets_construct` | Every entry in `REGIMES` returns a valid `WealthEngineConfig`. |
| T10-2 | `test_all_presets_run` | Each runs at a small config without error and yields finite metrics. `slow`. |
| T10-3 | `test_concentration_ordering` | Stationary top-1% shares order as the books describe: proprietarian and hypercapitalist regimes above the social-democratic regime. The substantive claim of the stage, tested rather than asserted. `slow`. |
| T10-4 | `test_social_democratic_has_largest_middle` | The social-democratic preset yields the highest middle-40% wealth share — the patrimonial middle class is a regime property. `slow`. |
| T10-5 | `test_presets_are_data_not_behaviour` | Every preset returns a config equal to one constructible by `replace` from defaults, proving no preset smuggles in behaviour. |
| T10-6 | `test_all_parameters_cited` | Every preset has a citation note for each non-default field; a preset with uncited parameters fails. |
| T10-7 | `test_compare_regimes_shape` | `compare_regimes` returns one row per regime with identical metric columns. |
| T10-8 | `test_free_editing_composes` | `replace` on a preset changes only the targeted field. |

`tests/test_reparations.py`

| ID | Test | Assertion |
|---|---|---|
| T10-9 | `test_compound_arithmetic` | `compound(100, 0.05, 10).value == pytest.approx(162.889, rel=1e-4)`. |
| T10-10 | `test_zero_rate_is_identity` | Zero rate returns the principal unchanged. |
| T10-11 | `test_monotone_in_rate_and_years` | Value strictly increases in both. |
| T10-12 | `test_deflator_produces_real_value` | A supplied deflator yields `real_value` below nominal under positive inflation. |
| T10-13 | `test_historical_inputs_come_from_snapshot` | `haitian_indemnity` and `compensated_abolition` read principal and year from the pinned data layer, not from module literals — asserted by patching the loader and observing the result change. |
| T10-14 | `test_rate_sensitivity_spans_orders` | Across the plausible rate range, present value spans at least an order of magnitude, which is the point the notebook makes. |

T10-13 matters: it structurally prevents a remembered number from being baked into
the code, which is the specific failure mode this stage is most exposed to.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_regimes.py packages/piketty-sim/tests/test_reparations.py -v
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty && make test
```

Pass criteria:

1. All commands exit zero; T10-3, T10-4, T10-6 and T10-13 pass specifically.
2. Every preset's citations reviewed by reading them, and the sources checked. A
   parameter whose source cannot be located is removed or replaced with a defaulted
   value and a stated gap — not left in with a vague note.
3. `compare_regimes` output recorded in §9 as the stage's headline result.
4. NB07's slave and colonial sections read as historically serious. This is a
   judgement, and it is part of the gate: a reviewer reads the narrative and confirms
   it describes expropriation rather than tabulating an asset class neutrally.
5. NB07 opened interactively; preset selection and free editing both work.

## 7. Risks

- **Presets as unfalsifiable storytelling.** Six parameter vectors chosen to produce
  the expected ordering would prove nothing. Mitigations: citation requirement
  (T10-6), the structural constraint that presets are data not behaviour (T10-5),
  and stating in the notebook which parameters are sourced versus assumed.
- **Remembered historical figures.** Addressed by T10-13 and the snapshot
  requirement.
- **Handling of slavery.** The risk is a notebook that is technically correct and
  morally tone-deaf. Gate item 4 makes the narrative a reviewed deliverable rather
  than incidental prose.
- **Engine limits surfacing as regime hacks.** If a regime cannot be expressed
  parametrically, that is information: either add the parameter or state in the
  notebook that this regime is outside what the engine represents. Do not
  special-case.

## 8. Out of scope

Endogenous regime transition — regimes emerging from political feedback rather than
being selected — is the capstone's job (S15). Here regimes are exogenous presets,
and the notebook says so.

## 9. Pinned results

*To be completed at implementation.*

| Regime | Top 1% share | Middle 40% share | Gini | Tail index |
|---|---|---|---|---|
| Ternary | — | — | — | — |
| Proprietarian 1900 | — | — | — | — |
| Social-democratic | — | — | — | — |
| Hypercapitalist | — | — | — | — |
