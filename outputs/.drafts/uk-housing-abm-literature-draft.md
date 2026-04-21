# Agent-Based Models for Simulating the UK Housing Market: A Literature Review

## 1. Introduction

The UK housing market is characterised by persistent boom-bust cycles, significant regional price heterogeneity, and deep interconnections with the mortgage credit system. Traditional approaches to modelling these dynamics — including dynamic stochastic general equilibrium (DSGE) models, vector autoregressions (VARs), and hedonic regression — rely on representative-agent assumptions and equilibrium conditions that limit their ability to capture the heterogeneous behaviours, feedback loops, and emergent nonlinearities that characterise real housing markets.

Agent-based models (ABMs) offer a fundamentally different approach: they simulate individual households, banks, investors, and other actors making decisions according to heterogeneous behavioural rules, and observe aggregate dynamics — such as house prices, transaction volumes, and default rates — as emergent outcomes of these micro-level interactions. Since Farmer & Foley's influential call in *Nature* that "the economy needs agent-based modelling," the methodology has gained traction in central banks and academia for studying housing markets specifically.

This review surveys the literature on agent-based models applied to the UK housing market, covering the period 2009–2026. It identifies the major model lineages, analyses their agent types and market mechanisms, examines calibration and validation approaches, surveys the policy experiments conducted, and situates UK-specific work within the broader international housing ABM literature. The review concludes with an assessment of consensus findings, acknowledged limitations, and open research gaps.

---

## 2. Taxonomy of UK Housing ABMs

The UK housing ABM literature can be organised into three distinct lineages, plus several standalone contributions:

### 2.1 The Surrey/PwC Model (Gilbert et al., 2009)

The earliest UK-specific housing ABM was developed by Nigel Gilbert, John Hawksworth, and Paul Swinney at the University of Surrey's Centre for Research in Social Simulation (CRESS), in collaboration with PricewaterhouseCoopers. Published at the AAAI Spring Symposium on Technosocial Predictive Analytics, this model:

- **Platform**: NetLogo
- **Agents**: Households (buyers/sellers) and realtors (estate agents)
- **Space**: Abstract grid; houses differentiated only by a neighbourhood price index
- **Market mechanism**: Posted-price with realtor valuations based on local recent sales; sellers reduce prices over time if unsold
- **Behavioural rules**: Households move when forced (job relocation, death) or when mortgage costs become unaffordable or income rises enough to trade up
- **Key findings**: Reproduced stylised facts including price sensitivity to interest rates, the role of first-time buyers in maintaining demand, asymmetric supply responses (slow to expand, fast to contract), and sticky-downward price dynamics
- **Limitations**: No explicit mortgage market, no buy-to-let investors, no spatial structure beyond neighbourhood index, not calibrated to specific UK data

This model established the template for subsequent UK work and remains actively extended: Gamal, Pinto & Iossifova (2024) built directly on it.

### 2.2 The BoE/INET-Oxford Model Lineage (Baptista → Carro → Bardoscia)

The most influential UK housing ABM programme emerged from the collaboration between the Bank of England and the Institute for New Economic Thinking (INET) at Oxford, producing three major papers over eight years:

**Baptista et al. (2016), BoE Staff Working Paper No. 619:**
- **Platform**: Java (custom framework)
- **Agents**: First-time buyers, homeowners, buy-to-let (BTL) investors, renters, a bank agent, a central bank agent
- **Market mechanism**: Double auction for owner-occupier transactions and rental matching
- **Calibration data**: Zoopla listing data, FCA loan-level regulatory data (PSD), English Housing Survey, ONS data
- **Policy experiments**: Hard LTV limit, soft LTI limit (allowing limited share of unconstrained new mortgages)
- **Key findings**: LTV/LTI policies mitigate house price cycles by reducing leverage; policies targeting owner-occupiers spill over to the rental market as BTL investors fill the gap, affecting rental supply/demand
- **Open source**: `INET-Complexity/housing-model` on GitHub (MIT licence, 47 stars)

**Carro et al. (2022), BoE Staff Working Paper No. 976 / Industrial and Corporate Change (2023):**
- Extended Baptista model with enhanced household heterogeneity and age-dependent behaviour
- Assessed macroprudential policy effects at the *individual household* level, not just aggregate
- Demonstrated that targeting one risk measure (e.g., LTV) affects other risk metrics, necessitating careful multi-dimensional calibration
- Confirmed the compositional shift: LTV caps reduce owner-occupier market share, increasing BTL investor presence
- **Open source**: `adrian-carro/spatial-housing-model` on GitHub (MIT licence, 13 stars)

**Bardoscia, Carro et al. (2024), BoE Staff Working Paper No. 1,066:**
- Integrated the housing ABM into a full **macroeconomic** agent-based model with production firms, a consumption goods market, and a labour market
- Added **bank capital requirements** as a policy instrument alongside borrower-based tools
- Three experiments: (i) higher capital requirements → sharp decline in mortgage and commercial lending, housing transactions; (ii) LTI cap → house prices fall relative to income, homeownership decreases; (iii) combined → positive GDP and employment effects, no material inflation impact
- Represents the **current state of the art** for UK housing ABMs

### 2.3 The Ge Spatial Housing Model (2013–2017)

Jiaqi Ge developed a spatial housing ABM using the MASON platform:

- **Ge (2013/2014)**: Argued that lenient lending policy is responsible for housing price bubbles, using a spatial model with a grid-based housing market
- **Ge (2017)**: Published in *Computers, Environment and Urban Systems*, modelling endogenous rise and collapse of housing prices, with agents on a spatial lattice
- These models emphasise the spatial dimension of housing markets but have been less widely adopted than the BoE/INET lineage

### 2.4 The Gamal/Gilbert Extension (2024)

The most recent UK housing ABM, published in JASSS (Journal of Artificial Societies and Social Simulation) volume 27:

- **Gamal, Pinto & Iossifova (2024)**: "A Behavioural Agent-Based Model for Housing Markets: Impact of Financial Shocks in the UK"
- **Platform**: NetLogo (with Python version available)
- **Extends**: Gilbert et al. (2009)
- **Key additions**: (1) explicit rental and BTL housing markets; (2) tenant and investor agents; (3) agents can transition between tenant, homebuyer, and investor over their lifetime; (4) fixed-rate mortgage periods with reversion to variable rates
- **Experiments**: Sudden interest rate shocks and LTV shocks, inspired by the 2022 UK rate rises
- **Key findings**: Interest rate rise → house price decrease + rent increase (with lag); interest rate fall → price increase + rent decrease; LTV decline → steep price decrease + rent increase; asymmetric responses between rise and fall scenarios
- **Open source**: GitHub and CoMSES repository

### 2.5 Other UK-Related Contributions

- **Tarne, Bezemer & Theobald (2022)**: Published in JEDC, extended the Baptista model to study borrower-specific LTV policies and their effects on wealth inequality and consumption volatility. Found that LTV caps significantly increase wealth inequality.
- **SpringerLink (2025)**: "An Agent-Based Model for Housing Markets: Impact of a Financial Shock on Wealth in the UK" — investigates the 2022 interest rate shock effects on household wealth.

---

## 3. Agent Types and Behavioural Rules

Across the UK housing ABM literature, a common set of agent types has emerged, though with varying levels of sophistication:

### 3.1 Household Agent Types

| Agent Type | Present In | Key Behaviours |
|------------|-----------|----------------|
| **First-time buyers** | Baptista (2016), Carro (2022), Bardoscia (2024) | Enter housing market when income/savings sufficient; constrained by LTV/LTI |
| **Homeowners** | All models | Trade up/down based on income changes; default when unable to meet payments |
| **BTL investors** | Baptista (2016), Carro (2022), Gamal (2024) | Purchase properties to rent; respond to yield changes; interest-only mortgages |
| **Renters/tenants** | Baptista (2016), Carro (2022), Gamal (2024) | Rent when unable to buy; may transition to buyers when capital accumulates |
| **Generic households** | Gilbert (2009), Ge (2013/2017) | Combined buyer/seller without tenure-type differentiation |

### 3.2 Non-Household Agents

| Agent Type | Present In | Role |
|------------|-----------|------|
| **Bank** | Baptista (2016), Carro (2022), Bardoscia (2024) | Mortgage origination with LTV/LTI checks, interest rate setting |
| **Central bank** | Baptista (2016), Bardoscia (2024) | Sets base rate, macroprudential parameters |
| **Realtors** | Gilbert (2009), Gamal (2024) | Value properties based on local sales history; mediate transactions |
| **Production firms** | Bardoscia (2024) | Employ households, produce consumption goods (macro extension) |

### 3.3 Behavioural Rules

A key dimension along which models differ is how agents form expectations and make decisions:

- **Bounded rationality**: All UK housing ABMs use heuristic decision rules rather than full optimisation. Households decide based on affordability thresholds, income-to-payment ratios, and simple comparisons — not utility maximisation.
- **Adaptive expectations**: Prices are typically based on recent local sales (Gilbert, Gamal) or market clearing in auctions (Baptista, Carro). No model uses rational expectations.
- **Heterogeneity sources**: Income (drawn from calibrated distributions), wealth accumulation, age/lifecycle (Carro 2022), risk preferences (Gamal 2024 "willingness to pay"), tenure type.
- **Transition rules**: Gamal (2024) allows agents to transition between tenure types (renter → buyer → investor) based on financial thresholds — the "relatively rich" and "relatively poor" classification is particularly detailed.

---

## 4. Market Mechanisms and Price Formation

### 4.1 Double Auction (Baptista/Carro/Bardoscia)

The BoE/INET models use a double auction mechanism where:
- Sellers list properties with asking prices
- Buyers submit bids based on affordability
- Matching occurs with priority rules (e.g., highest bid)
- Both sides of the market are active simultaneously

This produces competitive price discovery and is the most economically sophisticated mechanism in the UK literature.

### 4.2 Posted-Price with Realtor Valuation (Gilbert/Gamal)

Gilbert (2009) and Gamal (2024) use a posted-price mechanism:
- Realtors value houses based on local recent transaction prices
- Sellers list at the realtor's valuation
- Unsold houses experience price decay over time
- Buyers select from available listings within their budget

This captures the information asymmetry and search frictions of real housing markets more naturally than auctions.

### 4.3 Brochure Concept (JASSS Korean ABM)

While not UK-specific, the brochure concept from the Korean housing ABM (Ozel et al., JASSS 2020) is noteworthy: buyers receive only a limited subset of available listings, modelling information asymmetry explicitly. This has not yet been adopted in UK models.

### 4.4 Price Formation Summary

| Model | Mechanism | Price Discovery | Information |
|-------|-----------|----------------|-------------|
| Baptista/Carro | Double auction | Competitive bidding | Full market information |
| Gilbert/Gamal | Posted-price + decay | Realtor valuation | Local only |
| Ge (2017) | Spatial matching | Neighbourhood-based | Spatial proximity |

---

## 5. Calibration and Validation Methods

### 5.1 Data Sources Used for UK Models

| Data Source | Used By | Purpose |
|-------------|---------|---------|
| **Zoopla/Rightmove listings** | Baptista (2016), Carro (2022) | Asking prices, time on market |
| **FCA PSD (loan-level)** | Baptista (2016), Carro (2022) | LTV distributions, mortgage volumes, income multiples |
| **English Housing Survey** | Baptista (2016), Carro (2022) | Tenure distribution, household characteristics |
| **ONS earnings data** | Gamal (2024) | Income distribution (gamma distribution) |
| **BoE interest rate data** | Gamal (2024) | Base rate, mortgage rates |
| **DLUHC housing statistics** | Gamal (2024) | Construction rates, dwelling stock |
| **Korean census** | JASSS (2020) | Income, housing supply (non-UK) |

### 5.2 Calibration Approaches

The UK housing ABM literature uses relatively simple calibration methods compared to the state of the art in the broader ABM calibration literature:

- **Manual/expert calibration**: Gilbert (2009) and Gamal (2024) calibrate parameters by matching output patterns to stylised facts (pattern-oriented modelling approach)
- **Full-factorial design of experiments**: The JASSS Korean ABM (2020) uses factorial experiments to calibrate behavioural parameters, then validates against historical house price index and transaction volume data
- **Moment matching**: Baptista (2016) and Carro (2022) match a selection of summary statistics (price distributions, LTV distributions, homeownership rates, transaction volumes) but do not report formal simulated minimum distance or Bayesian estimation

More rigorous calibration methods exist in the broader literature — including Approximate Bayesian Computation, surrogate-assisted calibration with ML (Lamperti et al., 2018), and neural posterior estimation (Monti & Pangallo et al., 2022) — but these have not yet been applied to UK housing ABMs.

### 5.3 Validation

- **Stylised fact reproduction**: All UK models claim to reproduce some stylised facts (price sensitivity to interest rates, sticky-downward prices, boom-bust cycles)
- **Pattern-oriented validation**: Gamal (2024) systematically tests whether model output patterns match expected trends under different parameter regimes
- **Out-of-sample testing**: No UK housing ABM has published formal out-of-sample forecasting results (e.g., hindcasting the 2008 GFC or 2022 rate rise)
- **Sensitivity analysis**: Gamal (2024) provides one-parameter-at-a-time sensitivity analysis; Carro (2022) discusses sensitivity but without formal Sobol indices

### 5.4 Methodological Gap

The calibration and validation of UK housing ABMs falls short of what the broader methodology literature recommends. Windrum, Fagiolo & Moneta (2007) and Platt (2019) identify best practices including formal statistical calibration, uncertainty quantification, and out-of-sample validation — none of which are fully implemented in published UK models. This is the most significant methodological limitation of the field.

---

## 6. Policy Experiments and Findings

### 6.1 Macroprudential Policy (LTV/LTI Limits)

This is the dominant focus of UK housing ABM research:

| Paper | Experiment | Key Finding |
|-------|-----------|-------------|
| Baptista (2016) | Hard LTV limit | Mitigates house price cycle; reduces leverage; spills over to rental market |
| Baptista (2016) | Soft LTI limit (15% flow) | Moderates credit growth; compositional shift toward BTL |
| Carro (2022) | LTV/LTI comparative statics | Targeting one risk measure affects others; heterogeneous household impacts |
| Tarne et al. (2022) | Borrower-specific LTV | LTV caps significantly increase wealth inequality |
| Gamal (2024) | LTV decline shock | Steep price decrease (-86%); rent increase; severe population loss |
| Gamal (2024) | LTV rise shock | Sharp price increase; short-term rent increase then decline |

**Consensus**: LTV/LTI tightening reduces house prices and credit but creates unintended distributional consequences — particularly increased BTL market share and rent increases.

### 6.2 Bank Capital Requirements

| Paper | Experiment | Key Finding |
|-------|-----------|-------------|
| Bardoscia (2024) | Increased total capital requirements | Sharp decrease in commercial and mortgage lending; housing transactions fall |
| Bardoscia (2024) | Combined capital + LTI | Positive GDP and employment effects; no material inflation impact |

### 6.3 Interest Rate Shocks

| Paper | Experiment | Key Finding |
|-------|-----------|-------------|
| Gilbert (2009) | Interest rate increase +3% | Immediate 43% house price decrease |
| Gamal (2024) | Interest rate rise (3.7% → 8%) | 44% price decrease over 10 years; rent increase with 3-year lag |
| Gamal (2024) | Interest rate decline (8% → 3.7%) | 62% price increase; rents relatively unaffected |
| Geanakoplos et al. (2012) | Constant interest rates (US) | Higher rates alone would not have prevented the bubble |

**Consensus**: Interest rate rises decrease house prices but with asymmetric effects — rises cause sharper disruption than equivalent declines because they trigger forced sales.

### 6.4 Notable Gap

No UK housing ABM has modelled: **Help to Buy schemes**, **stamp duty changes**, **planning policy/housing supply constraints**, **immigration/population growth effects**, or **Section 21 reform / rental regulation**. These are significant policy-relevant omissions.

---

## 7. Relation to International Housing ABM Literature

### 7.1 The Washington DC Model (Geanakoplos, Axtell, Farmer et al.)

The most ambitious housing ABM to date, operating at 1:1 scale (~2 million agents) using IRS household data, mortgage servicer data, and MLS transaction data for the DC metro area. It reproduced the observed housing bubble shape, inventory levels, and listing-to-sale price ratios. Policy experiments showed maintaining credit standards (LTV) would have prevented the bubble more effectively than higher interest rates. Published in the American Economic Review (2012) with a full technical paper on SSRN (2024).

This model is architecturally more complex than any UK model and demonstrates the feasibility of large-scale, data-rich housing ABMs.

### 7.2 European Central Bank Models

Laliotis et al. (2019/2020, ECB Working Paper 2294) developed an ABM for assessing LTV caps across multiple European countries, finding heterogeneous effects depending on country-specific housing market characteristics. This highlights the importance of UK-specific calibration.

### 7.3 Other National Models

- **Hungary**: Mérő et al. (2023) — 1:1 scale model of all 4 million Hungarian households; tests construction cost shocks and family fiscal policies (JEDC)
- **Denmark**: Cokayne (2019) — Danmarks Nationalbank WP 138; finds stricter fiscal policies reduce price fluctuations
- **Iceland**: Erlingsson et al. (2014) — housing bubble ABM within a credit network economy
- **Netherlands**: Bezemer et al. — "Roof or real estate?" examines housing affordability with heterogeneous agents
- **South Korea**: JASSS (2020) — brochure-concept market mechanism; LTV/DTI experiments

### 7.4 Comparative Assessment

The UK housing ABM literature is among the most developed internationally, alongside the US (Geanakoplos/Axtell/Farmer) and Hungarian (Mérő) programmes. The UK's distinguishing features are:
- Strong institutional support from the Bank of England
- Open-source code availability (unique among central bank housing ABMs)
- Focus on macroprudential policy evaluation
- Multiple independent model lineages (Surrey, BoE/INET, Ge)

However, the UK literature lags behind the US DC model in **scale** (no 1:1 UK model exists), behind Hungary in **data resolution** (no 1:1 household matching), and behind the broader ABM methodology literature in **formal calibration and validation rigour**.

---

## 8. Limitations and Open Questions

### 8.1 Acknowledged Limitations (from the literature)

1. **No endogenous housing supply**: No UK model includes developers responding to price signals or planning constraints. Housing stock is either fixed or grows at an exogenous rate.
2. **Limited spatial structure**: The BoE/INET models are non-spatial or coarsely spatial. Ge (2017) uses a grid but without real geography. No model operates at Local Authority level with real spatial data.
3. **Simplified default mechanics**: No UK model fully implements the "double trigger" default mechanism (negative equity + income shock) identified by BoE Staff Working Paper 812.
4. **No fire-sale feedback**: While the theoretical importance of the default → forced sale → price decline → more defaults amplification loop is widely cited, no UK ABM has explicitly modelled this mechanism.
5. **Homogeneous BTL investors**: Current models treat BTL investors as a single class, despite significant heterogeneity between amateur landlords and professional portfolio investors.
6. **No government policy interventions**: Help to Buy, stamp duty holidays, Right to Buy, and other UK-specific policies are absent from all published models.
7. **Calibration limitations**: No UK model uses formal statistical calibration (MSM, ABC, indirect inference) or reports out-of-sample validation.
8. **Fixed interest rate period modelling**: Only Gamal (2024) explicitly models the UK-specific feature of fixed-rate mortgage periods with reversion to variable rates — a critical feature for understanding interest rate shock transmission.

### 8.2 Open Research Questions

1. **Can a UK housing ABM be calibrated to reproduce known historical episodes** (2008 GFC, 2013–2015 recovery, COVID stamp duty holiday, 2022 rate rises) out of sample?
2. **What spatial resolution is needed** for a UK housing ABM to capture regional divergence in prices without becoming computationally intractable?
3. **How does endogenous housing supply** (developer agents responding to planning permissions and price signals) affect the dynamics of boom-bust cycles?
4. **Can formal Bayesian calibration** (ABC or neural posterior estimation) improve the credibility and uncertainty quantification of UK housing ABMs?
5. **What is the role of expectations heterogeneity** (extrapolative vs. mean-reverting vs. fundamental-based) in generating realistic price dynamics?
6. **How do rental market regulations** (Section 21 reform, rent controls) interact with owner-occupier market dynamics in an ABM framework?

---

## 9. Conclusion

The literature on agent-based models for simulating the UK housing market has developed substantially since Gilbert et al.'s (2009) pioneering work. The field is dominated by the BoE/INET-Oxford lineage (Baptista 2016 → Carro 2022 → Bardoscia 2024), which has produced the most sophisticated, best-calibrated, and most policy-relevant models. A parallel line of work extending Gilbert's model (Gamal et al. 2024) has added valuable analysis of interest rate shock transmission through the BTL and rental markets.

**Points of consensus:**
- LTV/LTI tightening effectively reduces house prices and credit growth
- Macroprudential policies create unintended spillovers (particularly to the rental market via BTL compositional shifts)
- Interest rate changes have asymmetric effects on prices (rises cause sharper disruption than falls)
- Agent heterogeneity is essential — aggregate/representative-agent models miss distributional impacts

**Key disagreements/uncertainties:**
- The appropriate market clearing mechanism (double auction vs. posted-price) remains debated
- Whether stylised-fact reproduction constitutes adequate validation is contested
- The importance of spatial structure is theoretically recognised but empirically untested for UK models

**Critical gaps for future work:**
- Formal calibration and out-of-sample validation
- Endogenous housing supply
- Government policy interventions (Help to Buy, stamp duty, planning)
- Spatial structure at the Local Authority level
- Full implementation of the double-trigger default mechanism with fire-sale feedback

The intellectual foundations are strong and publicly available, with open-source code for both major model lineages. The field is well-positioned for the next generation of models that combine the behavioural richness of ABMs with the calibration rigour of modern simulation-based inference.
