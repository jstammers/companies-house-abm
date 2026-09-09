# Financial Market Crash Model — Literature Review, Data Review and Design Plan

**Status:** Design proposal. No implementation yet.
**Scope:** A leveraged-investor asset market module for `companies_house_abm`,
capable of reproducing recent financial crashes and coupling to the existing
real-economy ABM.

---

## 1. The Proposed Mechanism, and What Is Missing From It

The starting proposal is:

> Investors borrow from lenders to buy stocks. They must service debt and
> reinvest to grow. Falling prices trigger a sell-off because investors need to
> cover debts; too few buyers creates a liquidity problem; if assets fall below
> liabilities the investor is insolvent.

This is the core of the **leverage cycle** (Geanakoplos 2010; Thurner, Farmer &
Geanakoplos 2012) and it is the right skeleton. But as stated it will *not*
produce a crash of realistic size or shape. Four things are load-bearing and
absent:

1. **Nothing makes the constraint tighten as prices fall.** With a fixed
   leverage limit, a price fall mechanically raises leverage and forces some
   selling — but the amplification is bounded and roughly linear. Real crashes
   are non-linear because *lenders raise haircuts and margins exactly when
   volatility rises* (Brunnermeier & Pedersen 2009; CGFS 2010). Procyclical
   margin is the amplifier, not leverage per se.
2. **"Too few buyers" needs a price-impact function and a modelled liquidity
   supplier.** Without an explicit market-depth/impact rule and agents whose
   *own* capital limits how much they can absorb, the depth of the crash is a
   free parameter rather than a model output (Cont & Schaanning 2017;
   Baranova, Douglas & Silvestri 2019).
3. **Debt repayment is not the only forced-sale trigger.** Two others dominate
   recent episodes: **refusal to roll over** short-term funding (repo runs,
   2008) and **investor redemptions** from open-ended funds (March 2020). Both
   force sales without any covenant being breached.
4. **One asset is not enough.** Price-mediated contagion — the dominant
   post-2008 systemic channel — works through *overlapping portfolios*: A sells
   asset X, depressing X, which marks down B, who sells Y, which hits C
   (Caccioli et al. 2014; Cont & Schaanning 2017; Duarte & Eisenbach 2021).
   A single-asset model cannot represent it.

Section 5 lists the full set of mechanisms recommended, split into a minimum
viable core and layered extensions.

---

## 2. Literature Review

### 2.1 Leverage cycles and endogenous leverage

- **Geanakoplos (2010), "The Leverage Cycle"** (NBER Macro Annual 24): leverage
  is an equilibrium object, not a parameter. Collateral requirements are set by
  lenders and move with perceived tail risk, so leverage rises in calm periods
  and collapses in bad ones. **Fostel & Geanakoplos (2014)** formalises the
  general-equilibrium version. *Implication:* haircuts must be endogenous.
- **Thurner, Farmer & Geanakoplos (2012), "Leverage causes fat tails and
  clustered volatility"** (*Quantitative Finance* 12(5)): the canonical ABM for
  this problem. Value-investing leveraged funds + noise traders + a bank that
  issues margin loans. Deleveraging alone generates fat-tailed returns and
  clustered volatility from Gaussian fundamentals. **This is the closest
  published analogue to the requested model and should be the reference
  implementation for the core.**
- **Aymanns & Farmer (2015), "The dynamics of the leverage cycle"** (*JEDC*
  50): adds a VaR-based (Basel-style) leverage constraint and shows the system
  undergoes a Hopf bifurcation into endogenous boom–bust cycles as risk
  management gets more aggressive. **Aymanns, Caccioli, Farmer & Tan (2016),
  "Taming the Basel leverage cycle"** (*JFS* 27) shows counter-cyclical
  buffers can stabilise it — a ready-made policy experiment.
- **Adrian & Shin (2010), "Liquidity and leverage"** (*JFI* 19(3)): empirically,
  broker-dealer leverage is *procyclical* — balance sheets expand when asset
  prices rise. Target-leverage behaviour ("actively manage to a leverage
  target") is the right default rule for dealer-type agents.
- **Poledna, Thurner, Farmer & Geanakoplos (2014)** (*JBF* 42): the same ABM
  used to evaluate Basel II, expected shortfall and a leverage tax. Confirms
  that regulation which is risk-sensitive *at the individual level* can
  increase systemic risk.

### 2.2 Funding liquidity ↔ market liquidity spirals

- **Brunnermeier & Pedersen (2009), "Market Liquidity and Funding Liquidity"**
  (*RFS* 22(6)): the two "spirals" — the *loss spiral* (mark-to-market losses
  reduce capital, forcing sales) and the *margin spiral* (higher volatility
  raises margins, forcing more sales). Liquidity is fragile: it can be
  destabilising because margins are increasing in volatility. **This paper
  defines the two feedback loops the model must contain.**
- **Shleifer & Vishny (1992, 2011)**: fire-sale prices are set by the *second-
  best user's* valuation, so specialised assets sold into a distressed sector
  clear far below fundamental value.
- **Gromb & Vayanos (2002, 2010)**, **Duffie (2010) "Slow-moving capital"**:
  arbitrage capital arrives with a lag, so mispricing persists. Motivates a
  "slow capital" replenishment rate rather than instantaneous liquidity supply.
- **He & Krishnamurthy (2013), "Intermediary asset pricing"** (*AER* 103(2))
  and **Adrian, Etula & Muir (2014)**: intermediary capital is a priced state
  variable — risk premia spike when intermediary equity is depleted. Justifies
  making the dealer's capital the key state variable for market depth.

### 2.3 Fire sales and price-mediated (indirect) contagion

- **Cifuentes, Ferrucci & Shin (2005), "Liquidity risk and contagion"**
  (*JEEA* 3): the canonical mark-to-market + regulatory-ratio fire-sale model.
  A downward-sloping inverse demand curve for the asset plus solvency
  constraints produces contagion *without any direct counterparty exposure*.
- **Caccioli, Shrestha, Moore & Farmer (2014)** (*JBF* 46): stability analysis
  of contagion via overlapping portfolios. Identifies a sharp phase transition
  in (leverage, diversification, market crowding) space — the system is stable
  until it abruptly is not.
- **Greenwood, Landier & Thesmar (2015), "Vulnerable banks"** (*JFE* 115(3)):
  a tractable linear-algebra formula for "aggregate vulnerability" from a
  holdings matrix, leverage vector and impact parameter. **Directly
  implementable as a diagnostic on model state and as an empirical target.**
- **Duarte & Eisenbach (2021), "Fire-Sale Spillovers and Systemic Risk"**
  (*JF* 76(3)): extends the above with empirical US bank data; shows
  spillovers spike ahead of crises. Useful for validation.
- **Cont & Schaanning (2017/2019), "Fire sales, indirect contagion and
  systemic stress testing"** (Norges Bank WP 2/2017): introduces *liquidity-
  weighted portfolio overlap* and shows deleveraging changes stress-test
  outcomes materially. Supplies a concrete, calibrated price-impact
  specification (see §6.3).

### 2.4 Price impact and the supply of liquidity

- **Kyle (1985)**: linear impact, `Δp = λ·q`. Simple, still the default for
  aggregate models.
- **Tóth et al. (2011), "Anomalous price impact and the critical nature of
  liquidity"** (*PRX* 1) and **Bouchaud, Farmer & Lillo (2009)**: empirically
  impact is *concave* — the **square-root law**, `Δp/p ≈ Y·σ_daily·√(Q/V_daily)`
  with `Y ≈ 0.5–1`. Confirmed across equities, FX, futures and credit; recent
  work (Tokyo Stock Exchange, 2024–2026) finds it strictly universal.
  **Recommendation: use the square-root law as the default impact function** —
  it is empirically grounded, has only one free parameter, and needs only daily
  volatility and daily volume, both freely available.
- **Cont & Schaanning**: use an exponential/linear-in-`Q/depth` form with a
  market-depth parameter calibrated from ADV; equivalent in the small-`Q` limit.
- **Coval & Stafford (2007)** (*JFE* 86): empirical fire-sale price impact from
  mutual-fund flow-driven trades — a clean identification of impact magnitudes
  and, importantly, of the *reversal* horizon (transient vs permanent impact).

### 2.5 Heterogeneous beliefs — how the boom gets built

A crash model that only ever receives exogenous shocks cannot explain the
build-up. To get an endogenous bubble:

- **Brock & Hommes (1998)** (*JEDC* 22): fundamentalists vs. trend-followers
  with evolutionary switching on realised profit — routes to chaos.
- **Lux & Marchesi (1999)** (*Nature* 397): herding/switching between chartists
  and fundamentalists reproduces fat tails and volatility clustering.
- **Chiarella, Dieci & He (2009)**: survey of heterogeneous-agent asset pricing.
- **Minsky (1986/1992) Financial Instability Hypothesis**; **Kindleberger &
  Aliber**: stability breeds risk-taking. The existing `docs/abm-design.md`
  already proposes the hedge/speculative/Ponzi taxonomy — reuse it for
  investors, not just firms.

### 2.6 Non-bank financial intermediation — the mechanisms behind recent crashes

- **Open-ended funds and redemption runs.** **Chen, Goldstein & Jiang (2010)**
  (*JFE* 97): payoff complementarities create a first-mover advantage and
  strategic complementarity in redemptions. **Falato, Goldstein & Hortaçsu
  (2021)** (*JME* 123) and **Ma, Xiao & Zeng (2022)** (*RFS*): March 2020
  corporate-bond fund fragility and "reverse flight to liquidity" — funds sold
  *liquid* assets first, spreading the shock. **BIS (2021), "Open-ended bond
  funds: systemic risks and policy implications"**; **BIS Bulletin 39**: funds
  sold *more* than redemptions required, rebuilding cash buffers.
- **Margin and collateral procyclicality.** **CGFS (2010), "The role of margin
  requirements and haircuts in procyclicality"**: the definitive policy
  treatment. Derivatives *variation margin* is a cash drain that is entirely
  independent of any asset sale — the LDI mechanism.
- **The 2022 UK gilt/LDI crisis.** **Bank of England SWP 1019 (2023), "An
  anatomy of the 2022 gilt market crisis"**; **Bank Underground (2024), "What
  caused the LDI crisis?"** — LDI selling accounted for roughly *half* the fall
  in gilt prices, fiscal news the other half. **IMF WP 23/210, Chen & Kemp,
  "Putting Out the NBFIRE"**; **BIS Quarterly Review (Dec 2022)**. Pooled LDI
  funds were the most levered and worst affected. **This is the single best
  target episode for a UK-focused model.**
- **Repo runs.** **Gorton & Metrick (2012)** (*JFE* 104): the 2007–08 run on
  repo via haircuts. **Krishnamurthy, Nagel & Orlov (2014)**: the run was
  concentrated in bilateral/dealer repo, not tri-party.
- **Dealer capacity.** **Baranova, Liu & Shakir (2017), BoE SWP 665**: a
  partial-equilibrium model of dealer intermediation under leverage-ratio
  constraints. **Baranova, Douglas & Silvestri (2019), BoE SWP 803,
  "Simulating stress in the UK corporate bond market"** and **BoE Financial
  Stability Paper 42 (2017)**: a calibrated UK simulation of investor sales vs.
  dealer absorption. **Braun-Munzinger, Liu & Turrell (2016), BoE SWP 592**: an
  ABM of corporate-bond trading dynamics. These are the closest UK-calibrated
  precedents and their structure should be borrowed directly.
- **Bank of England System-Wide Exploratory Scenario (SWES), final report
  Nov 2024**: the most useful single document for calibration targets. Key
  qualitative and quantitative findings to reproduce:
  - The sterling corporate bond market shows a **"jump to illiquidity"**: the
    *speed* of desired sales exceeds purchasing capacity, so prices must fall
    rapidly to clear. A model with a static impact function will miss this —
    it requires a **rate-of-sale vs. absorption-capacity** comparison.
  - Gilt repo tightens because of **bank de-risking and counterparty credit
    concerns**, not only price moves; some NBFIs do not receive the repo
    financing they expect.
  - Re-running the scenario with hedge funds' 2024 repo positions would have
    produced **~£5bn additional gilt sales, more than doubling** the exercise's
    sales and **fully exhausting banks' market-making capacity**.
  - LDI funds were recapitalised by their pension-fund investors and *would*
    have sold gilts if that had failed — an explicit, modellable contingency.
  - Crowding matters: the most-levered gilt hedge funds also had large
    positions in US Treasury and EGB repo, creating cross-market spillovers.

### 2.7 Networks, default cascades and clearing

- **Eisenberg & Noe (2001)** (*Man. Sci.* 47): the clearing-payment vector —
  the standard way to resolve simultaneous defaults consistently.
- **Gai & Kapadia (2010)** (*Proc. R. Soc. A* 466, BoE): contagion in financial
  networks is "robust yet fragile".
- **Battiston et al. (2012)**, **Haldane & May (2011)** (*Nature* 469),
  **Glasserman & Young (2016)** (*JEL*): direct counterparty contagion is
  usually *smaller* than price-mediated contagion — a good reason to prioritise
  fire sales over an interbank exposure network in v1.

### 2.8 ABM practice and validation

- **Borsos, Carro, Glielmo, Hinterschweiger, Kaszowska-Mojsa & Uluc (2025),
  BoE SWP 1122, "Agent-based modeling at central banks"**: current survey of
  central-bank ABM practice, including calibration and validation standards.
- **Bookstaber, Paddrik & Tivnan (2018), "An agent-based model for financial
  vulnerability"** (*JEIC* 13; OFR WP 2014-05): a full agent map of the funding
  chain — cash providers → banks/dealers → hedge funds → asset markets, with
  both **asset-based** and **funding-based** fire sales. **This is the best
  structural template for the agent taxonomy.**
- **Cont (2001)**: the canonical list of return stylised facts (fat tails,
  volatility clustering, no linear autocorrelation, leverage effect,
  aggregational Gaussianity) — the validation checklist.
- **Kirilenko, Kyle, Samadi & Tuzun (2017)** (*JF* 72): the 2010 Flash Crash —
  relevant only if intraday microstructure is in scope (recommended: it is not).

---

## 3. Target Episodes

Choose episodes that isolate different mechanisms, so each adds a distinct
validation constraint. Ordered by suitability for this repo.

| # | Episode | Primary trigger | Dominant amplifier | Why it is a good target |
|---|---------|-----------------|--------------------|-------------------------|
| 1 | **UK gilt / LDI, Sep–Oct 2022** | Fiscal news → 100bp+ yield rise in 4 days | Derivative **variation margin** → forced gilt sales → yields ↑ | UK-specific, extensively documented, BoE published attribution (~50% of the move from LDI selling), clean central-bank intervention counterfactual |
| 2 | **COVID "dash for cash", Mar 2020** | Exogenous real shock | **Fund redemptions** + dealer balance-sheet limits | Tests the redemption channel and reverse-flight-to-liquidity; rich public fund-flow data |
| 3 | **GFC, 2007–09** | Subprime credit losses | **Repo haircuts / run** + mark-to-market + default cascades | Tests every channel; the natural coupling test to the existing real-economy ABM and the housing module |
| 4 | **Archegos, Mar 2021** | Idiosyncratic concentrated position | **Total-return-swap leverage** + dealer margin + block-sale impact | Small, clean test of concentration + synthetic leverage + price impact |
| 5 | **"Volmageddon", Feb 2018** | Volatility spike | Mechanical **rebalancing of inverse-VIX ETPs** | Pure test of volatility-triggered forced flow |
| 6 | **SVB / regional banks, Mar 2023** | Rate rises → held-to-maturity losses | **Depositor run** + unrealised-loss accounting | Tests the MTM vs. amortised-cost distinction |

**Recommendation for v1:** build to reproduce **(1)** and **(2)**, since they
are pure NBFI-leverage/liquidity episodes that the proposed mechanism directly
targets, and both are UK-relevant with public data. Treat (3) as the milestone
for coupling the financial block to the real economy.

---

## 4. Where This Fits in the Existing Codebase

The repo already has (`packages/companies-house-abm/src/companies_house_abm/abm/`):

| Existing | Reusable for the crash model |
|---|---|
| `model.py::Simulation` | Orchestrator, Mesa `Model`, `PeriodRecord`, `DataCollector` — extend, don't replace |
| `markets/housing.py` | **Closest precedent**: a leveraged asset market with bilateral matching, aspiration pricing, LTV/DTI limits, arrears and foreclosure. The crash module is structurally the same object with a faster clock and a continuous price |
| `assets/mortgage.py` | Template for a `Position` / collateralised-loan contract (principal, rate, LTV, arrears) |
| `agents/bank.py` | Already has risk-weighted `capital_ratio`, `meets_capital_requirement`, loan evaluation, default recording — extend for margin lending and dealer inventory |
| `agents/central_bank.py` | Taylor rule; needs a market-maker-of-last-resort / asset-purchase action |
| `config.py` | Frozen dataclass + YAML pattern to follow exactly |
| `calibration/from_data.py`, `firm_profiles.py` | Pattern for data → `ModelConfig` |
| `uk_data` adapters (ONS, BoE, Land Registry, HMRC) | Pattern and home for any new data adapters — **per the layering rule, all new fetching goes in `uk-data`, not in the ABM** |

### 4.1 The critical architectural decision: timescale

The macro model runs on **quarters** (`SimulationConfig.time_step = "quarter"`).
Crashes play out over **days**. A margin spiral resolved once per quarter is not
a margin spiral. (Note the existing model is already inconsistent here — the
housing module's parameters are described in months, e.g. `max_months_listed`,
while the loop is quarterly.)

Three options:

| Option | Description | Verdict |
|---|---|---|
| **A. Nested clock** | Financial block runs `n_subperiods` (e.g. 60 daily) inner steps per macro quarter; only aggregates cross the boundary | **Recommended.** Preserves the existing quarterly macro loop; keeps crash dynamics at the right frequency; testable in isolation |
| B. Convert everything to daily | Uniform clock | Rejected: 400 quarters → 26,000 days of a 1,000-firm real-economy model; invalidates existing calibration |
| C. Financial block only, no coupling | Standalone daily simulation | Good **first milestone**, insufficient as the end state |

**Plan: implement C as Phase 1 (validate against return stylised facts and
crash episodes standalone), then A as Phase 3.**

---

## 5. Proposed Model Design

### 5.1 Agent taxonomy

Following Bookstaber et al. (2018)'s funding chain, adapted to UK institutions:

```
        Cash providers                Intermediaries                Asset owners
  ┌────────────────────────┐   ┌──────────────────────────┐   ┌────────────────────┐
  │ Households (existing)  │   │ Bank / prime broker      │   │ LeveragedInvestor  │
  │ MMFs, corporate cash   │──▶│  - margin lending        │──▶│  - hedge fund      │
  │ Pension schemes        │   │  - repo financing        │   │  - LDI fund        │
  └────────────────────────┘   │  - sets haircuts         │   │  - investment trust│
                               │ Dealer (market maker)    │   └────────────────────┘
                               │  - absorbs order flow    │              │
                               │  - inventory + capital   │◀─────────────┘
                               └──────────────────────────┘        sells into
                                          ▲                          market
                               ┌──────────┴───────────┐
                               │ CentralBank          │
                               │  - LOLR / MMLR / QE  │
                               └──────────────────────┘

  Unlevered / slow capital:  FundamentalInvestor (value buyer, slow capital)
  Liability-side pressure:   OpenEndedFund (redemptions), PensionScheme (margin top-ups)
  Real-economy link:         Firm (existing) — equity issuer, credit demander
```

Concretely, new agent classes:

- **`LeveragedInvestor`** — the requested agent. Holds a portfolio of risky
  assets, funds it with margin loans / repo from banks, targets a leverage
  ratio, faces margin calls, deleverages, and defaults when equity ≤ 0.
  Subtypes by strategy: value/fundamental, trend-following, and
  liability-hedging (LDI).
- **`OpenEndedFund`** — unlevered or lightly levered; forced selling comes from
  **redemptions** rather than margin. Cash buffer, waterfall (cash → liquid →
  illiquid), first-mover-advantage flow rule.
- **`Dealer`** — market maker with finite risk capital and an inventory limit;
  supplies liquidity, sets bid–ask, withdraws when its own constraint binds.
  Extends the existing `Bank`.
- **`FundamentalInvestor` / slow capital** — buys when price < perceived value,
  but with a capital replenishment lag (Duffie 2010).
- **`PensionScheme`** — holds LDI units, can be called on to recapitalise
  (the SWES contingency), otherwise the LDI fund sells gilts.

### 5.2 Assets

A small set (5–20) of `RiskyAsset` objects with:
`price`, `fundamental_value`, `shares_outstanding`, `daily_volume` (ADV),
`realised_volatility` (EWMA), `haircut`, `asset_class`
(`equity | gilt | corporate_bond | cash`). A common factor plus idiosyncratic
noise drives fundamentals, so overlapping portfolios are meaningful.

### 5.3 Balance sheets and identities

Every agent keeps a strict balance sheet; the module must satisfy
stock-flow consistency in the same spirit as the existing design:

```
assets = Σ_a (holdings[a] × price[a]) + cash
liabilities = margin_debt + repo_borrowing + redemption_payable
equity = assets − liabilities
leverage λ = assets / equity
```

with the funding constraint (endogenous, per §5.4):

```
margin_debt ≤ Σ_a (1 − haircut[a]) × holdings[a] × price[a]
```

### 5.4 Mechanisms — core (M1–M8) and extensions (M9–M15)

**Core (minimum viable crash model — implement all eight):**

| ID | Mechanism | Specification | Source |
|----|-----------|---------------|--------|
| **M1** | Leveraged position-taking | Investor targets `λ*`; demand for asset `a` scales with perceived mispricing and available funding | Thurner et al. (2012) |
| **M2** | **Endogenous, procyclical haircuts** | `haircut[a] = clip(k · VaR_α(r_a), h_min, h_max)` with VaR from EWMA volatility. Lender-set, updated each step | Geanakoplos (2010); Brunnermeier & Pedersen (2009); CGFS (2010) |
| **M3** | Margin call and forced deleveraging | If `λ > λ_max` or `margin_debt > collateral value`, investor must sell `q` to restore the constraint, within a maximum liquidation rate per step | Thurner et al. (2012); Cont & Schaanning (2017) |
| **M4** | **Price impact / finite depth** | Square-root law `Δp/p = −Y · σ_daily · sign(q) · √(|q| / ADV)`, split into a permanent component and a transient component that decays with resiliency `ρ` | Tóth et al. (2011); Bouchaud et al. (2009) |
| **M5** | **Liquidity supply with limited capital** | Dealers and fundamental investors absorb flow up to an inventory/capital limit; capital replenishes at rate `κ` per step (slow-moving capital) | Duffie (2010); Baranova et al. (2019); He & Krishnamurthy (2013) |
| **M6** | Mark-to-market revaluation | All positions revalued each step; losses hit equity, which feeds M3 (loss spiral) | Cifuentes et al. (2005) |
| **M7** | **Overlapping portfolios** | ≥5 assets, agents hold heterogeneous but overlapping baskets; sales in one asset mark down others' portfolios | Caccioli et al. (2014); Greenwood et al. (2015) |
| **M8** | Insolvency and resolution | Equity ≤ 0 → default; lender takes collateral and liquidates it into the market (a second wave of selling); lender records the loss against capital | Eisenberg & Noe (2001); Shleifer & Vishny (2011) |

**Extensions (add in the stated priority order):**

| ID | Mechanism | Why it is needed | Target episode |
|----|-----------|------------------|----------------|
| **M9** | **Derivative variation margin** | A pure *cash* drain independent of asset sales — the LDI mechanism. Investor holds a notional swap/futures position; a rate/price move generates a same-day cash call | 2022 LDI |
| **M10** | **Redemption channel** | Open-ended fund outflows `f(past return, liquidity)` with first-mover advantage; sale waterfall (cash → liquid → pro-rata) reproduces "reverse flight to liquidity" | Mar 2020 |
| **M11** | **Funding rollover risk** | Short-maturity repo that the lender may decline to roll (based on counterparty risk, not only price) — the SWES finding that repo tightened on *bank de-risking* | 2008, SWES |
| **M12** | **Heterogeneous expectations** | Fundamentalist/chartist mix with performance-based switching, so booms are endogenous rather than assumed | All — needed for boom-then-crash |
| **M13** | **Central-bank backstop** | LOLR, asset purchases / market-maker of last resort, with an announcement effect. Without this every crash runs to total collapse and no policy question can be asked | 2022 (BoE gilt purchases), 2020 |
| **M14** | **Real-economy coupling** | Credit crunch: bank capital losses → tighter firm lending in the existing `CreditMarket`; household wealth effect → consumption; firm cost of capital → investment | 2008; makes the crash matter for GDP |
| **M15** | **Crowding / concentration metric** | Similarity of portfolios as an explicit state variable, tracked and shockable | SWES cross-market finding |

**Explicitly out of scope for v1:** intraday/order-book microstructure and HFT
(Kirilenko et al. 2017); full bilateral CDS/derivative networks; cross-border
spillovers; internal credit-rating dynamics. Each adds large state without
changing the qualitative dynamics of the target episodes.

### 5.5 Within-period sequence (financial sub-step)

```
 1. Exogenous news        → update fundamental values (common + idiosyncratic factor)
 2. Volatility update     → EWMA realised vol per asset
 3. Lenders set haircuts  → M2 (procyclical, from vol)
 4. Variation margin      → M9 cash calls on derivative positions
 5. Redemptions posted    → M10 fund outflow draws
 6. Solvency/leverage check → who is constrained?  (M3, M6)
 7. Desired orders        → constrained agents' forced sales + unconstrained demand
 8. Liquidity supply      → dealers/value buyers quote absorbable size (M5)
 9. Market clears         → price impact applied (M4); unabsorbed flow → larger move
10. Revalue all portfolios → M6 mark-to-market, M7 spillover to other holders
11. Defaults resolved     → M8 collateral liquidation, lender losses
12. Policy response       → M13 central bank intervention if trigger met
13. Record metrics
```

Steps 6–11 may need **iteration to convergence within a step** (a fire-sale
cascade), as in Cont & Schaanning — with an iteration cap and a convergence
diagnostic recorded.

### 5.6 Configuration surface

Following the existing frozen-dataclass + YAML pattern in `abm/config.py`:

```python
@dataclass(frozen=True)
class RiskyAssetConfig:
    count: int = 8
    classes: tuple[str, ...] = ("equity", "gilt", "corporate_bond")
    fundamental_drift: float = 0.0002       # per day
    fundamental_vol: float = 0.01           # per day
    common_factor_share: float = 0.5

@dataclass(frozen=True)
class InvestorConfig:
    count: int = 200
    target_leverage_mean: float = 3.0       # assets / equity
    target_leverage_std: float = 1.0
    strategy_shares: tuple[float, ...] = (0.5, 0.3, 0.2)  # value / trend / LDI
    portfolio_overlap: float = 0.6

@dataclass(frozen=True)
class MarginConfig:
    haircut_min: float = 0.05
    haircut_max: float = 0.50
    var_confidence: float = 0.99
    var_lookback: int = 60                  # days
    var_multiplier: float = 3.0
    max_liquidation_rate: float = 0.25      # of position per step
    margin_call_grace_periods: int = 1

@dataclass(frozen=True)
class MarketLiquidityConfig:
    impact_model: str = "sqrt"              # "sqrt" | "linear" | "exponential"
    impact_coefficient: float = 0.75        # Y in the square-root law
    resiliency: float = 0.20                # transient impact decay per step
    dealer_count: int = 5
    dealer_inventory_limit_ratio: float = 0.02   # of ADV
    slow_capital_replenishment: float = 0.05

@dataclass(frozen=True)
class RedemptionConfig:
    flow_performance_beta: float = 2.0
    cash_buffer_target: float = 0.05
    first_mover_advantage: float = 0.5      # 0 = pro-rata, 1 = full FMA
```

Add a `FinancialMarketConfig` aggregating these, hung off `ModelConfig`, and a
`financial:` block in `config/model_parameters.yml`.

### 5.7 Proposed file layout

```
abm/
  assets/
    security.py          # RiskyAsset: price, fundamental, ADV, vol, haircut
    position.py          # Position / margin loan contract (mirrors mortgage.py)
  agents/
    investor.py          # LeveragedInvestor (+ strategy mixins)
    fund.py              # OpenEndedFund, PensionScheme
    dealer.py            # Dealer / market maker (extends Bank)
  markets/
    asset_market.py      # Clearing, price impact, cascade iteration
    funding.py           # Margin/repo market: haircuts, rollover
  financial_model.py     # Standalone daily FinancialSimulation (Phase 1)
reporting/
  financial_metrics.py   # Aggregate vulnerability, systemic risk indicators
calibration/
  investor_profiles.py   # Investor balance sheets from data (mirrors firm_profiles.py)
```

---

## 6. Data Sources for Calibration

### 6.1 What we need, and what actually exists

| Need | Ideal data | Realistically available |
|---|---|---|
| Investor balance sheets (assets, debt, equity) | Fund-level assets and borrowings | **Good** — see §6.2 |
| Portfolio holdings (for overlap matrix) | Position-level holdings per investor | **Good for US** (N-PORT, 13F), **poor for UK** — sector-level only |
| Leverage distribution across investors | Gross/net leverage per fund | **Aggregate only** for hedge funds (SEC Private Funds Statistics, FCA/ESMA AIFMD aggregates); **firm-level for UK investment trusts** |
| Margin/haircut levels and their dynamics | Bilateral haircuts by asset and counterparty | **Weak** — CGFS/BIS surveys, OFR bilateral repo pilot, SWES qualitative |
| Market depth / ADV / impact | Daily volume and volatility per asset | **Good and free** |
| Redemption/flow behaviour | Fund-level flows | **Good** — IA (UK), ICI (US), Morningstar |
| Dealer capacity | Dealer inventories | **Good for US** (FR2004), **weak for UK** |

### 6.2 Investor / investment-company balance sheets

**UK**

| Source | Content | Access | Notes |
|---|---|---|---|
| **Companies House Accounts Data Product** (already ingested by this repo) | Full statutory accounts for UK-registered companies, incl. **investment trusts (SIC 64301, ~2,800 active companies)**, VCTs (64303), financial holding companies (64205), fund managers (66300) | Free daily/monthly iXBRL bulk ZIPs + REST API (600 req / 5 min) | **The best fit for this repo.** UK investment trusts are ordinary PLCs that file accounts showing investments at fair value, borrowings and net assets — i.e. a directly observable leveraged-investor balance sheet. **Caveat:** the bulk product covers only electronically filed accounts (~60–75% of filings), and the repo's current 39-column schema (`packages/companies-house/src/companies_house/schema.py`) is built for FRS 102/105 small-company tags. It has **no field for investments held at fair value**, which is the entire asset side of an investment company. Extending the XBRL extractor with IFRS/investment-trust tags is a prerequisite. |
| **FCA National Storage Mechanism (NSM)** | Annual financial reports for all UK regulated-market issuers; **structured ESEF iXBRL** (IFRS group accounts) mandatory since 2021, downloadable as original format, **JSON and CSV** | Free | The right source for **publicly traded** UK companies' balance sheets — cleaner than Companies House for listed issuers |
| **AIC (Association of Investment Companies) monthly statistics** | Per-trust **gearing %**, total assets, NAV, discount, sector — monthly | Free website / research tools | The direct empirical target for the **investor leverage distribution**. Historic gearing through the 2020 and 2022 stress episodes is exactly the calibration target |
| **ONS "Ownership of UK quoted shares"** (2024 edition, published 29 Jan 2026) | Sector shares of the £2.54tn LSE-listed UK equity market: rest of world 58.8%, UK individuals 11.6%, banks 3.6%, public sector 0.2% | Free XLSX | Sets the **relative size of investor types** in the model. Note the RoW share means a UK-only investor population is a poor representation of who actually holds UK equity |
| **ONS UK Economic Accounts / flow-of-funds "from-whom-to-whom" matrices** | Quarterly financial assets and liabilities by institutional sector *and counterparty sector*, by instrument | Free | The backbone for **sector-level balance sheets and the overlap matrix**, where firm-level holdings are unavailable. Note: still labelled experimental for the whom-to-whom detail |
| **ONS Funded occupational pension schemes (FOPS)** | DB/DC assets and asset allocation | Free | Sizes the pension/LDI sector |
| **Bank of England Bankstats (Tables A–D) and the IADB** | MFI balance sheets, lending to NBFIs, repo, sterling money markets, effective rates | Free XLSX; IADB CSV (the repo's `uk_data/adapters/boe.py` already handles this, with a documented 403 fallback) | Bank/dealer side; funding volumes |
| **BoE Financial Stability Report + chart data; SWES final report (Nov 2024)** | NBFI leverage, gilt repo positioning, dealer market-making capacity, "jump to illiquidity" | Free | **Best source of behavioural parameters** — sale speeds, absorption capacity, the £5bn / "fully exhausting market-making capacity" benchmark |
| **BoE SWP 1019, "An anatomy of the 2022 gilt market crisis"** | Sector-level gilt transaction flows during the LDI episode (from MiFID transaction data) | Paper free; underlying data restricted | Published aggregates are enough to calibrate and validate the 2022 replication |
| **FCA / ESMA AIFMD aggregate reporting; ESMA Annual AIF Market Report** | Distribution of AIF leverage (gross and commitment method), asset-class exposures | Free publications | Leverage distribution for hedge-fund-like agents |
| **Investment Association fund statistics** | Monthly UK retail fund flows and FUM by asset class | Free | **Redemption-channel calibration** — the flow-performance relation and March 2020 outflow magnitudes |
| **LSEG / London Stock Exchange monthly market reports** | Turnover, market capitalisation | Free summaries | ADV for the price-impact function |

**International (better holdings data; needed for the overlap matrix and for US episodes)**

| Source | Content | Access |
|---|---|---|
| **SEC Form N-PORT via EDGAR** | **Position-level holdings** of every US registered fund (mutual funds, ETFs, closed-end) since Oct 2019, with derivatives and counterparties, borrowings, flows, and **position-level liquidity classifications** | Free, public quarterly (monthly filed) | The single best public dataset for building a real **overlapping-portfolio matrix** |
| **SEC Form 13F** | Quarterly US equity holdings of institutions >$100m AUM | Free | Long history; the standard input to Greenwood–Landier–Thesmar-style vulnerability calculations |
| **SEC Form N-MFP / N-CEN** | MMF portfolios (monthly), fund-level borrowing and leverage | Free | Cash-provider side |
| **SEC Private Funds Statistics (from Form PF)** | Aggregate hedge-fund gross/net leverage and borrowings by strategy, quarterly | Free (aggregates only) | Leverage distribution priors |
| **FINRA Margin Statistics** | Monthly aggregate customer **margin debt** and free credit balances, **from Jan 1997**, XLSX | Free download from finra.org | **The best single public time series of the leverage cycle.** Directly validates M1–M3: margin debt rises with prices and collapses in crashes |
| **Federal Reserve Z.1 Financial Accounts** | US sector balance sheets, incl. security brokers and dealers | Free | US analogue of the ONS flow of funds |
| **NY Fed primary dealer statistics (FR2004)** | Weekly dealer positions and financing | Free | **Dealer inventory limits** for M5 |
| **SEC Financial Statement Data Sets** | Numeric face-of-financials for **all** XBRL filers, quarterly, flattened CSV with SIC | Free | Free balance sheets for US publicly traded companies |
| **OFR** (hedge fund monitor, bilateral repo pilot, FSRs) | Repo haircuts and NBFI leverage | Free | Rare public source on **haircut levels** |
| **BIS** (CGFS margin/haircut reports; credit-to-GDP gap; DSR; Quarterly Reviews) | Procyclicality of margin; global leverage context | Free | Priors for M2 |
| **ECB Securities Holdings Statistics by Sector (SHSS)** | Holder sector × ISIN, quarterly | Aggregates public; granular restricted | European overlap matrix |
| **Price/volume**: Yahoo Finance / stooq / Alpha Vantage; **BoE yield curves**; Ken French library | Daily prices, returns, volume, factor returns | Free | Volatility, ADV, and the crash-episode return paths to fit against |

### 6.3 Parameter → target → source

| Parameter | Empirical target | Source |
|---|---|---|
| `target_leverage_mean/std` | Investment-trust gearing distribution; AIF leverage distribution; aggregate margin debt / market cap | AIC; ESMA/FCA AIFMD; FINRA |
| `haircut_min/max`, `var_multiplier` | Repo haircut levels and their 2008/2020 widening | CGFS (2010); OFR bilateral repo; Gorton & Metrick (2012) |
| `impact_coefficient` (Y) | `Y ≈ 0.5–1` from the square-root law; corroborated by flow-driven fire-sale impact | Tóth et al. (2011); Coval & Stafford (2007) |
| `resiliency` (ρ) | Price-reversal half-life after fire sales (weeks to months in equities) | Coval & Stafford (2007) |
| `dealer_inventory_limit_ratio` | Dealer inventories as a share of market size; SWES market-making capacity | FR2004; BoE SWES; BoE SWP 803 |
| `flow_performance_beta`, `cash_buffer_target` | Flow–performance elasticity; fund cash buffers vs. March 2020 outflows | IA / ICI; Falato et al. (2021); BIS Bulletin 39 |
| Portfolio overlap | Liquidity-weighted overlap computed from a real holdings matrix | N-PORT / 13F; ONS flow-of-funds matrices |
| Investor-type population shares | Sector shares of UK quoted equity | ONS Ownership of UK Quoted Shares |
| Variation-margin sensitivity | LDI hedge ratios and gilt duration; observed 2022 margin calls | BoE SWP 1019; IMF WP 23/210; TPR guidance |

### 6.4 Data gaps to plan around

1. **No public UK firm-level holdings data.** The overlap matrix cannot be
   built directly for the UK. Mitigations: (a) build it from US N-PORT/13F and
   transfer the *structure*; (b) generate synthetic portfolios matched to ONS
   sector-level flow-of-funds aggregates; (c) treat overlap as a calibrated
   parameter with sensitivity analysis.
2. **Haircuts are essentially unobservable.** Bilateral repo and prime-broker
   haircuts are not public. Calibrate M2 from surveys and from the *implied*
   deleveraging in known episodes, and report sensitivity.
3. **The repo's Companies House schema cannot represent an investment
   company.** Fixing this (IFRS/investment-trust XBRL tags: investments at fair
   value, bank loans and overdrafts, net asset value per share) is a
   prerequisite for the "calibrate from Companies House" story, and is a
   genuinely novel contribution given the repo already owns that pipeline.
4. **Derivative exposure is off-balance-sheet.** Notional swap/futures
   positions — the whole LDI mechanism — do not appear in statutory accounts.
   Use EMIR-derived aggregates published by the BoE/FCA, or calibrate to
   published LDI leverage multiples.
5. **BoE IADB blocks non-browser clients** (already documented in
   `uk_data/adapters/boe.py`, which falls back to hardcoded values). Any new
   BoE series will need the same fallback treatment or a pre-downloaded cache.

---

## 7. Validation Targets

**Tier 1 — return stylised facts (Cont 2001), from the standalone module:**

- Fat-tailed daily returns: tail exponent ≈ 3 (power-law tail, not Gaussian)
- Volatility clustering: slowly decaying autocorrelation of |returns|
- No significant linear autocorrelation of returns
- Leverage effect: negative correlation between returns and future volatility
- Aggregational Gaussianity: tails thin as the horizon lengthens

**Tier 2 — crash-specific stylised facts:**

- Negative skewness; crashes are faster than booms
- Volume spikes on the way down
- Correlations rise in stress (diversification fails when needed)
- Liquidity evaporates non-linearly — the SWES **"jump to illiquidity"**
- Aggregate leverage is procyclical (validate against FINRA margin debt)

**Tier 3 — episode replication:**

- **2022 LDI:** given the observed fiscal shock, the model should attribute
  roughly half the gilt price fall to forced LDI selling, and BoE intervention
  should arrest it — matching BoE SWP 1019 and the Bank Underground attribution
- **March 2020:** redemption-driven selling exceeds redemptions themselves
  (cash-buffer rebuilding), and liquid assets are sold first
- **Counterfactuals:** without procyclical haircuts (M2 off), the crash should
  be materially smaller — an internal check that the amplifier is doing the work

**Tier 4 — coupled model:** the financial crash produces a credit crunch,
falling firm investment, rising bankruptcies and a GDP contraction of a
plausible magnitude in the existing real-economy block.

---

## 8. Implementation Roadmap

| Phase | Deliverable | Mechanisms | Exit criterion |
|---|---|---|---|
| **0. Data spike** | Extend the Companies House XBRL extractor with investment-company tags; profile UK investment-trust balance sheets and gearing; pull AIC, ONS share-ownership, FINRA margin debt | — | An empirical leverage distribution exists for UK investment trusts |
| **1. Core crash engine** (standalone, daily) | `RiskyAsset`, `LeveragedInvestor`, `Dealer`, `asset_market.py`, `funding.py`, `financial_model.py` | M1–M8 | Tier 1 + Tier 2 stylised facts reproduced; M2-off counterfactual shows the amplifier works |
| **2. NBFI mechanisms** | `OpenEndedFund`, `PensionScheme`, variation margin, rollover risk | M9–M11 | 2022 LDI and March 2020 episodes replicated (Tier 3) |
| **3. Endogenous cycle + policy** | Heterogeneous expectations; central-bank backstop | M12, M13 | Endogenous boom–bust without exogenous shocks; intervention counterfactuals run |
| **4. Coupling** | Nested clock; link to `CreditMarket`, `Firm`, `Household` | M14, M15 | GFC-style crash → credit crunch → GDP contraction (Tier 4) |
| **5. Calibration & sweeps** | `calibration/investor_profiles.py`; extend `calibration/sweep.py`; reporting metrics | — | Aggregate-vulnerability and systemic-risk metrics reported per run |

Each phase should follow the repo conventions: frozen dataclass config + YAML,
Mesa `AgentSet` orchestration, `PeriodRecord` extension for new metrics, tests
per `docs/testing.md`, and `make fix` → `make verify` → `make test` before each
commit.

---

## 9. Risks and Limitations

- **Overfitting to episodes.** With this many mechanisms, almost any crash can
  be fitted. Mitigation: fix parameters from data *before* episode replication;
  report out-of-sample episodes; always run the mechanism-off counterfactuals.
- **Unidentifiable parameters.** Haircut dynamics and portfolio overlap are the
  most influential and least observable. Mitigation: sensitivity analysis as a
  first-class output, not an appendix.
- **Timescale coupling is genuinely hard.** A quarterly macro block driven by a
  daily financial block can produce artefacts at the boundary. Mitigation:
  aggregate only stocks and flows across the boundary, and test the coupled
  model against the uncoupled ones.
- **Computational cost.** Cascade iteration inside each of ~250 daily steps per
  simulated year, across Monte Carlo runs and parameter sweeps. The existing
  `packages/rust-abm/` extension is the escape hatch if the Python inner loop
  becomes the bottleneck.
- **The UK holdings-data gap is structural**, not a matter of looking harder.
  The overlap matrix will always be partly synthetic for the UK.

---

## 10. References

**Leverage cycles and ABMs of financial markets**

1. Geanakoplos, J. (2010). "The Leverage Cycle." *NBER Macroeconomics Annual* 24, 1–65.
2. Fostel, A. & Geanakoplos, J. (2014). "Endogenous Collateral Constraints and the Leverage Cycle." *Annual Review of Economics* 6, 771–799.
3. Thurner, S., Farmer, J.D. & Geanakoplos, J. (2012). "Leverage causes fat tails and clustered volatility." *Quantitative Finance* 12(5), 695–707.
4. Aymanns, C. & Farmer, J.D. (2015). "The dynamics of the leverage cycle." *Journal of Economic Dynamics and Control* 50, 155–179.
5. Aymanns, C., Caccioli, F., Farmer, J.D. & Tan, V. (2016). "Taming the Basel leverage cycle." *Journal of Financial Stability* 27, 263–277.
6. Poledna, S., Thurner, S., Farmer, J.D. & Geanakoplos, J. (2014). "Leverage-induced systemic risk under Basel II and other credit risk policies." *Journal of Banking & Finance* 42, 199–212.
7. Adrian, T. & Shin, H.S. (2010). "Liquidity and leverage." *Journal of Financial Intermediation* 19(3), 418–437.
8. Bookstaber, R., Paddrik, M. & Tivnan, B. (2018). "An agent-based model for financial vulnerability." *Journal of Economic Interaction and Coordination* 13, 433–466. (OFR WP 2014-05.)
9. Brock, W.A. & Hommes, C.H. (1998). "Heterogeneous beliefs and routes to chaos in a simple asset pricing model." *JEDC* 22, 1235–1274.
10. Lux, T. & Marchesi, M. (1999). "Scaling and criticality in a stochastic multi-agent model of a financial market." *Nature* 397, 498–500.
11. Borsos, A., Carro, A., Glielmo, A., Hinterschweiger, M., Kaszowska-Mojsa, J. & Uluc, A. (2025). "Agent-based modeling at central banks: recent developments and new challenges." *Bank of England Staff Working Paper* 1122.

**Liquidity spirals and fire sales**

12. Brunnermeier, M.K. & Pedersen, L.H. (2009). "Market Liquidity and Funding Liquidity." *Review of Financial Studies* 22(6), 2201–2238.
13. Shleifer, A. & Vishny, R. (2011). "Fire Sales in Finance and Macroeconomics." *Journal of Economic Perspectives* 25(1), 29–48.
14. Cifuentes, R., Ferrucci, G. & Shin, H.S. (2005). "Liquidity Risk and Contagion." *Journal of the European Economic Association* 3(2–3), 556–566.
15. Caccioli, F., Shrestha, M., Moore, C. & Farmer, J.D. (2014). "Stability analysis of financial contagion due to overlapping portfolios." *Journal of Banking & Finance* 46, 233–245.
16. Greenwood, R., Landier, A. & Thesmar, D. (2015). "Vulnerable banks." *Journal of Financial Economics* 115(3), 471–485.
17. Duarte, F. & Eisenbach, T.M. (2021). "Fire-Sale Spillovers and Systemic Risk." *Journal of Finance* 76(3), 1251–1294.
18. Cont, R. & Schaanning, E. (2017). "Fire sales, indirect contagion and systemic stress testing." *Norges Bank Working Paper* 2/2017.
19. Coval, J. & Stafford, E. (2007). "Asset fire sales (and purchases) in equity markets." *Journal of Financial Economics* 86(2), 479–512.
20. Duffie, D. (2010). "Presidential Address: Asset Price Dynamics with Slow-Moving Capital." *Journal of Finance* 65(4), 1237–1267.
21. He, Z. & Krishnamurthy, A. (2013). "Intermediary asset pricing." *American Economic Review* 103(2), 732–770.

**Market impact**

22. Kyle, A.S. (1985). "Continuous Auctions and Insider Trading." *Econometrica* 53(6), 1315–1335.
23. Tóth, B. et al. (2011). "Anomalous price impact and the critical nature of liquidity in financial markets." *Physical Review X* 1, 021006.
24. Bouchaud, J.-P., Farmer, J.D. & Lillo, F. (2009). "How markets slowly digest changes in supply and demand." *Handbook of Financial Markets*.
25. Cont, R. (2001). "Empirical properties of asset returns: stylized facts and statistical issues." *Quantitative Finance* 1, 223–236.

**Non-bank finance and recent crises**

26. Bank of England (2024). *The Bank of England's system-wide exploratory scenario exercise: final report.*
27. Bank of England (2023). "An anatomy of the 2022 gilt market crisis." *Staff Working Paper* 1019.
28. Bank Underground (2024). "What caused the LDI crisis?"
29. Chen, R. & Kemp, E. (2023). "Putting Out the NBFIRE: Lessons from the UK's Liability-Driven Investment (LDI) Crisis." *IMF Working Paper* 23/210.
30. Baranova, Y., Douglas, G. & Silvestri, L. (2019). "Simulating stress in the UK corporate bond market: investor behaviour and asset fire-sales." *BoE Staff Working Paper* 803.
31. Baranova, Y., Liu, Z. & Shakir, T. (2017). "Dealer intermediation, market liquidity and the impact of regulatory reform." *BoE Staff Working Paper* 665.
32. Braun-Munzinger, K., Liu, Z. & Turrell, A. (2016). "An agent-based model of dynamics in corporate bond trading." *BoE Staff Working Paper* 592.
33. Bank of England (2017). "Simulating stress across the financial system: the resilience of corporate bond markets and the role of investment funds." *Financial Stability Paper* 42.
34. Committee on the Global Financial System (2010). "The role of margin requirements and haircuts in procyclicality." *CGFS Papers* 36, BIS.
35. Falato, A., Goldstein, I. & Hortaçsu, A. (2021). "Financial fragility in the COVID-19 crisis: The case of investment funds in corporate bond markets." *Journal of Monetary Economics* 123, 35–52.
36. Ma, Y., Xiao, K. & Zeng, Y. (2022). "Mutual Fund Liquidity Transformation and Reverse Flight to Liquidity." *Review of Financial Studies* 35(10).
37. Chen, Q., Goldstein, I. & Jiang, W. (2010). "Payoff complementarities and financial fragility: Evidence from mutual fund outflows." *JFE* 97(2), 239–262.
38. Bank for International Settlements (2021). "Open-ended bond funds: systemic risks and policy implications." *BIS Quarterly Review*, December.
39. Gorton, G. & Metrick, A. (2012). "Securitized banking and the run on repo." *Journal of Financial Economics* 104(3), 425–451.
40. Kirilenko, A., Kyle, A.S., Samadi, M. & Tuzun, T. (2017). "The Flash Crash: High-Frequency Trading in an Electronic Market." *Journal of Finance* 72(3), 967–998.

**Networks and default cascades**

41. Eisenberg, L. & Noe, T.H. (2001). "Systemic Risk in Financial Systems." *Management Science* 47(2), 236–249.
42. Gai, P. & Kapadia, S. (2010). "Contagion in financial networks." *Proceedings of the Royal Society A* 466, 2401–2423.
43. Haldane, A.G. & May, R.M. (2011). "Systemic risk in banking ecosystems." *Nature* 469, 351–355.
44. Glasserman, P. & Young, H.P. (2016). "Contagion in Financial Networks." *Journal of Economic Literature* 54(3), 779–831.
45. Minsky, H.P. (1992). "The Financial Instability Hypothesis." *Levy Economics Institute Working Paper* 74.
