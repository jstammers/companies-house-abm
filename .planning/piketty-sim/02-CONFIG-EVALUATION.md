# Stage 02 — Configuration and evaluation framework

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S01 |
| **Blocks** | S05 |
| **Requirements** | CFG-01 … CFG-06 |
| **Commit** | `feat(piketty-sim): add engine config and evaluation framework` |

## 1. Purpose

Establish the two spines that every later stage attaches to: an immutable,
hierarchical parameter object describing an economy, and a model-agnostic way to
score a set of computed statistics against empirical targets.

Getting the config shape right now is what makes stages 08 through 13 additive
rather than invasive. Each of those stages introduces a mechanism — bequests,
progressive taxes, endowments, transmission — and each must be reachable by
changing a parameter, not by editing the engine loop. The config therefore
declares **neutral slots for mechanisms not yet built**, with defaults chosen so
that the mechanism is off and the engine's behaviour is exactly as if the slot did
not exist.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/config.py` | create | frozen dataclasses plus YAML round-trip helpers |
| `src/piketty_sim/evaluation.py` | create | copy-adapted target/report classes, plus `evaluate_stats` |
| `src/piketty_sim/__init__.py` | modify | re-export the public config and evaluation names |
| `tests/test_config.py` | create | immutability, round-trip, neutral defaults |
| `tests/test_evaluation.py` | create | scoring arithmetic and edge cases |

## 3. Design

### 3.1 Configuration hierarchy

Frozen dataclasses, one per concern, aggregated by `WealthEngineConfig`, with
`field(default_factory=...)` for every nested default. This mirrors the idiom
already proven in `packages/companies-house-abm/src/companies_house_abm/abm/config.py`
(17 frozen dataclasses aggregated by `ModelConfig`), which is worth copying for
consistency of feel across the repo even though none of its content applies.

```python
@dataclass(frozen=True)
class ReturnsConfig:
    """Parameters of the stochastic return process on wealth."""
    r_mean: float = 0.05          # mean net real return, r
    r_std: float = 0.10           # idiosyncratic return volatility
    scale_elasticity: float = 0.0 # extra mean return per log-unit of relative wealth
    r_floor: float = -0.9         # truncation keeping the gross factor positive

@dataclass(frozen=True)
class IncomeConfig:
    """Parameters of the labour-income process."""
    mean: float = 1.0             # numeraire: mean labour income at t=0
    sigma: float = 0.6            # lognormal dispersion of permanent income
    growth: float = 0.02          # g, productivity growth of labour income

@dataclass(frozen=True)
class SavingsConfig:
    """Savings behaviour and the drawdown of accumulated wealth."""
    rate: float = 0.10            # s, saved share of labour income
    wealth_retention: float = 0.98  # gross wealth carried forward each period
    consumption_floor: float = 0.0

@dataclass(frozen=True)
class TaxConfig:
    """Fiscal instruments. All neutral by default; S09 activates them."""
    wealth_tax_brackets: tuple[tuple[float, float], ...] = ()
    capital_income_tax_rate: float = 0.0
    labour_income_tax_brackets: tuple[tuple[float, float], ...] = ()
    estate_tax_brackets: tuple[tuple[float, float], ...] = ()
    transfer_per_capita: float = 0.0
    avoidance_elasticity: float = 0.0

@dataclass(frozen=True)
class DemographyConfig:
    """Population turnover. `mode="reset"` until S08 adds true OLG."""
    mode: str = "reset"           # "reset" | "olg"
    death_rate: float = 0.02      # per-period probability of exit
    bequest_division: str = "single"   # S08: "single" | "equal_split"
    max_age: int | None = None    # S08: deterministic retirement/mortality bound

@dataclass(frozen=True)
class EndowmentConfig:
    """Universal capital endowment. Off by default; S13 activates."""
    amount_fraction_of_mean: float = 0.0
    age_at_receipt: int = 25

@dataclass(frozen=True)
class TransmissionConfig:
    """Intergenerational human-capital transmission. Off by default; S12."""
    parental_elasticity: float = 0.0
    public_spending: float = 0.0
    public_progressivity: float = 0.0
    credit_constraint: float | None = None

@dataclass(frozen=True)
class WealthEngineConfig:
    """Complete description of a simulated economy."""
    n_agents: int = 10_000
    periods: int = 500
    seed: int = 42
    initial_wealth_sigma: float = 1.0
    returns: ReturnsConfig = field(default_factory=ReturnsConfig)
    income: IncomeConfig = field(default_factory=IncomeConfig)
    savings: SavingsConfig = field(default_factory=SavingsConfig)
    taxes: TaxConfig = field(default_factory=TaxConfig)
    demography: DemographyConfig = field(default_factory=DemographyConfig)
    endowment: EndowmentConfig = field(default_factory=EndowmentConfig)
    transmission: TransmissionConfig = field(default_factory=TransmissionConfig)
```

**Why the empty-tuple bracket representation.** A progressive schedule is a
sequence of `(threshold, marginal_rate)` pairs. An empty tuple is unambiguously
"no tax", needs no sentinel, is hashable inside a frozen dataclass, and extends
to arbitrarily many bands — which NB06 needs, since its whole point is
user-editable band structure.

**Why `wealth_retention` defaults to 0.98 rather than 1.0.** It is the fraction of
gross wealth carried into the next period, and it is what makes the wealth process
stationary. With retention at exactly 1 and a return above the growth rate, wealth
grows without bound relative to income and there is no stationary distribution to
measure — that is Piketty's divergence force in its pure form. The value 0.98,
combined with the other defaults, yields a tail index of about 1.7, which is in
the empirically observed range. S05 derives this in closed form and depends on the
number, so changing it requires re-deriving that stage's acceptance bands.

**Why `scale_elasticity` defaults to zero.** Return heterogeneity rising in
wealth is one of Piketty's amplifying mechanisms, and NB03 must be able to switch
it on to show the tail thicken. Zero default means the baseline is the clean
textbook Kesten process, and the amplification is visibly attributable.

### 3.2 Serialisation helpers

Copy-adapt `config_to_dict` and `save_config` from the ABM package (verified at
`abm/config.py:349` and `:370`): a recursive `_convert` that turns nested
dataclasses into dicts and tuples into lists so the result is YAML-safe, then
`yaml.dump` with `default_flow_style=False`.

```python
def config_to_dict(config: WealthEngineConfig) -> dict[str, Any]
def save_config(config: WealthEngineConfig, path: Path) -> None
def load_config(path: Path) -> WealthEngineConfig
```

`load_config` must handle the bracket fields specially: YAML round-trips tuples as
lists, so loading has to coerce nested lists back to tuples of tuples or the
frozen dataclass silently holds unhashable, mutable values. This is the one place
where the round-trip is not symmetric by default, and it is the reason T02-3
exists.

### 3.3 Evaluation framework

Copy `TargetStat`, `StatResult` and `EvaluationReport` from
`packages/companies-house-abm/src/companies_house_abm/reporting/evaluation.py`
lines 41–162 — these are genuinely model-agnostic: `TargetStat` is a declarative
`(name, description, target_value, tolerance, weight)` record, and
`EvaluationReport` computes a weighted root-mean-square **relative** deviation,
counts targets within tolerance, and renders `summary()` and `as_dict()`.

Everything from line 170 onward in that file is discarded: it hardcodes GDP
growth, inflation, unemployment and debt-to-GDP off the ABM's `PeriodRecord`, and
importing it would reintroduce the coupling this package exists to avoid.

Replace the discarded glue with one generic function:

```python
def evaluate_stats(
    stats: Mapping[str, float],
    targets: Sequence[TargetStat],
) -> EvaluationReport:
    """Score computed statistics against declarative targets."""
```

Semantics, matching the original: relative deviation
`(simulated - target) / abs(target)`; `passed` when
`abs(simulated - target) <= tolerance`; a target whose name is absent from
`stats` produces a `StatResult` with `nan` deviation that is counted in
`n_total`, excluded from the weighted sum, and rendered as `N/A` — a missing
statistic must be visible, never silently scored as a pass.

The module docstring records that these classes are adapted from the ABM
package's evaluation module, so a future reader knows the duplication is
deliberate and where the sibling lives.

## 4. Requirements

- [ ] **CFG-01** Frozen nested dataclasses aggregated by `WealthEngineConfig`, nested defaults via `default_factory`.
- [ ] **CFG-02** `config_to_dict` / `save_config` / `load_config` round-trip losslessly, including bracket tuples.
- [ ] **CFG-03** Mutation raises; variants come from `dataclasses.replace`.
- [ ] **CFG-04** Every not-yet-built mechanism is neutral at its default.
- [ ] **CFG-05** `TargetStat` / `StatResult` / `EvaluationReport` present, decoupled, provenance documented.
- [ ] **CFG-06** `evaluate_stats` scores a plain mapping.

## 5. Tests

`tests/test_config.py`

| ID | Test | Assertion |
|---|---|---|
| T02-1 | `test_config_is_frozen` | Assigning to any field of any config dataclass raises `FrozenInstanceError`. |
| T02-2 | `test_replace_produces_variant` | `dataclasses.replace` yields a changed copy leaving the original intact. |
| T02-3 | `test_yaml_round_trip` | `save_config` then `load_config` reproduces an equal config, including a multi-band `wealth_tax_brackets` restored as a tuple of tuples, not lists. |
| T02-4 | `test_defaults_are_neutral` | On a default config: all tax rates and bracket sets are zero or empty, `scale_elasticity == 0.0`, endowment amount is zero, transmission elasticity is zero, demography mode is `"reset"`. Directly encodes CFG-04, which is what protects every later stage's seeded results. |
| T02-5 | `test_nested_defaults_not_shared` | Two independently constructed configs have distinct nested instances (guards against a mutable class-level default). |

`tests/test_evaluation.py`

| ID | Test | Assertion |
|---|---|---|
| T02-6 | `test_perfect_match_scores_zero` | Stats equal to targets give `overall_score == 0.0` and all passed. |
| T02-7 | `test_relative_deviation_arithmetic` | A known 10% overshoot on a single target gives `deviation == pytest.approx(0.1)`. |
| T02-8 | `test_weighted_score` | Two targets with unequal weights produce the weighted RMS, verified against a hand-computed value. |
| T02-9 | `test_tolerance_boundary` | A deviation exactly equal to tolerance counts as passed; one epsilon beyond does not. |
| T02-10 | `test_missing_stat_is_visible` | A target absent from `stats` yields `nan` deviation, is counted in `n_total`, is not passed, and renders as `N/A` in `summary()`. |
| T02-11 | `test_empty_report_score_is_inf` | An empty report scores `inf` rather than dividing by zero. |

## 6. Verification gate

```bash
make fix && make verify
make test-piketty
uv run pytest packages/piketty-sim/tests/test_config.py packages/piketty-sim/tests/test_evaluation.py -v
make test
```

Pass criteria:

1. All of the above exit zero; T02-4 and T02-10 pass specifically.
2. Round-trip check by hand:
   ```bash
   uv run python -c "
   from pathlib import Path
   from dataclasses import replace
   from piketty_sim.config import WealthEngineConfig, TaxConfig, save_config, load_config
   c = WealthEngineConfig(taxes=TaxConfig(wealth_tax_brackets=((1e6, 0.01), (5e6, 0.02))))
   p = Path('/tmp/c.yml'); save_config(c, p)
   assert load_config(p) == c, 'round trip lost information'
   print('round trip ok')"
   ```
3. `rg -l 'companies_house' packages/piketty-sim/` returns nothing — the copy is a
   copy, not an import.
4. Coverage of `config.py` and `evaluation.py` is at or above 95%; these are small
   pure modules with no excuse for gaps.

## 7. Risks

- **Silent tuple/list drift.** The most likely real bug in this stage is a config
  loaded from YAML holding lists where the code expects tuples, which stays
  invisible until a bracket set is used for hashing or comparison in S09. T02-3
  is the guard.
- **Copy divergence.** The ABM's evaluation classes may change later. That is
  acceptable — the copy is intentional and documented — but the docstring must
  say so, or a future reader will "fix" the duplication by importing.
- **Over-declaring slots.** Config fields for mechanisms five stages away risk
  becoming wrong guesses. Mitigation: each slot is only a scalar or a bracket
  tuple with a neutral default, carries no behaviour, and is cheap to reshape when
  its owning stage arrives. Any reshaping is a normal change to this file, not a
  breach of the plan.

## 8. Out of scope

No simulation, no metrics, no data. `TaxConfig` and friends are declared here but
consumed by their owning stages; declaring them does not commit this stage to
implementing anything they describe.
