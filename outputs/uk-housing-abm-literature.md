# Agent-Based Models for Simulating the UK Housing Market: A Literature Review

## 1. Introduction

The UK housing market is characterised by persistent boom-bust cycles, significant regional price heterogeneity, and deep interconnections with the mortgage credit system. Traditional approaches to modelling these dynamics — including dynamic stochastic general equilibrium (DSGE) models, vector autoregressions (VARs), and hedonic regression — rely on representative-agent assumptions and equilibrium conditions that limit their ability to capture the heterogeneous behaviours, feedback loops, and emergent nonlinearities that characterise real housing markets.

Agent-based models (ABMs) offer a fundamentally different approach: they simulate individual households, banks, investors, and other actors making decisions according to heterogeneous behavioural rules, and observe aggregate dynamics — such as house prices, transaction volumes, and default rates — as emergent outcomes of these micro-level interactions. Since Farmer & Foley's influential call in *Nature* that "the economy needs agent-based modelling" [1], the methodology has gained traction in central banks [2][3] and academia for studying housing markets specifically.

This review surveys the literature on agent-based models applied to the UK housing market, covering the period 2009–2026. It identifies the major model lineages, analyses their agent types and market mechanisms, examines calibration and validation approaches, surveys the policy experiments conducted, and situates UK-specific work within the broader international housing ABM literature.

---

## 2. Taxonomy of UK Housing ABMs

The UK housing ABM literature can be organised into three distinct lineages, plus several standalone contributions.

### 2.1 The Surrey/PwC Model (Gilbert et al., 2009)

The earliest UK-specific housing ABM was developed by Nigel Gilbert, John Hawksworth, and Paul Swinney at the University of Surrey's Centre for Research in Social Simulation (CRESS), in collaboration with PricewaterhouseCoopers [4][5].

- **Platform**: NetLogo
- **Agents**: Households (buyers/sellers) and realtors (estate agents)
- **Space**: Abstract grid; houses differentiated only by a neighbourhood price index
- **Market mechanism**: Posted-price with realtor valuations based on local recent sales; sellers reduce prices over time if unsold
- **Behavioural rules**: Households move when forced (job relocation, death) or when mortgage costs become unaffordable or income rises enough to trade up
- **Key findings**: Reproduced stylised facts including price sensitivity to interest rates, the role of first-time buyers in maintaining demand, asymmetric supply responses (slow to expand, fast to contract), and sticky-downward price dynamics
- **Limitations**: No explicit mortgage market, no buy-to-let investors, no spatial structure beyond neighbourhood index, not calibrated to specific UK data

This model established the template for subsequent UK work and remains actively extended.

### 2.2 The BoE/INET-Oxford Model Lineage (Baptista → Carro → Bardoscia)

The most influential UK housing ABM programme emerged from the collaboration between the Bank of England and the Institute for New Economic Thinking (INET) at Oxford, producing three major papers over eight years:

**Baptista et al. (2016), BoE Staff Working Paper No. 619** [6][7]:
- **Platform**: Java (custom framework)
- **Agents**: First-time buyers, homeowners, buy-to-let (BTL) investors, renters, a bank agent, a central bank agent
- **Market mechanism**: Double auction for owner-occupier transactions and rental matching
- **Calibration data**: Zoopla listing data, FCA loan-level regulatory data (PSD), English Housing Survey, ONS data
- **Policy experiments**: Hard LTV limit, soft LTI limit (allowing limited share of unconstrained new mortgages)
- **Key findings**: LTV/LTI policies mitigate house price cycles by reducing leverage; policies targeting owner-occupiers spill over to the rental market as BTL investors fill the gap
- **Open source**: `INET-Complexity/housing-model` on GitHub (MIT licence) [8]

**Carro et al. (2022/2023), BoE Staff Working Paper No. 976 / Industrial and Corporate Change** [9]:
- Extended Baptista model with enhanced household heterogeneity and age-dependent behaviour
- Assessed macroprudential policy effects at the *individual household* level, not just aggregate
- Demonstrated that targeting one risk measure (e.g., LTV) affects other risk metrics, necessitating careful multi-dimensional calibration
- Confirmed the compositional shift: LTV caps reduce owner-occupier market share, increasing BTL investor presence
- **Open source**: `adrian-carro/spatial-housing-model` on GitHub (MIT licence) [10]

**Bardoscia, Carro et al. (2024), BoE Staff Working Paper No. 1,066** [11]:
- Integrated the housing ABM into a full **macroeconomic** agent-based model with production firms, a consumption goods market, and a labour market
- Added **bank capital requirements** as a policy instrument alongside borrower-based tools
- Three experiments: (i) higher capital requirements → sharp decline in mortgage and commercial lending; (ii) LTI cap → house prices fall relative to income, homeownership decreases; (iii) combined → positive GDP and employment effects, no material inflation impact
- Represents the **current state of the art** for UK housing ABMs

### 2.3 The Ge Spatial Housing Model (2013–2017)

Jiaqi Ge developed a spatial housing ABM using the MASON platform [12][13]:

- **Ge (2013/2014)**: Argued that lenient lending policy is responsible for housing price bubbles, using a spatial model with a grid-based housing market [12]
- **Ge (2017)**: Published in *Computers, Environment and Urban Systems*, modelling endogenous rise and collapse of housing prices [13]
- These models emphasise the spatial dimension of housing markets but have been less widely adopted than the BoE/INET lineage

### 2.4 The Gamal/Gilbert Extension (2024)

The most recent UK housing ABM, published in JASSS volume 27 [14]:

- **Gamal, Pinto & Iossifova (2024)**: "A Behavioural Agent-Based Model for Housing Markets: Impact of Financial Shocks in the UK"
- **Platform**: NetLogo (with Python version)
- **Extends**: Gilbert et al. (2009) [4]
- **Key additions**: (1) explicit rental and BTL housing markets; (2) tenant and investor agents; (3) agents can transition between tenant, homebuyer, and investor over their lifetime; (4) fixed-rate mortgage periods with reversion to variable rates
- **Experiments**: Sudden interest rate shocks and LTV shocks, inspired by the 2022 UK rate rises
- **Key findings**: Interest rate rise → house price decrease + rent increase (with lag); interest rate fall → price increase + rent decrease; LTV decline → steep price decrease + rent increase; asymmetric responses between rise and fall scenarios
- **Open source**: GitHub and CoMSES repository

### 2.5 Other UK-Related Contributions

- **Tarne, Bezemer & Theobald (2022)** [15]: Published in JEDC, extended the Baptista model to study borrower-specific LTV policies and their effects on wealth inequality and consumption volatility. Found that LTV caps significantly increase wealth inequality.
- **SpringerLink (2025)** [16]: "An Agent-Based Model for Housing Markets: Impact of a Financial Shock on Wealth in the UK" — investigates the 2022 interest rate shock effects on household wealth.

---

## 3. Agent Types and Behavioural Rules

### 3.1 Household Agent Types

| Agent Type | Present In | Key Behaviours |
|------------|-----------|----------------|
| **First-time buyers** | Baptista [6], Carro [9], Bardoscia [11] | Enter market when income/savings sufficient; constrained by LTV/LTI |
| **Homeowners** | All models | Trade up/down based on income changes; default when unable to meet payments |
| **BTL investors** | Baptista [6], Carro [9], Gamal [14] | Purchase to rent; respond to yield changes; interest-only mortgages |
| **Renters/tenants** | Baptista [6], Carro [9], Gamal [14] | Rent when unable to buy; may transition to buyers |
| **Generic households** | Gilbert [4], Ge [12][13] | Combined buyer/seller without tenure-type differentiation |

### 3.2 Non-Household Agents

| Agent Type | Present In | Role |
|------------|-----------|------|
| **Bank** | Baptista [6], Carro [9], Bardoscia [11] | Mortgage origination with LTV/LTI checks, rate setting |
| **Central bank** | Baptista [6], Bardoscia [11] | Sets base rate, macroprudential parameters |
| **Realtors** | Gilbert [4], Gamal [14] | Value properties based on local sales history |
| **Production firms** | Bardoscia [11] only | Employ households, produce consumption goods |

### 3.3 Behavioural Rules

All UK housing ABMs use **bounded rationality** — heuristic decision rules rather than full optimisation [2][3]. Key dimensions of behavioural modelling include:

- **Adaptive expectations**: Prices based on recent local sales (Gilbert [4], Gamal [14]) or market clearing in auctions (Baptista [6], Carro [9]). No model uses rational expectations.
- **Heterogeneity sources**: Income (calibrated distributions), wealth accumulation, age/lifecycle (Carro [9]), risk preferences (Gamal [14]).
- **Transition rules**: Gamal (2024) allows agents to transition between tenure types based on financial thresholds — the "relatively rich" and "relatively poor" classification determines market entry and exit [14].

---

## 4. Market Mechanisms and Price Formation

### 4.1 Double Auction (Baptista/Carro/Bardoscia)

The BoE/INET models use a double auction mechanism [6][9][11]: sellers list with asking prices, buyers submit bids based on affordability, matching occurs with priority rules. This produces competitive price discovery.

### 4.2 Posted-Price with Realtor Valuation (Gilbert/Gamal)

Gilbert (2009) and Gamal (2024) use a posted-price mechanism [4][14]: realtors value houses based on local recent transactions; unsold houses experience price decay. This better captures search frictions and information asymmetry.

### 4.3 Comparison

| Model | Mechanism | Price Discovery | Information Structure |
|-------|-----------|----------------|----------------------|
| Baptista/Carro [6][9] | Double auction | Competitive bidding | Full market |
| Gilbert/Gamal [4][14] | Posted-price + decay | Realtor valuation | Local only |
| Ge [13] | Spatial matching | Neighbourhood-based | Spatial proximity |
| Korean ABM [17] | Brochure concept | Limited listings | Restricted (information asymmetry) |

---

## 5. Calibration and Validation Methods

### 5.1 Data Sources

| Data Source | Used By | Purpose |
|-------------|---------|---------|
| **Zoopla/Rightmove** | Baptista [6], Carro [9] | Asking prices, time on market |
| **FCA PSD (loan-level)** | Baptista [6], Carro [9] | LTV distributions, mortgage volumes |
| **English Housing Survey** | Baptista [6], Carro [9] | Tenure distribution |
| **ONS earnings** | Gamal [14] | Income distribution |
| **BoE interest rates** | Gamal [14] | Base rate, mortgage rates |
| **DLUHC housing stats** | Gamal [14] | Construction rates |

### 5.2 Calibration Approaches

The UK literature uses relatively simple calibration compared to state-of-the-art methods [18][19]:

- **Manual/expert calibration**: Gilbert [4] and Gamal [14]
- **Full-factorial design of experiments**: Korean ABM [17]
- **Moment matching (informal)**: Baptista [6] and Carro [9] match summary statistics but do not report formal simulated minimum distance

More rigorous methods exist — ABC [19], surrogate-assisted calibration [20], neural posterior estimation [21] — but have not been applied to UK housing ABMs.

### 5.3 Validation Gap

No UK housing ABM has published formal out-of-sample forecasting results. Windrum, Fagiolo & Moneta (2007) and Platt (2019) identify best practices — formal statistical calibration, uncertainty quantification, out-of-sample validation — none of which are fully implemented in published UK models [18][19]. This is the most significant methodological limitation.

---

## 6. Policy Experiments and Findings

### 6.1 Macroprudential Policy (LTV/LTI)

| Paper | Experiment | Key Finding |
|-------|-----------|-------------|
| Baptista (2016) [6] | Hard LTV limit | Mitigates price cycle; spillovers to rental market |
| Baptista (2016) [6] | Soft LTI limit | Moderates credit growth; compositional shift toward BTL |
| Carro (2022) [9] | LTV/LTI comparative statics | Targeting one metric affects others; heterogeneous impacts |
| Tarne et al. (2022) [15] | Borrower-specific LTV | Caps significantly increase wealth inequality |
| Gamal (2024) [14] | LTV shock | Steep price changes; rent increase on decline |

**Consensus**: LTV/LTI tightening reduces prices and credit but creates unintended distributional consequences — particularly increased BTL market share and rent increases.

### 6.2 Bank Capital Requirements

Bardoscia et al. (2024) [11]: increased capital requirements sharply reduce lending and transactions; combined with LTI, positive GDP/employment effects emerge.

### 6.3 Interest Rate Shocks

| Paper | Experiment | Key Finding |
|-------|-----------|-------------|
| Gilbert (2009) [4] | +3% rate increase | 43% immediate price decrease |
| Gamal (2024) [14] | 3.7% → 8% | 44% price decrease over 10 years; rent increase with 3-year lag |
| Gamal (2024) [14] | 8% → 3.7% | 62% price increase; rents unaffected |

**Consensus**: Interest rate rises decrease house prices with asymmetric effects — rises cause sharper disruption than equivalent declines [4][14].

### 6.4 Notable Policy Gap

No UK housing ABM has modelled: Help to Buy, stamp duty changes, planning policy, immigration/population growth, or Section 21 rental reform.

---

## 7. Relation to International Housing ABM Literature

### 7.1 The Washington DC Model

Geanakoplos, Axtell, Farmer et al. built the most ambitious housing ABM — operating at **1:1 scale** (~2 million agents) for the DC metro area [22][23][24]. It reproduced the observed bubble shape and demonstrated that maintaining credit standards would have prevented the bubble more effectively than higher rates. Published in the American Economic Review (2012) [22].

### 7.2 European Models

- **ECB**: Laliotis et al. (2019/2020) — multi-country LTV caps assessment [25]
- **Hungary**: Mérő et al. (2023) — 1:1 scale model of 4 million households [26]
- **Denmark**: Cokayne (2019) — finds stricter fiscal policies reduce price fluctuations [27]
- **Iceland**: Erlingsson et al. (2014) — housing bubble ABM in a credit network [28]
- **Netherlands**: Bezemer et al. — affordability with heterogeneous agents [29]

### 7.3 ABM Methodology Reviews

Several survey papers provide context for the housing ABM field:
- **Axtell & Farmer (2025)**: Comprehensive JEL review of ABM in economics and finance [30]
- **Haldane & Turrell (2018/2019)**: Drawing on different disciplines for macroeconomic ABMs [3]
- **Turrell (2016)**: BoE Quarterly Bulletin introduction to ABMs for central banking [2]

### 7.4 Comparative Position

The UK literature is among the most developed internationally. Its distinguishing features are: strong BoE institutional support, open-source code availability, and focus on macroprudential policy. However, it lags the DC model in **scale**, Hungary in **data resolution**, and the broader methodology literature in **formal calibration rigour**.

---

## 8. Limitations and Open Questions

### 8.1 Acknowledged Limitations

1. **No endogenous housing supply**: No UK model includes developers responding to price signals or planning constraints [6][9][11][14].
2. **Limited spatial structure**: BoE/INET models are non-spatial or coarsely spatial [6][9]. No model operates at Local Authority level with real geographic data.
3. **Simplified default mechanics**: No UK model implements the "double trigger" default mechanism (negative equity + income shock) identified by BoE Staff Working Paper 812 [31].
4. **No fire-sale feedback loop**: The default → forced sale → price decline → more defaults amplification mechanism is theoretically important but not explicitly modelled in any UK ABM.
5. **Homogeneous BTL investors**: Current models treat BTL investors as a single class [6][9][14].
6. **No government policy interventions**: Help to Buy, stamp duty holidays, Right to Buy are absent from all published models.
7. **Weak calibration**: No UK model uses formal statistical calibration or reports out-of-sample validation [18][19].
8. **Fixed-rate modelling**: Only Gamal (2024) [14] models UK-specific fixed-rate periods with variable-rate reversion.

### 8.2 Open Research Questions

1. Can a UK housing ABM reproduce known historical episodes out of sample?
2. What spatial resolution is needed to capture regional price divergence?
3. How does endogenous housing supply affect boom-bust cycle dynamics?
4. Can formal Bayesian calibration improve model credibility?
5. What role does expectations heterogeneity play in price dynamics?
6. How do rental market regulations interact with owner-occupier dynamics?

---

## 9. Conclusion

The literature on agent-based models for simulating the UK housing market has developed substantially since Gilbert et al.'s (2009) pioneering work [4]. The field is dominated by the BoE/INET-Oxford lineage [6][9][11], which has produced the most sophisticated and policy-relevant models. A parallel line extending Gilbert's model [14] has added valuable analysis of interest rate shock transmission.

**Points of consensus:**
- LTV/LTI tightening effectively reduces house prices and credit growth [6][9][14]
- Macroprudential policies create unintended rental market spillovers via BTL compositional shifts [6][9]
- Interest rate changes have asymmetric effects on prices [4][14]
- Agent heterogeneity is essential for capturing distributional impacts [9][11]

**Critical gaps for future work:**
- Formal calibration and out-of-sample validation [18][19]
- Endogenous housing supply with developer agents
- Government policy interventions (Help to Buy, stamp duty, planning)
- Spatial structure at Local Authority level
- Double-trigger default mechanism with fire-sale feedback [31]

The intellectual foundations are strong and publicly available, with open-source code for both major model lineages [8][10]. The field is well-positioned for next-generation models combining ABM behavioural richness with modern simulation-based inference.

---

## Sources

[1] Farmer, J.D. & Foley, D. (2009). "The economy needs agent-based modelling." *Nature*, 460, 685–686. https://www.nature.com/articles/460685a

[2] Turrell, A. (2016). "Agent-based models: understanding the economy from the bottom up." *Bank of England Quarterly Bulletin*, Q4. https://www.bankofengland.co.uk/quarterly-bulletin/2016/q4/agent-based-models-understanding-the-economy-from-the-bottom-up

[3] Haldane, A. & Turrell, A. (2019). "Drawing on different disciplines: macroeconomic agent-based models." *Journal of Evolutionary Economics*, 29, 39–66. https://link.springer.com/article/10.1007/s00191-018-0557-5

[4] Gilbert, N., Hawksworth, J.C. & Swinney, P.A. (2009). "An agent-based model of the English housing market." AAAI Spring Symposium. https://cress.soc.surrey.ac.uk/housingmarket/index.html

[5] Gilbert, N., Hawksworth, J.C. & Swinney, P.A. (2009). Model description. https://cress.soc.surrey.ac.uk/housingmarket/ukhm.html

[6] Baptista, R., Farmer, J.D., Hinterschweiger, M., Low, K., Tang, D. & Uluc, A. (2016). "Macroprudential policy in an agent-based model of the UK housing market." BoE Staff Working Paper No. 619. https://www.bankofengland.co.uk/working-paper/2016/macroprudential-policy-in-an-agent-based-model-of-the-uk-housing-market

[7] Baptista et al. (2016). SSRN version. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2850414

[8] INET-Complexity/housing-model. GitHub. https://github.com/INET-Complexity/housing-model

[9] Carro, A., Hinterschweiger, M., Uluc, A. & Farmer, J.D. (2022). "Heterogeneous effects and spillovers of macroprudential policy in an agent-based model of the UK housing market." BoE Staff Working Paper No. 976. Published: *Industrial and Corporate Change* (2023). https://www.bankofengland.co.uk/working-paper/2022/heterogeneous-effects-and-spillovers-of-macroprudential-policy-in-model-of-uk-housing-market

[10] adrian-carro/spatial-housing-model. GitHub. https://github.com/adrian-carro/spatial-housing-model

[11] Bardoscia, M., Carro, A., Hinterschweiger, M., Napoletano, M., Popoyan, L., Roventini, A. & Uluc, A. (2024). "The impact of prudential regulations on the UK housing market and economy." BoE Staff Working Paper No. 1,066. https://www.bankofengland.co.uk/working-paper/2024/the-impact-of-prudential-regulations-on-the-uk-housing-market-and-economy

[12] Ge, J. (2014). "Who creates housing bubbles? An agent-based study." *International Workshop on Multi-Agent Systems and Agent-Based Simulation*, Springer.

[13] Ge, J. (2017). "Endogenous rise and collapse of housing price." *Computers, Environment and Urban Systems*, 62, 182–198.

[14] Gamal, Y., Pinto, N. & Iossifova, D. (2024). "A Behavioural Agent-Based Model for Housing Markets: Impact of Financial Shocks in the UK." *JASSS*, 27(4), 5. https://www.jasss.org/27/4/5.html

[15] Tarne, R., Bezemer, D. & Theobald, T. (2022). "The effect of borrower-specific loan-to-value policies on household debt, wealth inequality and consumption volatility." *JEDC*, 144. DOI: 10.1016/j.jedc.2022.104526

[16] "An Agent-Based Model for Housing Markets: Impact of a Financial Shock on Wealth in the UK." *Springer* (2025). https://link.springer.com/chapter/10.1007/978-3-031-91782-0_10

[17] JASSS (2020). "Housing Market Agent-Based Simulation with Loan-To-Value and Debt-To-Income." *JASSS*, 23(4), 5. https://www.jasss.org/23/4/5.html

[18] Windrum, P., Fagiolo, G. & Moneta, A. (2007). "Empirical Validation of Agent-Based Models: Alternatives and Prospects." *JASSS*, 10(2), 8. https://www.jasss.org/10/2/8.html

[19] Platt, D. (2019). "A Comparison of Economic Agent-Based Model Calibration Methods." arXiv:1902.05938. https://arxiv.org/abs/1902.05938

[20] Lamperti, F., Roventini, A. & Sani, A. (2018). "Agent-based model calibration using machine learning surrogates." *JEDC*, 90, 366–389.

[21] Monti, C., Pangallo, M., De Francisci Morales, G. & Bonchi, F. (2022). "On learning agent-based models from data." arXiv:2205.05052. https://arxiv.org/abs/2205.05052

[22] Geanakoplos, J., Axtell, R., Farmer, J.D. et al. (2012). "Getting at Systemic Risk via an Agent-Based Model of the Housing Market." *American Economic Review*, 102(3), 53–58. https://www.aeaweb.org/articles.php?doi=10.1257%2Faer.102.3.53

[23] Axtell, R. et al. (2024). "An Agent-Based Model of the Housing Market Bubble in Metropolitan Washington D.C." SSRN. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4710928

[24] "How to prevent the next housing bubble." INET Oxford. https://www.inet.ox.ac.uk/news/prevent-next-housing-bubble

[25] Laliotis, D. et al. (2020). "An agent-based model for the assessment of LTV caps." *Quantitative Finance*, 20(10), 1721–1748.

[26] Mérő, B. et al. (2023). "A high-resolution, data-driven agent-based model of the housing market." *JEDC*, 155.

[27] Cokayne, G. (2019). "The effects of macro-prudential policies on house price cycles in an agent-based model of the Danish housing market." Danmarks Nationalbank WP 138.

[28] Erlingsson, E.J. et al. (2014). "Housing Market Bubbles and Business Cycles in an Agent-Based Credit Economy." *Economics*, 8. https://www.degruyter.com/document/doi/10.5018/economics-ejournal.ja.2014-8/html

[29] Bezemer, D. et al. "Roof or real estate? An agent-based model of housing affordability in The Netherlands." University of Groningen. https://www.rug.nl/staff/d.j.bezemer/roof-or-real-estate.pdf

[30] Axtell, R.L. & Farmer, J.D. (2025). "Agent-Based Modeling in Economics and Finance: Past, Present, and Future." *Journal of Economic Literature*, 63(1), 197–287. https://www.aeaweb.org/articles?from=f&id=10.1257%2Fjel.20221319

[31] BoE Staff Working Paper No. 812 (2019). "Three triggers? Negative equity, income shocks and institutions as determinants of mortgage default." https://www.bankofengland.co.uk/working-paper/2019/three-triggers-negative-equity-income-shocks-and-institutions-as-determinants-of-mortgage-default

[32] Pangallo, M., Nadal, J.P. & Vignes, A. (2019). "Residential income segregation: A behavioral model of the housing market." *JEBO*, 159, 15–35.

[33] Grazzini, J. & Richiardi, M. (2017). "Bayesian estimation of agent-based models." *JEDC*, 77, 26–47. https://econpapers.repec.org/RePEc:eee:dyncon:v:77:y:2017:i:c:p:26-47
