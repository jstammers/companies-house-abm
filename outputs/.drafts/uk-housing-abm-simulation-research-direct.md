# Research Notes: UK Housing ABM Simulation

## Search Terms Used
1. "agent-based model UK housing market house prices Bank of England"
2. "Baptista Carro agent-based model UK housing macroprudential BoE staff working paper"
3. "commercial housing market scenario planning tools Moody's Oxford Economics CoreLogic UK"
4. "ABM calibration validation housing market method simulated moments Bayesian"
5. "UK housing mortgage default agent-based model stress testing PRA FPC macroprudential"
6. "Simudyne agent-based model commercial platform financial services housing"
7. "Land Registry Price Paid Data ONS House Price Index methodology UK FCA PSD mortgage data"
8. "FLAME GPU agent-based model housing Mesa MASON ABM platform scalability performance"
9. "Geanakoplos leverage cycle agent-based model housing mortgage default fire sale dynamics"
10. "PRA stress testing mortgage portfolios UK bank scenario analysis 2024 2025"
11. "Carro agent-based model UK housing open source code GitHub Java"
12. "FCA Product Sales Data PSD001 PSD007 mortgage microdata what fields available"
13. "Help to Buy stamp duty holiday agent-based model housing policy UK evaluation"
14. "Agents.jl Julia agent-based model performance benchmark vs Mesa Python"
15. "agent-based model housing market calibration UK Wealth Distribution English Housing Survey"
16. "Axtell Farmer Washington DC housing agent-based model large scale"
17. "ABM housing market spatial heterogeneity regional house prices UK postcode"
18. "mortgage default model UK arrears repossession negative equity income shock"

## Key Sources Found

### T1: Academic ABM Literature
- Baptista et al. (2016) BoE WP 619 — foundational UK housing ABM
- Carro et al. (2022) BoE WP 976 — extended ABM with heterogeneous macroprudential effects
- Bardoscia, Carro et al. (2024) BoE WP 1066 — macroeconomic ABM with capital requirements + LTI
- BoE UK-HANK model (2026) — new HANK (not ABM but heterogeneous agent) model
- Geanakoplos, Axtell, Farmer et al. (2012) AER — Washington DC housing ABM
- Axtell et al. (2024) SSRN — full DC metro ABM bubble model
- Gilbert, Hawksworth, Swinney (2009) — early UK housing ABM (Surrey/PwC)
- JASSS paper on Korean housing ABM with LTV/DTI (2020)
- Laliotis et al. (2019) ECB WP 2294 — European LTV caps ABM
- Open source: INET-Complexity/housing-model (Java, MIT), adrian-carro/spatial-housing-model (Java, MIT)

### T2: Data & Commercial Tools
- Land Registry Price Paid Data — open, transaction-level, all England/Wales sales
- ONS UK HPI — hedonic regression, monthly, regional/LA level
- FCA PSD001/PSD007 — mortgage origination microdata (loan amounts, LTV, income, rate type)
- English Housing Survey — household characteristics, tenure
- BoE mortgage lending stats — aggregate flows, rates, LTV distributions
- Oxford Economics Real Estate Service — macro-model-driven forecasts, scenario analysis
- Simudyne — commercial ABM platform with financial toolkit, lending model module
- PRA 2025 stress testing guidance — scenarios for banks

### T3: Mortgage & Default Modelling
- BoE WP 812 (2019) "Three triggers?" — double trigger: negative equity + income shock + institutional factors
- CEP/ORA models — aggregate UK mortgage arrears/repossessions with negative equity driver
- Baptista/Carro models include bank agent with LTV/LTI constraints, affordability checks
- Bardoscia et al. (2024) adds capital requirements channel

### T4: Calibration & Engineering
- ABM calibration methods: MSM, ABC, indirect inference, surrogate-assisted (ML)
- Framework benchmarks: Agents.jl ~1x, Ark.jl ~0.3x, MASON ~1-7x, Mesa ~3-160x depending on model
- FLAME GPU — GPU-accelerated, hundreds of millions of agents on H100
- Carro model is Java/MASON-based, open source
