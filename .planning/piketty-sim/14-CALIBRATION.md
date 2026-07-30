# Stage 14 — Calibration and validation harness

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S04, S05 |
| **Blocks** | S15 |
| **Requirements** | CAL-01 … CAL-05 |
| **Commit** | `feat(piketty-sim): add calibration targets, moments and sweep` |

> Specified to design depth. May run in parallel with S07–S13 once S05 is done.

## 1. Purpose

Turn "the simulation looks roughly right" into a number. This stage builds the
machinery to score a configuration against empirical moments from WID, to search a
parameter space for the best-scoring configuration, and — critically — to establish
that a result is a property of the model rather than of the random seed.

The seed-stability discipline is the part that matters most and is most often
skipped. An agent-based model with 5 000 agents produces a top-1% share that varies
across seeds; if that variation is comparable to the effect being reported, the
result is noise. The established principle is to start small, require a minimum
number of agents per stratum, and demonstrate run-to-run stability *before* scaling
up — and this stage makes that a tool rather than an intention.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/calibration/__init__.py` | create | public surface |
| `src/piketty_sim/calibration/targets.py` | create | WID-derived `TargetStat` sets |
| `src/piketty_sim/calibration/moments.py` | create | panel to statistics mapping |
| `src/piketty_sim/calibration/sweep.py` | create | grid search, ranking, seed stability |
| `tests/test_calibration.py` | create | targets, moments, sweep, stability |

## 3. Design

### 3.1 Targets from data, not from memory

```python
def wid_wealth_targets(
    *, country: str = "GB", year: int = 2020, offline: bool = True,
    tolerances: Mapping[str, float] | None = None,
) -> list[TargetStat]
```

Target *values* are read from the S04 data layer at call time; only the tolerances
and weights are supplied by the caller. This is deliberate and structural: a
`TargetStat` with a hard-coded `target_value` typed from memory is exactly the
failure mode that makes calibration meaningless, and building the targets from the
pinned snapshot makes it impossible.

Default target set: top-1%, top-10% and bottom-50% wealth shares, the Gini, and the
wealth-to-income ratio `beta` — the five quantities Piketty's presentation turns on.

### 3.2 Moments

```python
def panel_moments(
    panel: WealthPanel, *, warm_up: int = 0, detrend: bool = True
) -> dict[str, float]
```

Maps a panel to the statistics dictionary that `evaluate_stats` (S02) scores,
composing S03's metrics. `warm_up` discards initial transient periods, because a
distribution that has not reached stationarity will score against targets it was
never going to match. `detrend` defaults to true for the reasons S05 §3.3 sets out.

The names it emits must match the target names exactly, and the missing-statistic
behaviour from S02 (visible `nan`, never a silent pass) is what makes a mismatch
obvious instead of flattering.

### 3.3 Sweep and ranking

```python
@dataclass(frozen=True)
class SweepResult:
    config: WealthEngineConfig
    report: EvaluationReport
    moments: dict[str, float]
    seed: int

@dataclass(frozen=True)
class SweepSummary:
    results: tuple[SweepResult, ...]
    @property
    def best(self) -> SweepResult: ...
    def ranked(self) -> tuple[SweepResult, ...]: ...
    def summary_table(self) -> pl.DataFrame: ...

def parameter_sweep(
    param_grid: Mapping[str, Sequence[float]], *,
    base: WealthEngineConfig, targets: Sequence[TargetStat],
    periods: int, warm_up: int, seeds: Sequence[int] = (42,),
) -> SweepSummary
```

The repo has a close analogue in
`packages/companies-house-abm/src/companies_house_abm/calibration/sweep.py`, whose
`SweepResult`/`SweepSummary` shape (with `best`, `ranked`, `summary_table`) is worth
copying for familiarity. It cannot be imported: it is coupled to
`evaluate_simulation` and to the ABM's result type, and importing it would breach
the coupling rule. Copy-adapt the structure, cite it in the docstring, and note that
this version sweeps over seeds as well as parameters — which the original does not.

Parameter paths are dotted strings resolved against the nested config
(`"returns.r_mean"`, `"savings.wealth_retention"`), applied with `dataclasses.replace`
along the path. Grid size grows multiplicatively, so the docstring states the run
count arithmetic and the function logs it before starting.

### 3.4 Seed stability

```python
@dataclass(frozen=True)
class StabilityReport:
    metric: str
    n_agents: int
    seeds: tuple[int, ...]
    values: tuple[float, ...]
    mean: float
    std: float
    cv: float                    # coefficient of variation
    @property
    def is_stable(self) -> bool  # cv below threshold

def seed_stability(
    config: WealthEngineConfig, *, seeds: Sequence[int],
    metrics: Mapping[str, Callable[[np.ndarray], float]],
    cv_threshold: float = 0.05,
) -> dict[str, StabilityReport]
```

This is CAL-04 and the stage's most valuable output. The documented workflow, which
S15 must follow and evidence:

1. Start at about 5 000 agents.
2. Run `seed_stability` across at least ten seeds.
3. If the coefficient of variation of a reported metric exceeds the threshold, the
   population is too small for that metric — increase agents, not seeds, and repeat.
4. Only once stable, scale up and calibrate.
5. Never report an effect smaller than the seed variation of the metric it is
   measured in.

That last rule is the one that keeps the whole series honest, and it is worth
stating in the notebook of any stage that reports a comparison.

## 4. Requirements

- [ ] **CAL-01** WID-derived target sets with documented provenance and tolerances.
- [ ] **CAL-02** `panel_moments` maps a panel to the scored statistics.
- [ ] **CAL-03** Grid sweep evaluates and ranks, reporting the best.
- [ ] **CAL-04** Seed-stability harness reports run-to-run variation; workflow documented.
- [ ] **CAL-05** Runs reproducible from a committed config plus a seed.

## 5. Tests

`tests/test_calibration.py`

| ID | Test | Assertion |
|---|---|---|
| T14-1 | `test_targets_read_from_data` | Target values come from the data layer: patching the loader changes them. Structurally prevents hard-coded targets. |
| T14-2 | `test_target_names_match_moment_names` | Every default target name is produced by `panel_moments` — the mismatch that silently produces `nan` scores cannot occur unnoticed. |
| T14-3 | `test_moments_are_finite` | On a reference run, every moment is finite and in a plausible range (shares in `[0, 1]`, `beta` positive). |
| T14-4 | `test_warm_up_discards_transient` | A non-zero `warm_up` changes the moments on a run that has not reached stationarity, and does not on one that has. |
| T14-5 | `test_sweep_covers_grid` | A 2×3 grid produces exactly six results per seed, with the expected configs. |
| T14-6 | `test_sweep_ranking_orders_by_score` | `ranked()` is sorted ascending by `overall_score` and `best` is its first element. |
| T14-7 | `test_dotted_path_resolution` | `"returns.r_mean"` sets the nested field and leaves siblings untouched; an invalid path raises. |
| T14-8 | `test_sweep_reproducible` | The same grid, base and seeds produce identical results across invocations. CAL-05. |
| T14-9 | `test_seed_stability_detects_noise` | At a deliberately small population, at least one metric's CV exceeds the threshold and `is_stable` is False; at a large population it is True. The harness detects the problem it exists to detect. `slow`. |
| T14-10 | `test_stability_threshold_configurable` | A stricter threshold flips a borderline case, and the threshold is reported in the result. |
| T14-11 | `test_perfect_config_scores_well` | A config generated to match synthetic targets exactly scores near zero — end-to-end validation of targets, moments and scoring together. |

T14-9 and T14-11 are the two that establish the harness works: one proves it catches
noise, the other proves it recognises a good fit.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_calibration.py -v
make test-piketty && make test
```

Pass criteria:

1. All commands exit zero; T14-1, T14-2, T14-9 and T14-11 pass specifically.
2. A real calibration run is performed against WID targets for one country, and the
   result recorded in §8: the best-scoring configuration, its weighted score, and
   its per-target deviations. A poor score is an acceptable outcome and must be
   reported as such rather than tuned away by widening tolerances.
3. Seed stability is established and recorded for the reference configuration at
   5 000 agents across ten seeds, for each of the five default metrics. Any metric
   failing the threshold is reported with the population size at which it becomes
   stable.
4. The calibrated configuration is saved via `save_config` and committed, so the
   result is reproducible from the file plus the seed.
5. Sweep runtime is documented; if the reference grid takes more than a few minutes,
   note it and reduce the grid rather than leaving a slow default.

## 7. Risks

- **Targets typed from memory.** The central risk, structurally prevented by T14-1.
- **Overfitting to five moments.** Matching five statistics does not validate a
  model; many configurations will fit. Report the *set* of well-scoring
  configurations, not just the best, and state which parameters are poorly
  identified — the sweep's ranked output makes this visible if it is looked at.
- **Combinatorial explosion.** A five-parameter grid at five points each with ten
  seeds is over 30 000 runs. Keep grids coarse, sweep seeds separately from
  parameters where possible, and treat this as the motivating case for S15's Rust
  kernel rather than a problem to solve with patience.
- **Stability threshold theatre.** A threshold loose enough to pass everything is
  worse than none. The default of 0.05 is meaningful; if a metric cannot meet it,
  the honest response is a larger population or a retracted claim.

## 8. Pinned results

*To be completed at implementation.*

| Quantity | Value | Note |
|---|---|---|
| Country and year calibrated | — | — |
| Best weighted score | — | lower is better |
| Top-1% share, target / simulated | — | — |
| Top-10% share, target / simulated | — | — |
| Bottom-50% share, target / simulated | — | — |
| Gini, target / simulated | — | — |
| `beta`, target / simulated | — | — |
| Metrics stable at 5 000 agents | — | of five |
| Population needed for full stability | — | — |
| Committed config path | — | — |
