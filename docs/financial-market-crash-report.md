# Financial Market Crash Model — Validation Report

**Status:** Phase 1 implemented and validated (core M1-M8, standalone daily
engine). Phases 0, 2-5 not implemented — see [Scope](#scope-of-this-pass).
**Companion documents:** [`financial-market-crash.md`](financial-market-crash.md)
(design plan this implements) · [`financial-market-crash-results.json`](financial-market-crash-results.json)
(raw numbers behind every figure quoted below).

## Scope of this pass

The design plan in `financial-market-crash.md` lays out a six-phase roadmap:
a Companies House data-pipeline extension (Phase 0), a standalone core
engine (Phase 1), NBFI-specific mechanisms — variation margin, redemptions,
funding rollover (Phase 2), endogenous cycles and a central-bank backstop
(Phase 3), coupling to the real-economy ABM (Phase 4), and calibration
sweeps against real data (Phase 5).

This pass implements **Phase 1 only**: the standalone daily leveraged-asset
market with the eight core mechanisms (M1-M8), calibrated from the
literature-sourced parameter values in the design doc rather than from
newly-ingested external data. That was a deliberate scope decision, agreed
before implementation started, because Phases 0 and 2-5 each involve
substantial additional work (new XBRL tags, new agent types, real BoE/SEC
data ingestion, coupling to a 1000-firm quarterly model) that would not fit
in a single implementation pass. Concretely, **not implemented**:
variation margin (M9), the redemption/fund-run channel (M10), funding
rollover risk (M11), heterogeneous fundamentalist/chartist switching (M12),
a central-bank backstop (M13), real-economy coupling (M14), and the
crowding/concentration diagnostic (M15). Every number in this report comes
from the Phase 1 engine only.

## What was built

All new code lives under `packages/companies-house-abm/src/companies_house_abm/`:

| File | Contents |
|---|---|
| `abm/assets/security.py` | `RiskyAsset` — price, fundamental value, ADV, EWMA volatility, haircut, transient-impact state |
| `abm/agents/investor.py` | `LeveragedInvestor` — M1 (position-taking), M3 (margin calls) |
| `abm/agents/dealer.py` | `Dealer` — M5 (capital-limited liquidity supply) |
| `abm/markets/funding.py` | `compute_haircuts` — M2 (procyclical haircuts) |
| `abm/markets/asset_market.py` | `AssetMarket` — the within-day sequence (§5.5), M4 (price impact), M6 (mark-to-market), M8 (default resolution), and the fire-sale cascade iteration |
| `abm/financial_model.py` | `FinancialSimulation` — the standalone daily `Model`, mirroring the existing quarterly `Simulation`'s structure |
| `reporting/financial_metrics.py` | Tier 1/2 validation diagnostics (Hill tail exponent, ACF, skew/kurtosis, leverage effect, procyclicality) |
| `abm/config.py` | `RiskyAssetConfig`, `InvestorConfig`, `MarginConfig`, `MarketLiquidityConfig`, `FinancialMarketConfig`, hung off `ModelConfig` per the design doc, plus a new `financial:` block in `config/model_parameters.yml` |
| `tests/test_abm_financial_market.py` | 22 unit tests covering the balance-sheet identities, margin-call triggers, haircut computation, dealer capacity, and simulation-level invariants |
| `scripts/financial_crash_experiments.py` | Reproduces every number in this report |

Overlapping portfolios (M7) are not a separate mechanism in this
implementation — they fall out of the design directly: investors draw a
random basket of assets weighted toward a shared "core" pool
(`portfolio_overlap`), so a common-factor shock or a fire sale in one asset
mechanically marks down every other investor who happens to hold it.

### Deliberate simplifications versus the design doc

- **Single net-debt wedge instead of separate cash/margin-loan accounts.**
  `LeveragedInvestor.net_debt` can be positive (a margin loan) or negative
  (surplus cash); this is algebraically identical to §5.3's
  `equity = assets - liabilities` for every computation that matters
  (equity, leverage, collateral value) and matches the aggregate-fund
  abstraction in Thurner, Farmer & Geanakoplos (2012), the paper the design
  doc names as the closest published analogue. A dedicated `Position`
  class (per-loan bookkeeping, as in `assets/mortgage.py`) was dropped as
  unnecessary complexity for a portfolio-level margin loan.
- **`Dealer` does not subclass `Bank`.** The design doc suggests extending
  the existing `Bank` agent; this implementation keeps `Dealer` independent
  because the quarterly `Bank`'s interface (loan books, deposits, capital
  ratios) doesn't map cleanly onto inventory-based market-making, and Phase
  1 is explicitly standalone.
- **No separate `funding.py` rollover market.** `markets/funding.py` holds
  only the haircut function (M2); rollover risk (M11) is an explicit
  Phase-2 extension, out of scope here.
- **Demand has two components, not one.** The design doc's M1 says demand
  "scales with perceived mispricing." A pure softmax-over-mispricing
  allocation *within* an investor's basket turned out to be insufficient on
  its own: a common-factor shock moves every held asset's fundamental value
  together, so relative mispricing inside the basket barely changes and a
  softmax-only investor would not trade at all in response to genuine
  market-wide news. The implementation adds a second term — the *level* of
  desired exposure scales with the basket's average mispricing
  (`mispricing_sensitivity`, clipped to `[0.1, 3x target]` to prevent the
  unbounded leverage swings described below) — so that market-wide news
  actually generates order flow. This is noted here because it is the one
  place where implementation surfaced a real gap in the M1 specification
  as written.

## Two bugs the validation process caught

Building the standalone module surfaced two non-obvious bugs, both fixed
before any of the numbers below were generated. They are worth recording
because they are the kind of thing a design document cannot anticipate and
only a running simulation exposes:

1. **Volatility was being measured against a same-day return of exactly
   zero.** The initial implementation called `roll()` (which resets the
   return-calculation anchor to the current price) *before* that day's
   trading happened, so `update_volatility()` always saw `daily_return ==
   0`. The EWMA volatility collapsed toward zero within ~100 days
   regardless of how much prices actually moved. Fixed by moving the
   volatility update and roll to the end of the day, after price impact has
   been applied.
2. **Realised volatility spiralling to zero fed back into price impact
   and froze the market.** Because the square-root price-impact law scales
   with realised volatility (M4), and realised volatility is itself
   computed from *realised* price moves, an initial quiet day could
   self-reinforce: lower measured volatility → smaller impact from the same
   order flow → an even quieter next day → volatility decays further. Over
   a few hundred days the price would freeze completely (to the decimal)
   while investors' *desired* trades kept growing, because nothing was left
   to translate order flow into a price move. Fixed with a volatility floor
   (`volatility_floor`, default 0.1%/day) below which the EWMA cannot decay
   — a pragmatic fix, not a literature-derived one, and worth re-examining
   in any future recalibration.

## Validation results

All figures below are from `scripts/financial_crash_experiments.py`,
seeded and reproducible; raw output is in
`financial-market-crash-results.json`. Baseline configuration: 8 assets, 200
investors, target leverage 3.0×, 1,500 trading days (~6 years).

### Tier 1 — return stylised facts (Cont 2001)

| Stylised fact | Target | Result | Verdict |
|---|---|---|---|
| Fat tails | tail exponent ≈ 3 | Hill exponent **1.20** | Tails present but **far fatter** than the empirical ~3 |
| Excess kurtosis | > 0, typically 5-50 | **35.0** | ✓ in range |
| Volatility clustering | slow-decaying ACF of \|returns\| | lag-1 **0.63**, lags 2-20 stay in **0.42-0.63**, no clean monotonic decay | ✓ present, shape doesn't match the smooth power-law decay usually reported |
| No linear return autocorrelation | ACF(lag 1) ≈ 0 | **0.42** | ✗ **fails** — see below |
| Leverage effect | corr(r_t, \|r_{t+1}\|) < 0 | **-0.075** | ✓ correct sign, weak |
| Aggregational Gaussianity | tails thin at longer horizons | not tested this pass | not evaluated |

The return-autocorrelation failure is the most important finding here and
is mechanistic, not mysterious: `rebalancing_speed = 0.25` means a voluntary
order only closes 25% of the gap to the desired position each day, so a
price move that starts today keeps propagating (weaker, same direction) for
several subsequent days as investors continue closing the same gap. That
manufactures exactly the kind of short-horizon momentum real markets don't
show. A future calibration pass should either raise `rebalancing_speed`
substantially or decouple trading speed from the autocorrelation structure
directly (e.g. an order-splitting model with a shorter memory).

The over-fat tails are plausibly connected to the same mechanism plus the
margin-call/cascade logic: forced sales occasionally clear several days'
worth of price adjustment in one step, producing occasional large jumps on
top of an otherwise quiet return distribution — a mixture that produces
fatter tails than a single volatility regime would.

### Tier 2 — crash-specific diagnostics

| Diagnostic | Target | Result | Verdict |
|---|---|---|---|
| Leverage is procyclical | corr(aggregate leverage, price) > 0 | **+0.37** | ✓ correct sign, moderate — directionally consistent with the FINRA margin-debt pattern the design doc cites, though not fitted to the FINRA series itself |
| Margin calls are rare in calm regimes | low frequency | **134 calls / 1,500 days** across 200 investors (≈ 0.09/investor/year) | ✓ plausible |
| No defaults in the calm baseline | 0 | **0** | ✓ |

### Tier 3 — the M2 counterfactual (does the amplifier do the work?)

The design doc's key internal check (§7): *"without procyclical haircuts
(M2 off), the crash should be materially smaller."* Two shock scenarios
were run with `procyclical_haircuts` on and off, holding the random seed
and shock fixed:

| Scenario | Shock | Max drawdown, M2 on | Max drawdown, M2 off | Amplification ratio |
|---|---|---|---|---|
| "LDI-shaped" (gilt-class assets only, -12%, target leverage 5×) | day 150 | **-24.17%** | **-24.10%** | **1.003** |
| "COVID-shaped" (all assets, -25%, target leverage 3.5×) | day 150 | **-6.29%** | **-6.29%** | **1.000** |

**This counterfactual fails at the current calibration: procyclical
haircuts make essentially no difference.** Digging into why is itself a
useful result. A margin call fires when either the leverage cap
(`leverage > target_leverage × margin_call_multiple`, fixed at 1.15×) or the
collateral/haircut constraint (`net_debt > Σ(1-haircut)×holdings×price`) is
breached. At target leverage 5× with `haircut_max = 0.5`, the collateral
constraint only starts to bind once realised volatility exceeds roughly
16.7%/day (`0.5 = 3.0 × vol`) — far above anything the shocks in this run
produce. In practice, **the fixed leverage cap is the only constraint that
ever binds**, so turning the haircut off changes almost nothing.

This reproduces, in miniature, exactly the critique the design doc opens
with (§1, point 1): *"with a fixed leverage limit... the amplification is
bounded and roughly linear... procyclical margin is the amplifier, not
leverage per se."* The current Phase 1 calibration has accidentally built
the naive mechanism the design doc warns against, alongside the intended
one, and the naive one is dominating. **Recommended fix for a future
calibration pass:** loosen `margin_call_multiple` (e.g. to 2-3×) or tighten
`var_multiplier` so that realistic stress-level volatility pushes haircuts
into the binding range before the fixed leverage cap does — i.e.
deliberately make procyclical haircuts, not the leverage cap, the load-bearing
constraint, then re-run this counterfactual.

### Verdict: how well does Phase 1 reproduce historic crash dynamics?

**Partially, and unevenly.** The model reproduces some qualitative
signatures of real crashes purely from the core mechanisms — fat tails,
volatility clustering, procyclical leverage that rises in calm periods and
would fall in a stress episode, margin calls concentrated around shocks
rather than spread evenly. It does **not** yet demonstrate that its
headline amplifier (procyclical haircuts) is doing more work than a naive
fixed leverage cap would, which is the specific mechanism the literature
review identifies as separating a realistic crash model from a
toy one. And because M9-M13 (variation margin, redemptions, rollover risk,
heterogeneous beliefs, central-bank backstop) are not implemented, the
"LDI-shaped" and "COVID-shaped" scenarios above are only shaped like those
episodes in the size and timing of the shock — they do not model the
mechanisms (derivative margin calls, fund redemptions) that BoE and IMF
research identifies as the actual proximate cause of those two crashes.
Genuine episode replication (the design doc's Tier 3 in the strict sense —
"the model should attribute roughly half the gilt price fall to forced LDI
selling") is a Phase 2 deliverable, not a Phase 1 one, and this report
should not be read as claiming it.

## Applying this to today's AI-driven US market

This section is explicitly illustrative, not a calibrated forecast. No US
equity data was ingested; the `ai_concentration` scenario below uses the
same synthetic fundamentals process as everything else, with parameters
chosen to caricature three structural features of the current market rather
than to fit any real time series.

### What the scenario changes, and why

| Parameter | Baseline | AI-concentration | Real-world analogue |
|---|---|---|---|
| Asset count | 8 | **4** | A handful of names (the "Magnificent Seven" plus AI-capex beneficiaries) now account for a historically unusual share of US index market cap and of index-level return variance |
| `common_factor_share` | 0.5 | **0.9** | AI-capex names move together on shared macro/AI-capex-cycle news to an unusual degree |
| `portfolio_overlap` | 0.6 | **0.9** | Passive/index ownership and crowded hedge-fund positioning mean most investors hold nearly the same basket |
| `target_leverage_std` | 1.0 | **2.0** | A fatter leverage tail — options exposure, structured products and margin lending create pockets of much higher effective leverage than the market-wide average |

### Results

| Metric | Baseline | AI-concentration |
|---|---|---|
| Daily return std | 0.06% | **4.06%** |
| Excess kurtosis | 35.0 | **354** |
| Skewness | -0.10 | **-18.2** |
| Hill tail exponent | 1.20 | **0.93** (fatter still) |
| Cross-asset return correlation | not applicable (diversified) | **0.87** |
| Leverage effect | -0.075 | **-0.69** (much stronger) |
| Investor defaults over 750 days | 0 / 200 | **178 / 200 (89%)** |

The direction of every one of these is what the mechanisms would predict:
concentrating exposure in fewer, more correlated, more leveraged names
removes the diversification that dampens shocks in the baseline, so the
same class of fundamental shocks that the baseline absorbs produces mass
insolvency here. The **89% default rate is an artefact of a deliberately
extreme, illustrative parameterisation** (a 750-day run with no
diversification and a leverage tail reaching 7-8×) — it is a demonstration
that the mechanism *can* produce systemic fragility under concentration,
not a prediction that 89% of leveraged AI-stock investors will default.

### What this suggests about the current market, read qualitatively

- **Concentration is the first-order risk channel the model highlights.**
  The mechanism that matters here is not leverage in isolation but leverage
  *combined with* correlation and crowding (M7, overlapping portfolios) —
  exactly the Caccioli et al. (2014) phase-transition result the literature
  review cites. A market where the majority of index returns are driven by
  a handful of AI-capex-linked names is structurally the "high crowding,
  high correlation" regime in which that phase transition occurs.
- **The model's biggest blind spot for this application is the
  redemption channel (M10), not leverage.** US equity ownership today is
  dominated by passive/index funds and ETFs to a degree the original design
  doc's UK-focused NBFI section (§2.6) does not emphasise (that section is
  built around open-ended bond funds and LDI). A concentration-driven
  sell-off in a market this passively owned would likely be amplified by
  mechanical index/ETF redemption flows — the same "reverse flight to
  liquidity" mechanism documented for March 2020 corporate-bond funds
  (Falato, Goldstein & Hortaçsu 2021), but via index rebalancing rather than
  active credit selling. This is squarely M10 territory and is not built.
- **A genuinely new mechanism would be needed that the original design
  doc does not cover at all: circular vendor financing.** Recent AI-capex
  financing arrangements — where AI infrastructure buyers, chip suppliers
  and cloud providers are financially intertwined through investment,
  supply and offtake agreements — create a correlated-default channel that
  doesn't map onto any of M1-M15 as written. It behaves like a hybrid of
  overlapping portfolios (M7) and price-mediated contagion, but through
  *revenue* and *capex* dependencies between firms rather than shared asset
  holdings between investors. Modelling it properly would mean coupling the
  financial-crash module to the firm-level real-economy ABM's supply-chain
  representation (a Phase 4 concern) rather than anything in Phase 1-3.
- **What would be needed to make this rigorous rather than illustrative:**
  (1) real market-cap weights, realised correlations and margin-debt levels
  for the relevant names (FINRA margin statistics, 13F/N-PORT holdings data
  — sources already catalogued in §6 of the design doc); (2) the redemption
  channel (M10) calibrated to passive/ETF flow data rather than open-ended
  bond funds; (3) the circular-financing mechanism above; (4) the M2
  recalibration fix from the previous section, since an uncalibrated
  haircut amplifier undermines any crash-depth conclusion drawn from this
  model as much here as in the UK scenarios.

## Limitations and recommended next steps

- **Fix the M2/leverage-cap calibration** (above) before trusting any
  drawdown-depth comparison from this model, including the AI-concentration
  numbers.
- **The return-autocorrelation failure** (ACF(1) = 0.42 vs. a target near
  zero) should be resolved before using this model for anything that
  depends on short-horizon return dynamics; the likely fix is decoupling
  trade-execution speed from `rebalancing_speed`, or increasing it
  substantially.
- **No real data was ingested.** Every parameter in this report is either
  the design doc's literature-sourced default or a hand-chosen illustrative
  value for the AI scenario. Phase 0 (Companies House investment-trust XBRL
  extraction) and the wider §6 data-sourcing plan remain undone.
- **M9-M15 are not implemented.** In particular, M10 (redemptions) is the
  single highest-priority addition for both the March-2020 replication the
  design doc targets and the AI-concentration application above.
- **Aggregational Gaussianity** (Tier 1's fifth stylised fact) was not
  evaluated this pass.
- **Coupling to the real-economy model (Phase 4)** and the central-bank
  backstop (M13, Phase 3) remain future work; without M13 every shock in
  this model runs to whatever floor the mechanics produce, with no policy
  response to compare against — a real limitation for any policy-relevant
  use of the model.

## Reproducing this report

```bash
uv run python scripts/financial_crash_experiments.py
uv run pytest tests/test_abm_financial_market.py
```

Both are deterministic given the seeds hard-coded in the script and tests.
