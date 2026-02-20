# Stochastic Behaviour and Bounded Rationality: Design Plan

This document sets out a plan to enrich the Companies House ABM with stochastic
shocks and boundedly rational decision rules. The current model uses deterministic
behavioural rules (fixed markups, fixed MPC, Taylor-rule policy). The additions
described here will make individual agents more realistic and the macro dynamics
more varied across runs.

---

## 1. Motivation

Real economies exhibit:

- **Idiosyncratic volatility** — individual firms and households face private
  uncertainty independent of aggregate shocks.
- **Bounded rationality** — agents form expectations with limited information and
  cognitive resources; they do not solve full dynamic optimisation problems.
- **Emergent coordination failures** — recessions and credit crunches arise from
  individually sensible decisions interacting badly.

Adding stochastic elements and bounded-rationality rules will allow the model to
reproduce stylised facts such as fat-tailed firm-size distributions, persistent
unemployment, and asymmetric business cycles that the current deterministic model
cannot generate.

---

## 2. Taxonomy of Stochastic Extensions

### 2.1 Aggregate Shocks

| Shock | Description | Implementation |
|---|---|---|
| **Demand shock** | Uniform shift in household autonomous consumption | Multiplicative noise term on `HouseholdConfig.income_mean` each quarter |
| **Productivity shock** | TFP perturbation applied to all firms | Multiplicative AR(1) process on firm output; configurable persistence (ρ) and volatility (σ) |
| **Financial shock** | Sudden tightening of bank lending standards | Step-change in `BankBehaviorConfig.lending_threshold`; recovers at exponential rate |
| **Policy shock** | Surprise deviation from Taylor rule | Additive noise on the central bank rate target, drawn from N(0, σ_mp) |

These are already partially scaffolded in `config/model_parameters.yml` under the
`shocks` key but are all disabled. Enabling them requires:

1. A `ShockSchedule` dataclass in `config.py` that holds shock timing, magnitude, and
   duration.
2. A `ShockManager` class in `abm/shocks.py` called from `Simulation.step()` before
   the agent activation sequence.

### 2.2 Idiosyncratic Shocks

Each agent draws a private shock every period from a configurable distribution:

| Agent | Shock variable | Suggested distribution |
|---|---|---|
| **Firm** | Productivity level | Log-normal multiplicative noise: exp(σ_f · ε), ε ~ N(0,1) |
| **Firm** | Entry / exit | Bernoulli draw against endogenous profitability threshold |
| **Household** | Income | Log-normal income shock: captures job loss, bonus, illness |
| **Household** | MPC | Transitory preference shock drawn from Beta distribution |
| **Bank** | Loan loss rate | Beta-distributed realised default, independent of expected rate |

---

## 3. Bounded Rationality Rules

### 3.1 Firms: Markup Heuristic with Satisficing

**Current behaviour**: Firms adjust price markup by a fixed speed toward a target
inferred from excess demand.

**Planned behaviour**: Firms use a *satisficing* rule (Simon 1955). They hold the
markup fixed if profit exceeds a target threshold and adjust only when profit falls
below it:

```
if profit / turnover < aspiration_level:
    markup += adjustment_speed * excess_demand_signal + η
else:
    markup += 0          # satisficed — no change
```

where `η ~ N(0, σ_markup)` is experimentation noise and `aspiration_level` is set
to rolling-average profitability over a configurable window. This produces
heterogeneous, history-dependent markups rather than convergence to a common value.

**Parameters to add to `FirmBehaviorConfig`**:

```yaml
aspiration_window: 8          # quarters of profit history to average
markup_noise_std: 0.005       # standard deviation of experimentation noise
aspiration_level: 0.05        # initial profit-rate target
```

### 3.2 Households: Adaptive Expectations

**Current behaviour**: Households consume a fixed fraction of current income plus a
wealth draw. Expectations are implicitly perfect.

**Planned behaviour**: Households form adaptive expectations about future income
using an exponential moving average:

```
expected_income_t = α * income_{t-1} + (1 - α) * expected_income_{t-1}
consumption_t = mpc * expected_income_t + (1 - mpc) * permanent_income
```

where `α` is the adaptation speed (low → slow learning, anchored expectations).
This creates consumption smoothing that responds to *perceived* permanent income
rather than realised quarterly income, matching empirical consumption dynamics.

**Parameters to add to `HouseholdBehaviorConfig`**:

```yaml
expectation_adaptation_speed: 0.3   # α above
buffer_stock_target: 3.0            # target wealth / quarterly income ratio
precautionary_saving_intensity: 0.2 # extra saving when wealth below target
```

### 3.3 Firms: Near-Neighbour Pricing

Firms observe a random sample of competitors' prices each period (rather than the
market average) and anchor their price to the sample minimum plus markup. This
models *search-based* price competition with information frictions.

**Implementation**:

- In `GoodsMarket.clear()`, expose a `sample_n_competitors` parameter (default: 5).
- Before firms set prices in `Firm.step()`, they receive a list of sampled
  competitor prices from the market's previous period.
- Price target = min(sampled_prices) × (1 + markup).

### 3.4 Banks: Rule-of-Thumb Credit Scoring

**Current behaviour**: Banks evaluate loans against hard capital and collateral
thresholds (deterministic credit rationing).

**Planned behaviour**: Banks use a noisy credit score that combines the deterministic
signals with idiosyncratic assessment error:

```
score = w1 * capital_ratio + w2 * collateral_ratio + w3 * debt_coverage + ε
ε ~ N(0, σ_credit)
approve if score > lending_threshold
```

This means otherwise-identical firms receive different credit outcomes in the same
quarter, creating realistic cross-sectional dispersion in financing conditions.

**Parameters to add to `BankBehaviorConfig`**:

```yaml
credit_score_weights: [0.4, 0.4, 0.2]   # capital, collateral, coverage
credit_score_noise_std: 0.05
```

### 3.5 Central Bank: Imperfect Information and Forecast Errors

The Taylor rule currently uses the realised inflation and a zero output gap. A
more realistic rule operates on *estimated* values that deviate from truth:

```
inflation_estimate = inflation_true + ε_π,  ε_π ~ N(0, σ_π_obs)
output_gap_estimate = output_gap_true + ε_y, ε_y ~ N(0, σ_y_obs)
```

This adds a *measurement error* layer, meaning the central bank can
systematically over- or under-shoot even with a correctly specified Taylor rule —
matching the empirical finding that monetary policy errors have a stochastic
component.

**Parameters to add to `TaylorRuleConfig`**:

```yaml
inflation_observation_noise: 0.003    # 0.3 pp std deviation
output_gap_observation_noise: 0.010   # 1 pp std deviation
```

---

## 4. Implementation Roadmap

### Phase 1 — Infrastructure (no behaviour change yet)

1. Add `ShockSchedule` dataclass to `config.py` and wire into `model_parameters.yml`.
2. Add `ShockManager` class to `abm/shocks.py` with an `apply(sim, period)` method.
3. Add per-agent RNG streams derived from the global seed (each agent gets its own
   `np.random.default_rng(seed + agent_index)`) to ensure reproducibility when the
   number of agents changes.
4. Expose `shock_log: list[dict]` on `SimulationResult` to record every shock applied
   and its magnitude.

### Phase 2 — Idiosyncratic shocks

5. Add `productivity_shock_std` to `FirmBehaviorConfig`; apply in `Firm._produce()`.
6. Add `income_shock_std` to `HouseholdConfig`; apply in `Household._receive_income()`.
7. Add `loan_loss_noise_std` to `BankBehaviorConfig`; apply in `Bank.step()`.

### Phase 3 — Bounded rationality rules

8. Implement satisficing markup in `Firm._set_price()`.
9. Implement adaptive expectations in `Household._consume()`.
10. Implement near-neighbour pricing by passing competitor sample into `Firm.step()`.
11. Implement noisy credit scoring in `Bank.evaluate_loan()`.
12. Implement measurement-error Taylor rule in `CentralBank.step()`.

### Phase 4 — Aggregate shocks and calibration

13. Activate the `shocks` block in `model_parameters.yml` with UK-calibrated values.
14. Run ensemble simulations (different seeds) to quantify uncertainty bands around
    macro trajectories.
15. Compare unconditional moments (output volatility, inflation persistence, Okun
    coefficient) with UK ONS data.

---

## 5. Calibration Targets

The stochastic extensions should be calibrated to reproduce the following UK
empirical moments (ONS / BoE sources, 1993–2023):

| Moment | Target | Notes |
|---|---|---|
| GDP growth std dev | 1.0% per quarter | Real GDP growth volatility |
| Inflation std dev | 1.2% annualised | CPI |
| Unemployment rate std dev | 0.8 pp | ILO measure |
| Firm entry rate | 11% per year | Companies House data |
| Firm exit rate | 9% per year | Companies House data |
| Consumption / income correlation | 0.65 | National accounts |

---

## 6. Testing Approach

Each new stochastic component will be covered by:

- **Unit tests** verifying that shocks are drawn from the correct distribution and
  applied to the correct agent attribute.
- **Seed-reproducibility tests** confirming that two runs with the same seed
  produce byte-identical `SimulationResult` objects.
- **Ensemble smoke tests** (marked `@pytest.mark.slow`) running N=20 replicates and
  checking that cross-replicate standard deviations lie within plausible ranges.

---

## 7. References

- Simon, H.A. (1955). *A behavioural model of rational choice.* Quarterly Journal
  of Economics, 69(1), 99–118.
- Dosi, G., Fagiolo, G., & Roventini, A. (2010). *Schumpeter meeting Keynes.*
  Journal of Economic Dynamics and Control, 34(9), 1748–1767.
- Gabaix, X. (2014). *A sparsity-based model of bounded rationality.* Quarterly
  Journal of Economics, 129(4), 1661–1710.
- Benes, J., et al. (2014). *Estimating potential output with a multivariate filter.*
  IMF Working Paper WP/10/285.
