# Stage 15 — Capstone and Rust kernel (NB12)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | all stages |
| **Blocks** | — |
| **Requirements** | CAP-01 … CAP-05 |
| **Commit** | `feat(piketty-sim): add capstone ABM notebook and Rust kernel` |

> Specified to design depth. Everything numerical is pinned at implementation start.

## 1. Purpose

Compose everything into one model, and add the compiled kernel that makes it
tractable.

The composition is what makes this an agent-based model rather than a
microsimulation. Every earlier stage takes policy as given: NB06 imposes a tax
schedule, NB07 selects a regime, NB10 sets a redistribution intensity. Here the
distribution produces voters, voters produce policy through S11's mechanism, policy
feeds back into accumulation, and the resulting distribution produces the next
period's voters. Regimes stop being presets and become **emergent and
path-dependent**: the model can settle into a high-inequality political equilibrium
or a redistributive one depending on where it started and what shocks it met.

That feedback loop is the intellectual payoff of the whole series. It is also what
makes the computational cost real, which is why the Rust kernel belongs here and
nowhere earlier.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `notebooks/nb12_full_piketty_economy.py` | create | the capstone |
| `src/piketty_sim/engine/policy_feedback.py` | create | voting to policy to accumulation |
| `src/piketty_sim/_rust.py` | create | optional accelerator shim |
| `packages/rust-piketty/Cargo.toml` | create | separate maturin crate |
| `packages/rust-piketty/pyproject.toml` | create | maturin backend |
| `packages/rust-piketty/src/lib.rs` | create | pyo3 module surface |
| `packages/rust-piketty/src/kernel.rs` | create | the wealth-process inner loop |
| `scripts/build_rust_piketty.sh` | create | build and install the extension |
| `Makefile` | modify | `build-rust-piketty` target |
| `pyproject.toml` | modify | workspace `exclude` for the new crate |
| `tests/test_policy_feedback.py` | create | loop behaviour, hysteresis |
| `tests/test_rust_parity.py` | create | Python/Rust agreement, `importorskip` |

## 3. Design

### 3.1 The policy feedback loop

```python
@dataclass(frozen=True)
class PolicyFeedbackConfig:
    election_interval: int = 20
    parties: tuple[Party, ...] = ()
    policy_inertia: float = 0.5      # weight on the previous schedule
    party_adaptation: float = 0.0    # parties reposition toward the winning coalition

def policy_feedback_hook(cfg: PolicyFeedbackConfig, ...) -> PeriodHook
```

Implemented as a `PeriodHook` — the same seam S05 provided and S07 first used. Every
`election_interval` periods: build voters from the current distribution (S11), compute
vote shares, translate the winning coalition's position on the redistribution axis
into a tax schedule (S09), and blend it with the existing schedule under
`policy_inertia`. Institutions are sticky; a model where the schedule jumps
discontinuously every election is less realistic, not more.

`policy_inertia` and `party_adaptation` are the two parameters that determine whether
the system exhibits hysteresis, so they are the ones the experiments vary.

That this composes purely through the existing hook mechanism, with no engine
modification, is the design being validated. If the capstone requires changing
`kesten.py`, the seams were wrong and that is worth recording as a finding.

### 3.2 The three experiments

CAP-02 requires answers, not just a runnable model:

**(a) Can shocks alone produce the twentieth-century equalisation, or is policy
required?** Run the S07 historical scenario with the policy loop disabled — shocks
only — and with it enabled. Compare both against the observed U-curve. This is the
Piketty-versus-Acemoglu-Robinson question posed as an experiment, and either answer
is publishable within the notebook: if shocks alone suffice, that supports the
"general laws" reading; if policy is required, it supports the institutional one.

**(b) Hysteresis.** Drive the system from hypercapitalism toward social democracy by
a sequence of shocks, then reverse the sequence exactly, and measure whether it
retraces its path. Path dependence means the reverse trajectory differs; if it
retraces, the model has no genuine hysteresis and the "regimes are political
equilibria" framing is not supported by this implementation. Report either way.

**(c) Sensitivity to `r − g`.** A structured sweep of the gap, with every headline
outcome reported as a function of it, using S14's sweep and stability machinery.

### 3.3 Validation discipline

CAP-03 makes S14's workflow a gate condition rather than advice:

1. Start at about 5 000 agents.
2. Ensure at least 30 to 50 agents per stratum, where strata are the cross of
   income quintile and any regional or educational grouping used. State the stratum
   count and the implied minimum population explicitly.
3. Run `seed_stability` across at least ten seeds for every metric the experiments
   report.
4. Only then scale to the large runs.
5. No reported effect may be smaller than the seed variation of its metric.

The stratum arithmetic must be written down in the notebook: with five income
quintiles crossed with, say, four education groups, 20 strata at 50 agents each is a
floor of 1 000 agents before any tail estimate is meaningful, and tail statistics
need far more than that because they depend on the count in the top percentile, not
the total.

### 3.4 The Rust kernel

**Only after the Python engine's API is frozen.** The kernel is a drop-in
replacement behind the same signature, not a reimplementation with its own
interface.

Structure follows the existing `packages/rust-abm` precedent exactly, since it is a
working template: `crate-type = ["cdylib"]`, pyo3 with the `extension-module`
feature, maturin backend with `python-source`, excluded from the uv workspace so
`uv sync` never tries to build it, and a build script that copies the compiled
artefact into the Python package — mirroring `scripts/build_rust_abm.sh`.

Deliberate divergences from that precedent, which exists only for benchmarking:

- A **separate crate**, `packages/rust-piketty`, with module name
  `piketty_sim._rust_kernel`. Adding to `rust-abm` would couple the packages.
- The kernel takes the **full configuration**, not hardcoded defaults. The existing
  `run_simulation` accepts five scalars and reads its config from a Rust-side
  `Default`, which is fine for a benchmark and useless as a drop-in.
- Crates: `rand` and `rand_distr` for sampling, `ndarray` for agent state, `rayon`
  for parallelism across seeds and grid points. **Not** krABMaga: its
  model-exploration and genetic-algorithm calibration macros overlap with S14's
  machinery, and duplicating that layer is the specific escalation the source plan
  warns against. If the capstone ever outgrows a pyo3 kernel, krABMaga is the next
  step, not the starting point.

The shim keeps the choice invisible to callers:

```python
def kernel_available() -> bool
def simulate_wealth_fast(config, *, rng=None, ...) -> WealthPanel
```

`simulate_wealth_fast` dispatches to the extension when built and falls back to the
Python implementation otherwise, with the same signature and the same return type.
Root `ty` config already sets `unresolved-import = "warn"` precisely because such an
extension is not built in a normal dev environment, so no type-checking change is
needed.

**Parity is the requirement that makes the kernel trustworthy.** Bit-identical
output across languages is not achievable — the RNG streams differ — so parity is
statistical: on matched configurations, the two implementations must agree on the
distributional moments within a tolerance derived from seed variation, not within an
arbitrary epsilon. Concretely: run both across ten seeds and require the difference
in means to be small relative to the pooled standard deviation.

Speed-up is measured and recorded, not claimed. The motivating case is S14's grid ×
seed explosion, and the honest report is the observed factor on this hardware for
this workload.

## 4. Requirements

- [ ] **CAP-01** NB12 composes the full model with policy emerging from the feedback loop.
- [ ] **CAP-02** The three experiments are run and answered.
- [ ] **CAP-03** Validation discipline followed and evidenced.
- [ ] **CAP-04** Rust kernel is a drop-in behind the Python signature, skipped cleanly when unbuilt.
- [ ] **CAP-05** Python and Rust agree within documented tolerance; speed-up measured.

## 5. Tests

`tests/test_policy_feedback.py`

| ID | Test | Assertion |
|---|---|---|
| T15-1 | `test_feedback_disabled_reproduces_baseline` | With no parties, the panel reproduces S13's baseline bitwise. |
| T15-2 | `test_elections_occur_on_schedule` | Policy changes only at `election_interval` boundaries. |
| T15-3 | `test_policy_responds_to_distribution` | Starting from high inequality with a redistributive party available, the schedule becomes more progressive over time. |
| T15-4 | `test_inertia_smooths_policy` | Higher `policy_inertia` reduces period-to-period schedule variance. |
| T15-5 | `test_hysteresis_measurable` | The forward and reversed shock sequences produce measurably different trajectories, or the test records that they do not — either outcome passes, but the measurement must exist and be reported. |
| T15-6 | `test_composes_without_engine_changes` | The capstone runs using only `period_hooks` and config; asserted by confirming `kesten.py` is unchanged since S05 apart from documented seams. |

`tests/test_rust_parity.py` — every test begins with
`pytest.importorskip("piketty_sim._rust_kernel")`, following
`tests/test_abm_performance.py:301`.

| ID | Test | Assertion |
|---|---|---|
| T15-7 | `test_kernel_available_reports_truthfully` | `kernel_available()` matches whether the import succeeds. |
| T15-8 | `test_fallback_without_kernel` | With the extension absent, `simulate_wealth_fast` returns the same result as `simulate_wealth`. Runs in the default suite, unskipped. |
| T15-9 | `test_moment_parity` | Across ten seeds, Python and Rust moment means differ by less than the pooled seed standard deviation. |
| T15-10 | `test_tail_index_parity` | Fitted tail indices agree within the S05 tolerance band. |
| T15-11 | `test_config_passthrough` | Changing any config field changes the Rust result correspondingly — the kernel honours the whole config, not just a subset. |
| T15-12 | `test_speedup_recorded` | A benchmark runs and reports a factor; the test asserts the kernel is not *slower*, and the observed factor is recorded in §8. |

T15-8 is the one that must never be skipped: the fallback path is what most users
will exercise, and it is the path that silently rots if only the fast path is tested.

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_policy_feedback.py -v
uv run pytest packages/piketty-sim/tests/test_rust_parity.py -v      # mostly skipped
make test-piketty && make test                                       # without the kernel built
make build-rust-piketty
uv run pytest packages/piketty-sim/tests/test_rust_parity.py -v      # now unskipped
make test                                                            # with the kernel built
```

Pass criteria:

1. Every command exits zero, **both** with and without the extension built. A test
   suite that only passes in one of those two states is not acceptable.
2. All three experiments run, and their answers are recorded in §8 — including
   answers that do not favour the source material's thesis.
3. Validation discipline evidenced: stratum arithmetic written down, seed-stability
   report attached for every reported metric, and no reported effect smaller than its
   metric's seed variation.
4. Parity holds (T15-9, T15-10) and the measured speed-up is recorded.
5. Every earlier stage's pinned observations still reproduce.
6. `rg -e 'from companies_house' -e 'import companies_house' packages/piketty-sim/ packages/rust-piketty/` returns
   nothing.
7. NB12 opened interactively and run end to end; documented runtime for the full
   configuration.

## 7. Risks

- **Premature Rust.** Writing the kernel before the Python API is frozen means
  writing it twice. The stage ordering exists for this reason; if S05's signature is
  still in flux when this stage begins, freeze it first or defer the kernel and land
  the capstone on Python alone. A capstone without a kernel is a complete
  deliverable; a kernel against a moving API is waste.
- **Complexity collapse.** Composing eight mechanisms produces a model whose
  behaviour nobody can attribute. Mitigation: every mechanism must remain
  independently disableable, and the notebook must include an ablation — headline
  outcome with each mechanism switched off in turn. Without ablations the capstone is
  a black box, and the ablation table is arguably its most valuable output.
- **Parity chasing.** Pursuing bit-identical cross-language output wastes
  substantial time for no benefit. Statistical parity against seed variation is the
  correct standard and is what §3.4 specifies.
- **Runtime.** A million households over three centuries with parameter sweeps is a
  large computation. Report actual runtimes, keep the notebook's interactive
  configuration small, and reserve the large runs for explicit, non-reactive
  execution.
- **Confirmation pressure at the finale.** Experiment (a) is a genuine test of the
  book's central claim and experiment (b) of its framing. Both must be reported as
  they come out. A capstone that finds shocks alone sufficient, or finds no
  hysteresis, is a more interesting result than one that confirms everything.

## 8. Pinned results

*To be completed at implementation.*

| Quantity | Value | Note |
|---|---|---|
| Experiment (a): shocks-only fit to U-curve | — | correlation, RMSE |
| Experiment (a): shocks-plus-policy fit | — | correlation, RMSE |
| Experiment (a): conclusion | — | is policy required? |
| Experiment (b): forward vs reversed divergence | — | hysteresis present? |
| Experiment (c): outcome sensitivity to `r − g` | — | elasticity of top share |
| Strata count and minimum population | — | CAP-03 |
| Metrics stable at chosen population | — | of those reported |
| Ablation table | — | headline outcome per mechanism disabled |
| Rust speed-up | — | factor, workload, hardware |
| Full-configuration runtime | — | Python and Rust |
