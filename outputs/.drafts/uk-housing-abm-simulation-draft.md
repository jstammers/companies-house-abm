# Agent-Based Modelling of the UK Housing Market: A Proposal for a Commercial Scenario-Planning Platform

## Executive Summary

Agent-based models (ABMs) offer a uniquely powerful approach to simulating UK housing market dynamics because they capture the heterogeneity, feedback loops, and nonlinear amplification mechanisms that traditional econometric and DSGE models structurally miss. A decade of Bank of England-funded research — from Baptista et al. (2016) through Carro et al. (2022) to Bardoscia et al. (2024) — has produced increasingly sophisticated, open-source, UK-calibrated housing ABMs that model households, banks, and policy interventions at the individual level. In parallel, the Washington DC housing bubble model by Geanakoplos, Axtell, and Farmer demonstrated that ABMs can reproduce observed boom-bust dynamics with remarkable fidelity at 1:1 population scale.

This report synthesises the academic and regulatory landscape, identifies the gap between existing commercial tools (which are predominantly top-down econometric) and the bottom-up capabilities ABMs provide, and proposes a concrete architecture for a commercially viable ABM-based scenario-planning platform targeting mortgage lenders, housing planners, investors, and central banks. The platform would combine the proven BoE/INET housing ABM architecture with modern calibration techniques, UK public data pipelines, and a cloud-deployed scenario API.

---

## 1. The State of Housing ABMs: Academic Foundations

### 1.1 The BoE/INET Model Lineage

The most developed UK housing ABM lineage emerged from the collaboration between the Institute for New Economic Thinking (INET) at Oxford and the Bank of England:

**Baptista et al. (2016), BoE Staff Working Paper No. 619:**
- Developed the foundational agent-based model of the UK housing market
- Agent types: first-time buyers, owner-occupiers, buy-to-let (BTL) investors, renters
- Market mechanism: double auction for housing transactions
- Includes a bank agent implementing LTV and LTI constraints
- Calibrated using a large selection of UK microdata including real estate listing data and loan-level regulatory data
- Used to study macroprudential policy (hard LTV limits, soft LTI limits)
- Key finding: LTV/LTI policies mitigate house price cycles but create spillovers to the rental market as BTL investors compensate for reduced owner-occupier demand

**Carro et al. (2022), BoE Staff Working Paper No. 976:**
- Extended the Baptista model with enhanced heterogeneity
- Assessed macroprudential policy effects at the individual household level, not just aggregate
- Demonstrated that policies targeting specific risk measures (e.g., LTV) affect other risk metrics, requiring careful calibration
- Confirmed compositional shift: LTV caps reduce owner-occupier purchases, increasing BTL investor market share, affecting rental supply and demand
- Calibrated using Zoopla listing data and FCA loan-level regulatory data

**Bardoscia, Carro et al. (2024), BoE Staff Working Paper No. 1,066:**
- Integrated the housing ABM into a full macroeconomic agent-based model
- Added bank capital requirements alongside borrower-based tools (LTI caps)
- Three experiments: (i) increased capital requirements → sharp decrease in mortgage and commercial lending; (ii) LTI cap → house prices fall sharply relative to income, homeownership decreases; (iii) combined → housing transactions and prices drop, positive GDP and unemployment effects, no material inflation impact
- This represents the current state of the art for UK housing ABMs

All three models are **open source** under MIT licence:
- `INET-Complexity/housing-model` (47 stars, Java): the original Baptista model
- `adrian-carro/spatial-housing-model` (13 stars, Java): Carro's spatial extension

### 1.2 The Washington DC Model (Geanakoplos, Axtell, Farmer et al.)

The INET-funded Washington DC housing bubble model is the most ambitious housing ABM to date:
- Operates at **1:1 scale** with ~2 million household agents
- Uses IRS household data, mortgage servicer data, and Multiple Listing Service (MLS) transaction data
- Agents make individual decisions about: home purchase, down payment, refinancing, renting vs buying, investment/flipping
- Reproduces the observed bubble shape, inventory levels, listing-to-sale price ratios, and days-on-market
- Policy experiments showed: interest rate changes alone would not have prevented the bubble; maintaining LTV standards would have largely prevented it; combined policy most effective
- Published in the American Economic Review (Geanakoplos et al. 2012) and as a full SSRN working paper (Axtell et al. 2024)

This model demonstrates the feasibility of large-scale, data-rich housing ABMs for policy analysis.

### 1.3 Other Notable Housing ABMs

| Model | Geography | Key Feature |
|-------|-----------|-------------|
| Gilbert, Hawksworth & Swinney (2009) | UK | Early spatial housing ABM (50×50 grid), reproduced sticky-downward prices |
| Ge (2013) | UK | Spatial model arguing lenient lending causes price bubbles |
| Laliotis et al. (2019), ECB WP 2294 | European countries | Multi-country LTV caps assessment, calibrated per country |
| JASSS (2020) Korean housing ABM | South Korea | Brochure-concept market mechanism (information asymmetry), LTV/DTI experiments |

---

## 2. Mortgage and Default Modelling

### 2.1 Mortgage Origination in ABMs

The BoE models implement mortgage origination through a bank agent that:
- Applies LTV limits (hard cap or soft cap with exceptions)
- Applies LTI/DTI limits (ratio of total debt service to income)
- Sets interest rates as a spread over a base rate
- Distinguishes between owner-occupier and BTL mortgages
- Models fixed-rate periods (typically 2-5 years in the UK) with reversion to variable rates

The Bardoscia et al. (2024) model adds bank-side constraints: capital requirements affect the bank's willingness and capacity to lend, creating a credit supply channel independent of borrower constraints.

### 2.2 Default Mechanisms

The academic consensus on mortgage default, as confirmed by BoE Staff Working Paper No. 812 ("Three Triggers?", 2019), identifies the **double trigger hypothesis**: default requires both negative equity *and* an income/affordability shock. A third factor — institutional environment (recourse laws, forbearance norms) — modulates the relationship. This is directly relevant to ABM design:

- **Negative equity**: when house price falls leave the outstanding mortgage exceeding the property value
- **Income shock**: unemployment, income reduction, or interest rate rise making payments unaffordable
- **Institutional factors**: UK mortgages are full-recourse (unlike many US states), which suppresses strategic default; lender forbearance practices (payment holidays, term extensions) delay repossession

ABMs can model these triggers at the individual household level, capturing the heterogeneous distribution of LTV ratios, debt-service ratios, and employment vulnerability across the population — something aggregate models fundamentally cannot do.

### 2.3 Feedback Loops: Defaults → Fire Sales → Price Falls

A critical advantage of ABMs is their ability to model the **fire-sale feedback loop**:
1. Adverse shock → some households default
2. Repossessions increase housing supply (forced sales at discount)
3. Increased supply and distressed pricing depresses local house prices
4. Falling prices push more households into negative equity
5. More defaults → return to step 2

This amplification mechanism was central to the 2008 crisis and is explicitly captured in the Geanakoplos leverage cycle framework. Traditional models estimate reduced-form relationships; ABMs generate this dynamic endogenously.

### 2.4 External Shock Transmission Channels

The following transmission channels should be modelled:

| Channel | Mechanism | Evidence |
|---------|-----------|----------|
| **Interest rates** | Base rate → mortgage rate → affordability → demand → prices | Baptista (2016), Geanakoplos (2012) |
| **Unemployment** | Job loss → income shock → default + demand reduction | BoE WP 812 double trigger |
| **Credit conditions** | LTV/LTI limits → credit availability → purchasing power → prices | Carro (2022), Bardoscia (2024) |
| **Bank capital** | Capital requirements → lending capacity → credit supply | Bardoscia (2024) |
| **Population/migration** | Household formation → demand pressure | Not yet in BoE ABMs |
| **Housing supply** | Planning permissions → new builds → supply | Not yet in BoE ABMs |
| **Government policy** | Stamp duty, Help to Buy, Right to Buy → demand shifts | Not yet in BoE ABMs |
| **Inflation** | Real income erosion, construction costs → affordability | Partially in Bardoscia (2024) |

Notable gaps in existing models: **housing supply/planning constraints**, **government subsidies** (Help to Buy, stamp duty holidays), and **demographic/migration drivers** are not modelled in the published BoE ABMs. These represent key areas for commercial model development.

---

## 3. UK Housing Data Landscape

### 3.1 Open/Public Data Sources

| Source | Content | Granularity | Access |
|--------|---------|-------------|--------|
| **HM Land Registry Price Paid Data** | All property sales in England & Wales | Individual transactions (address, price, date, type) | Open Government Licence, monthly updates |
| **ONS UK House Price Index** | Mix-adjusted house price index | Monthly, 441+ areas (LA/region) | Open, hedonic regression methodology |
| **BoE Mortgage Lending Statistics** | Aggregate mortgage flows, rates, LTV distributions | Monthly/quarterly, national | Open |
| **English Housing Survey** | Household characteristics, tenure, housing conditions | Annual, ~13,000 households | Open (published tables), restricted microdata |
| **HMRC Stamp Duty Statistics** | Transaction volumes by price band | Quarterly, national/regional | Open |
| **ONS Labour Market Data** | Employment, unemployment, earnings | Monthly, regional | Open |
| **ONS Population Estimates** | Population by age, area | Annual, LA level | Open |

### 3.2 Restricted/Commercial Data

| Source | Content | Access |
|--------|---------|--------|
| **FCA Product Sales Data (PSD001/PSD007)** | Loan-level mortgage origination data (amount, LTV, income, rate type, product type) | FCA regulated firms only; aggregate statistics published |
| **Zoopla/Rightmove** | Asking prices, listings, time on market | Commercial licence |
| **Credit Reference Agency data** | Individual credit histories, arrears | Commercial licence |
| **MLS/estate agent data** | Viewing data, offers, chain information | Commercial/partnership |

The BoE models use both open data and regulatory data (FCA PSD). A commercial product would need to work primarily with open data, supplemented by commercial data partnerships.

### 3.3 ONS HPI Methodology

The UK HPI uses a **hedonic regression** approach: property characteristics (type, size, age, location) are controlled for, so the index measures "like-for-like" price changes rather than being affected by compositional shifts in what is being sold. The index is produced jointly by HM Land Registry, ONS, and Land and Property Services Northern Ireland. An ABM that generates synthetic transactions can compute a comparable mix-adjusted index for validation.

---

## 4. Existing Commercial Tools and the ABM Gap

### 4.1 Current Commercial Landscape

**Oxford Economics Real Estate Service:**
- Macro-model-driven forecasts powered by their Global Economic Model
- Scenario analysis capabilities (narrative scenarios)
- Covers 200+ countries, detailed city-level data
- Econometric (top-down), not agent-based
- Limitations: cannot model distributional effects, heterogeneous responses, or emergent fire-sale dynamics

**Moody's Analytics (HPA/ResiLandscape):**
- House Price Appreciation forecasts
- Mortgage portfolio stress testing tools
- Used extensively by US banks for CCAR/DFAST stress testing
- Statistical/econometric approach
- UK coverage exists but less granular than US

**Simudyne:**
- Commercial ABM platform for financial services
- Includes a financial toolkit with balance sheet and lending model modules
- Cloud-deployable, enterprise-grade
- Not housing-specific; provides a general ABM development framework
- Could serve as infrastructure for a housing ABM product

**Nationwide/Halifax House Price Indices:**
- Based on their own mortgage approval data
- Useful benchmarks but not scenario-planning tools

### 4.2 The ABM Competitive Advantage

Existing tools are fundamentally **top-down econometric models** that:
- Assume representative agents (no household heterogeneity)
- Cannot model distributional effects of policy changes
- Cannot capture emergent nonlinear dynamics (fire sales, contagion)
- Cannot assess who is affected by policy changes (FTBs vs BTL vs high-LTV borrowers)
- Cannot model the interaction between mortgage market segments

An ABM-based product would uniquely offer:
1. **Distributional impact analysis**: which household segments gain/lose from a policy change
2. **Nonlinear stress testing**: fire-sale dynamics, contagion, tipping points
3. **Policy experiment specificity**: model exact LTV limit changes, stamp duty rates, HTB schemes
4. **Micro-to-macro consistency**: aggregate outcomes emerge from individual decisions
5. **Scenario richness**: combine multiple simultaneous shocks with heterogeneous exposure

---

## 5. Regulatory Demand for Scenario Planning

### 5.1 PRA Stress Testing

The PRA's 2025 stress testing framework requires banks to:
- Project capital positions under prescribed adverse scenarios
- Stress mortgage portfolios by LTV band (benchmarks published: prime 0-50% LTV, 50-60%, 60-70%, etc.)
- Assess the impact of unemployment shocks, interest rate changes, and house price falls on mortgage defaults
- Banks that are not part of the concurrent stress test must use PRA-published scenarios

Current bank stress testing models are typically reduced-form PD/LGD models. An ABM could provide a structural alternative that captures the amplification mechanisms these models miss.

### 5.2 FPC Macroprudential Tools

The Financial Policy Committee has Powers of Direction over:
- LTV flow limits on residential mortgages
- LTI flow limits (currently the 15% limit at ≥4.5× LTI)
- Countercyclical capital buffer
- BTL-specific affordability stress tests (PRA, 2016)

Evaluating the impact of these tools before deployment is exactly what the BoE ABMs were built for. A commercial version would allow banks to assess their own portfolio impact.

### 5.3 FCA Affordability and PSD Reporting

Post-Mortgage Market Review, lenders must conduct affordability assessments including stress testing against a rate rise. The new PSD reporting requirements (PSD001 for sales data, PSD007 for performance data) create a rich dataset that could inform ABM calibration — though access is restricted to regulated firms.

---

## 6. Calibration and Validation

### 6.1 State of the Art in ABM Calibration

Three main approaches dominate:

**Simulated Minimum Distance (Method of Simulated Moments):**
- Minimise weighted distance between observed and simulated summary statistics
- Used by most housing ABMs (including Baptista/Carro models)
- Target moments: price distributions, transaction volumes, LTV distributions, homeownership rates, rental yields

**Approximate Bayesian Computation (ABC):**
- Full posterior estimation without tractable likelihood
- Provides uncertainty quantification over parameters
- Computationally expensive but increasingly feasible with surrogate models

**Surrogate-Assisted Calibration:**
- Train ML models (XGBoost, neural networks, Gaussian processes) on ABM input-output pairs
- Use surrogates for fast parameter search
- Enables calibration of complex models with many parameters
- Recent work (Lamperti et al., 2017; Gao et al., 2022) demonstrates effectiveness

### 6.2 Validation Requirements

For regulatory/commercial acceptance, a housing ABM should demonstrate:
1. **Stylised fact reproduction**: fat-tailed returns, volatility clustering, boom-bust cycles, spatial price correlation
2. **Moment matching**: price levels, transaction volumes, LTV distributions, homeownership rates against empirical data
3. **Out-of-sample performance**: hindcast against known episodes (2008 GFC, 2013-2015 recovery, COVID stamp duty holiday, 2022 rate rises)
4. **Comparison with benchmarks**: outperform or match VAR/DSGE models on key metrics
5. **Sensitivity analysis**: Sobol indices or Morris screening to identify influential parameters
6. **Uncertainty quantification**: ensemble runs with confidence intervals

### 6.3 Key Data Challenge

The BoE models benefit from access to FCA regulatory data (loan-level PSD). A commercial product operating outside the regulatory perimeter would need to:
- Use published aggregate PSD statistics for calibration targets
- Partner with lenders who can provide anonymised loan-level data
- Supplement with Land Registry transaction data and ONS/BoE aggregate statistics
- Potentially use synthetic microdata generation to fill gaps

---

## 7. Engineering and Platform Considerations

### 7.1 Framework Benchmarks

Based on the JuliaDynamics/ABMFrameworksComparison (automated CI benchmarks):

| Framework | Language | Time Ratio (vs Agents.jl=1.0) | Notes |
|-----------|----------|-------------------------------|-------|
| **Ark.jl** | Julia | 0.14–0.73x | Fastest; ECS architecture |
| **Agents.jl** | Julia | 1.0x (baseline) | Good API, well-documented |
| **MASON** | Java | 0.6–7.8x | Used by BoE models; mature |
| **Mesa** | Python | 3.3–159x | Easiest development; slowest |
| **FLAME GPU 2** | CUDA C++ / Python | Hundreds of millions of agents | GPU-accelerated; overkill for most housing sims |

### 7.2 Scale Requirements

For the UK housing market:
- ~27.8 million households (Census 2021)
- ~1.0–1.2 million residential property transactions per year
- ~1.4 million outstanding BTL mortgages
- ~11 million outstanding residential mortgages

A full 1:1 simulation is feasible in Julia/Rust/C++ but would require careful memory management. The BoE models operate at reduced scale (representative sample) which is sufficient for most policy experiments. For a commercial product:
- **Default mode**: 1:100 or 1:1000 scale with statistical reweighting (~28,000 or 278,000 agents)
- **High-fidelity mode**: 1:10 or 1:1 for specific regions or stress scenarios
- **Target runtime**: <5 minutes per scenario at default scale for interactive use

### 7.3 Recommended Technology Stack

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| **Core simulation** | Rust or Julia | Performance critical; Rust for memory safety + easy Python/JS bindings; Julia for rapid prototyping |
| **Calibration** | Python (PyTorch + SBI) | Surrogate-assisted calibration with neural posterior estimation |
| **Data pipeline** | Python (Polars/DuckDB) | Integration with UK open data sources |
| **API** | FastAPI (Python) or Axum (Rust) | Scenario submission, result retrieval |
| **Frontend** | React + D3/Observable Plot | Interactive scenario dashboard |
| **Cloud** | Kubernetes on AWS/Azure | Scalable ensemble runs |

### 7.4 Why Not Use the Existing BoE Java Code?

The open-source BoE models (Java/MASON) are valuable as reference implementations but have limitations for a commercial product:
- MASON's performance is 1-8× slower than Julia alternatives
- Java's ecosystem for ML/data science integration is less rich than Python/Rust
- The models lack a web API, scenario management, or user interface
- However, the model logic should be faithfully ported, not reinvented

---

## 8. Proposed Model Architecture

### 8.1 Agent Types

| Agent | State Variables | Key Behaviours |
|-------|----------------|----------------|
| **Household** | Income, wealth, employment status, age, region, tenure type, mortgage details, risk preferences | Buy/sell/rent decisions, mortgage application, default/arrears, migration |
| **BTL Investor** | Portfolio of properties, rental income, leverage | Purchase/sell investment properties, set rents, respond to yield changes |
| **Developer** | Land bank, build rate, costs | Respond to planning permissions, price signals, construction costs |
| **Bank** | Balance sheet, capital ratios, risk appetite | Mortgage origination (LTV/LTI checks), pricing (spread setting), forbearance decisions |
| **Central Bank** | Base rate, macroprudential settings | Set interest rates, LTV/LTI limits, capital buffer |
| **Government** | Fiscal policy, housing policy | Stamp duty rates, Help to Buy, planning policy, tax rules |

### 8.2 Market Modules

| Market | Mechanism | Key Outputs |
|--------|-----------|-------------|
| **Housing transaction market** | Double auction (following Baptista/Carro) with spatial segmentation | House prices by region/type, transaction volumes, days on market |
| **Rental market** | Posted-price matching with search frictions | Rental yields, vacancy rates, rent levels |
| **Mortgage market** | Bank-mediated with affordability checks and regulatory constraints | LTV distribution, mortgage volumes, interest rates, rejection rates |
| **Labour market** | Stochastic employment transitions calibrated to ONS data | Employment rate, income distribution, sector composition |

### 8.3 Spatial Structure

- **Local Authority level** (331 LAs in England) as primary spatial unit
- House price dynamics localised: price formation within each LA, with spatial spillovers to neighbouring LAs
- Migration flows between LAs calibrated to ONS internal migration data
- Regional economic conditions (employment, wages) drive local housing demand
- Planning constraints modelled per LA (housing completions data)

### 8.4 Scenario Interface

The platform should expose scenarios as structured inputs:

```yaml
scenario:
  name: "Rate rise + unemployment shock"
  horizon_months: 60
  ensemble_size: 100
  
  macro_path:
    bank_rate: [5.25, 5.50, 5.75, 5.50, 5.25, ...]  # monthly path
    unemployment_rate: [4.2, 4.5, 5.0, 5.5, 5.5, ...]
    inflation_cpi: [3.2, 3.0, 2.8, 2.5, 2.2, ...]
    
  policy_changes:
    - type: "ltv_cap"
      value: 0.85
      effective_month: 6
    - type: "stamp_duty"
      threshold_0pct: 250000
      effective_month: 1
      
  supply_shocks:
    - region: "London"
      new_builds_change_pct: -20
      effective_month: 12
```

### 8.5 Output Metrics

| Metric | Granularity | Use Case |
|--------|-------------|----------|
| House Price Index | LA / region / national | Validation, forecasting |
| Transaction volumes | LA / region / national | Market activity monitoring |
| Mortgage origination volumes | By LTV band, product type | Lender planning |
| Default / arrears rates | By LTV band, borrower segment | Risk management |
| Homeownership rate | By age cohort, income quintile | Policy evaluation |
| Rental yields | By region | Investor analysis |
| Distributional impact | By household segment | Equity assessment |
| Bank capital impact | Aggregate | Prudential assessment |

---

## 9. Commercial Viability Assessment

### 9.1 Target Customers

| Segment | Use Case | Willingness to Pay |
|---------|----------|--------------------|
| **Mortgage lenders** (top 10 UK banks/building societies) | Portfolio stress testing, origination strategy, regulatory compliance | High (regulatory necessity) |
| **Housing associations** | Development planning, affordability forecasting | Medium |
| **Local authorities / DLUHC** | Housing needs assessment, planning policy evaluation | Medium (budget-constrained) |
| **Institutional investors** (REITs, pension funds) | Portfolio allocation, risk assessment | High |
| **Central bank / FPC** | Macroprudential policy evaluation | High (but may build internally) |
| **Consultancies** (Big 4, boutique housing consultancies) | Client advisory, scenario analysis | High (reseller channel) |

### 9.2 Differentiation from Incumbents

| Feature | Oxford Economics | Moody's | Proposed ABM Platform |
|---------|-----------------|---------|----------------------|
| Distributional impact analysis | ✗ | ✗ | ✓ |
| Nonlinear fire-sale dynamics | ✗ | ✗ | ✓ |
| Individual household granularity | ✗ | Limited | ✓ |
| Custom policy experiments | Limited scenarios | Limited scenarios | Fully programmable |
| Spatial granularity | City-level | MSA-level | Local Authority |
| UK-specific calibration | ✓ | Partial | ✓ (primary focus) |
| Open methodology | ✗ | ✗ | Transparent (academic heritage) |

### 9.3 Risks and Barriers

1. **Trust / explainability**: ABMs are perceived as "black boxes" by some users. Mitigation: transparent model documentation, validation reports, sensitivity analysis dashboards
2. **Calibration accuracy**: ABM outputs are sensitive to parameter choices. Mitigation: Bayesian calibration with published uncertainty intervals
3. **Computational cost**: Ensemble runs are expensive. Mitigation: surrogate models for fast approximate results, cloud scaling for full runs
4. **Data access**: Some calibration targets require restricted data. Mitigation: partnerships with FCA-regulated firms; use of public aggregates
5. **Regulatory acceptance**: Banks may not be able to use ABM outputs for regulatory capital unless validated against PRA expectations. Mitigation: position as complementary to existing models, not replacement; build validation evidence base
6. **Competition from BoE**: The BoE could develop its own production version. Mitigation: commercial product offers UX, speed, and customisation that a research tool does not; BoE is unlikely to serve commercial users directly

### 9.4 Go-to-Market Strategy

**Phase 1 (0-12 months):** Core model development
- Port BoE/INET housing-model logic to Rust/Julia
- Calibrate against 2000-2025 UK data
- Validate against GFC, COVID, and 2022 rate rise episodes
- Build scenario API and basic dashboard

**Phase 2 (12-24 months):** Pilot with early adopters
- Partner with 2-3 mortgage lenders for pilot
- Integrate PSD-like calibration data via lender partnerships
- Add spatial model (LA-level)
- Publish validation paper

**Phase 3 (24-36 months):** Scale
- Full scenario dashboard with self-service
- Multi-region model (England, Scotland, Wales, NI)
- Add developer/supply-side agents
- API access for integration with lender risk systems
- Regulatory engagement (PRA, FCA) for model acceptance

---

## 10. Open Questions and Research Gaps

1. **Housing supply modelling**: No existing UK housing ABM includes endogenous supply (developers, planning constraints). This is a major gap for realistic scenario analysis and a key differentiator for a commercial product.

2. **Spatial resolution**: The BoE models are non-spatial or coarsely spatial. The relationship between LA-level granularity and model accuracy/calibration requirements is unexplored.

3. **BTL investor behaviour**: BTL investors are heterogeneous (amateur landlords vs professional portfolios) with different risk tolerances and exit strategies. Current models treat them as a single class.

4. **Rental market dynamics**: UK rental market regulations (Section 21 reform, rent controls) are changing rapidly. No ABM yet models these regulatory changes.

5. **Government intervention modelling**: Help to Buy, stamp duty holidays, and First Homes have significant market effects but are absent from published ABMs.

6. **Calibration without regulatory data**: Whether a commercially calibrated model (without FCA PSD access) can achieve sufficient accuracy for lender use is untested.

7. **Real-time data integration**: Whether ABM scenarios can be updated with monthly data releases for dynamic forecasting (vs static scenario analysis) is an open engineering question.

8. **Regulatory acceptance pathway**: No UK bank currently uses an ABM for regulatory stress testing. The pathway to PRA acceptance is undefined.

---

## 11. Conclusion

The academic foundations for a UK housing market ABM are strong and publicly available. The BoE/INET model lineage provides a validated, open-source starting point. The gap between existing commercial tools (top-down econometric) and what an ABM offers (bottom-up, heterogeneous, nonlinear) is real and commercially meaningful, particularly for:

- **Mortgage lenders** needing distributional stress testing
- **Macroprudential authorities** evaluating policy impacts before deployment
- **Investors** seeking scenario analysis that captures tail risks

The key technical challenges are: (1) achieving production-grade calibration accuracy with available data, (2) engineering a platform fast enough for interactive use, and (3) building the validation evidence base needed for regulatory trust.

The proposed architecture — porting the proven BoE model logic to a high-performance runtime, adding missing channels (supply, government policy, spatial structure), wrapping it in a cloud API with a scenario dashboard — is technically feasible with a team of 4-6 engineers/researchers over 12-24 months.

The commercial opportunity is real: there is no ABM-based housing scenario product in the UK market, the regulatory environment is creating increasing demand for sophisticated stress testing, and the academic foundations are freely available to build upon.
