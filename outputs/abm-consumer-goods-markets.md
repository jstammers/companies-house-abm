# Agent-Based Models for Consumer Goods Markets

## Executive Summary

Agent-based modeling (ABM) has become a significant methodology for studying consumer goods markets over the past two decades. By encoding micro-level behavioral rules for heterogeneous consumer and firm agents, ABMs generate emergent market-level phenomena — diffusion curves, price dynamics, brand competition, and spatial shopping patterns — that analytical and aggregate models cannot capture. This brief surveys the landscape across seven dimensions: frameworks and architectures, consumer agent modeling, firm agent modeling, market mechanisms, calibration and validation, software toolkits, and frontier directions including LLM-powered agents and digital twins. The field is transitioning from stylized theoretical models toward empirically calibrated, data-driven simulations, with the most recent frontier being LLM-based generative agents that replace hand-coded decision rules with language model reasoning.

---

## 1. Frameworks and Architectures

### 1.1 Foundational Work

ABM in consumer markets builds on the general ABM tradition established by Epstein & Axtell (1996, *Growing Artificial Societies*), Bonabeau (2002), and the computational economics program of Tesfatsion. The specific application to marketing was formalized by **Rand & Rust (2011)**, who provided guidelines for rigorous ABM in marketing, identifying six indicators for when ABM is appropriate: medium numbers of agents, local interactions, heterogeneity, rich environments, temporal dynamics, and adaptive agents.

The field's growth was documented by **Romero, Chica, Damas & Rand (2023)** in a bibliometric analysis covering two decades of ABM in marketing, published as an SSRN working paper. This analysis identified increasing publication rates and broadening application domains beyond innovation diffusion to pricing, advertising, and competitive strategy.

### 1.2 Key Surveys

Several reviews have mapped the landscape:

- **Kiesling, Günther, Stummer & Wakolbinger (2012)** provided an extensive review of ABM for innovation diffusion in *Central European Journal of Operations Research*, covering agent decision models, network structures, and calibration approaches.
- **Negahban & Yilmaz (2014)** published an integrated review of ABM in marketing research in the *Journal of Simulation*, categorizing decision-making approaches into six types: preference matching, stage-based, utility functions, exposure threshold, past experience, and random.
- **Rand & Stummer (2021)** offered a comprehensive overview of strengths and criticisms of ABM for new product market diffusion in *Annals of Operations Research*, including detailed discussion of parameterization, verification/validation, arbitrariness, causality, and computational cost challenges.
- **Jamali & Lazarova-Molnar (2026)** published a comprehensive review of ABM for economic markets in the *Journal of Simulation*, covering applications, challenges, and opportunities — cited in the recent RetailSim paper.

### 1.3 Consumer Goods–Specific Models

Direct application to consumer goods markets includes:

- **Glavin & Sengupta (2015)** presented a utility-based model with psychological drivers (loyalty and change-of-pace strategies) for studying typical consumer goods markets, published as a chapter in IGI Global's *Handbook of Research on Managing and Influencing Consumer Behavior*.
- **North et al. (2010)** developed a multiscale agent-based consumer market model calibrated and validated for **Procter & Gamble** using Nielsen and IRI household panel data, scanner data, and industry statistics — one of the few published examples of a major CPG company using ABM in practice.
- **Schenk, Löffler & Rauh (2007)** simulated consumer grocery shopping behavior at a regional level, published in the *Journal of Business Research*.
- **Sturley, Newing & Heppenstall (2018)** evaluated ABM for capturing consumer grocery retail store choice behaviors, published in the *International Review of Retail, Distribution and Consumer Research*.

---

## 2. Consumer Agent Modeling

### 2.1 Decision Rules

Following Negahban & Yilmaz's (2014) taxonomy, consumer agents in goods market ABMs use:

| Decision Type | Description | Example |
|---|---|---|
| **Preference matching** | Similarity between agent preferences and product attributes | Schramm et al. (2010) |
| **Stage-based** | Rogers' adoption stages: awareness → attitude → decision → experience | Stummer et al. (2015) |
| **Utility functions** | Weighted combination of price, quality, WOM influence, budget | Delre et al. (2007) |
| **Exposure threshold** | Adopt when share of adopting neighbors exceeds threshold | Granovetter & Soong (1986) |
| **Past experience** | Learning from repeated purchase, dynamic preference evolution | Stummer et al. (2015) |
| **Random** | Stochastic component for exploration | Various |

Most empirically grounded models combine multiple mechanisms — e.g., utility-based choice modulated by social influence thresholds and advertising exposure.

### 2.2 Social Influence and Word-of-Mouth

Social influence is a central mechanism. ABMs distinguish:

- **Direct interactions** (word-of-mouth): Consumer-to-consumer information exchange through social networks, which can be positive or negative.
- **Indirect interactions** (social influence): Threshold-based conformity effects where adoption depends on the share of peers who have adopted.
- **Advertising**: External "broadcast" interaction from firm agents, typically with lower influence weight than peer WOM.

Key findings from the literature include that seeding the most connected individuals in a network does not always maximize diffusion speed (Watts & Dodds, 2007), and that weak ties can serve as critical bridges between social groups (Brown & Reingen, 1987).

### 2.3 Heterogeneity

Consumer agents are typically heterogeneous across:
- **Innovativeness** (Rogers' adopter categories)
- **Price sensitivity** vs. quality sensitivity
- **Social network position** and susceptibility to influence
- **Demographics** (income, location, lifestyle)
- **Brand loyalty** and habit formation

This heterogeneity is the key advantage of ABM over aggregate models like Bass (1969), which conflate individual innovativeness with social influence effects.

---

## 3. Firm Agent Modeling and Market Mechanisms

### 3.1 Firm Agents

Firm agents in consumer goods ABMs are less developed than consumer agents. Where modeled, they handle:

- **Pricing**: Posted prices with possible promotional discounts. An algorithm for game-theoretic pricing in ABMs was proposed for oligopolistic markets, enabling simulation of different competitive structures.
- **Advertising**: Mass media campaigns, targeted promotions, and point-of-sale advertising modeled as external influence on consumer agents.
- **Product attributes**: Fixed or evolving product quality, features, and brand positioning.
- **Inventory/supply**: Most ABM studies assume infinite supply (a known limitation noted by Negahban & Yilmaz, 2014), though exceptions exist in supply chain ABMs.

### 3.2 Multi-Brand Competition

Schramm et al. (2010) introduced a model with both consumer and brand agents, enabling study of competitive dynamics. Stummer et al. (2015) demonstrated repeat purchase dynamics in a competitive setting with biofuels competing against conventional fuels, showing how ABM can evaluate pricing strategies (penetration pricing, skimming) in markets with competing products.

### 3.3 Supply Chain Models

Backs et al. (2021) applied ABM to traditional vs. fast fashion supply chains in the apparel industry. Retail promotional pricing effectiveness was analyzed using ABM in a 2024 study published in the *Journal of Revenue and Pricing Management*, examining how consumer preferences and product attributes interact with promotional strategies.

### 3.4 Retail and Spatial Mechanisms

Several models incorporate spatial elements:
- Gas station selection based on geographic proximity (Stummer et al., 2015)
- Regional grocery shopping patterns (Schenk et al., 2007)
- Store choice behavior influenced by distance, store attributes, and competitor proximity (Sturley et al., 2018)

---

## 4. Calibration and Validation

### 4.1 Calibration Approaches

Calibration methods documented in the literature include:

- **Conjoint analysis**: Eliciting consumer preferences for product attributes through choice experiments, then mapping to agent decision rules. Midgley, Marks & Kunchamwar (2007) demonstrated how conjoint analyses can validate ABM marketing models.
- **Scanner data / household panels**: North et al. (2010) calibrated their P&G model using Nielsen/IRI household panel data and store-level scanner data. This is the gold standard but requires proprietary data access.
- **Expert interviews and focus groups**: Stummer et al. (2015) used expert interviews, focus groups, and a survey of 1,000 consumers to parameterize their fuel market model.
- **Sociological network studies**: Dedicated studies of communication patterns to calibrate social network structures and WOM parameters.

### 4.2 Validation Methods

Rand & Rust (2011) proposed a four-level validation framework:

1. **Micro-face validation**: Agents behave plausibly at the individual level
2. **Macro-face validation**: Aggregate outputs look reasonable
3. **Empirical input validation**: Parameters match real-world data
4. **Empirical output validation**: Model outputs match real-world outcomes

Windrum, Fagiolo & Moneta (2007) discussed three methodological approaches for empirical validation in the *JASSS*: indirect calibration, the Werker-Brenner approach, and the history-friendly approach.

### 4.3 The Validation Gap

A persistent criticism is that many published ABMs in marketing lack rigorous empirical validation. Rand & Stummer (2021) note that while ABMs can show that a model is "one possible explanation" of input-output relationships, establishing causality remains challenging. The field is moving toward data-driven calibration using techniques from Bayesian inference and machine learning.

---

## 5. Software Toolkits

| Toolkit | Language | Key Features | Consumer Market Use |
|---|---|---|---|
| **NetLogo** | NetLogo | Easy IDE, educational, large model library | Most widely adopted for marketing ABMs; textbook by Wilensky & Rand (2015) |
| **Mesa** | Python | Integrates with Python data science stack | Growing popularity; JOSS paper (2015+) |
| **Repast Simphony** | Java | HPC support, large-scale simulations | Used for P&G consumer market model (North et al.) |
| **MASON** | Java | Fast execution, research-oriented | Used for biofuel diffusion study (Stummer et al.) |
| **AnyLogic** | Java/Proprietary | Multi-paradigm (ABM + SD + DES), commercial | Industry applications |
| **Agents.jl** | Julia | Performance-focused, modern | Emerging |

The community infrastructure includes CoMSES/OpenABM for model sharing and the SIMSOC mailing list. The ODD protocol (Overview, Design concepts, Details) is the standard for documenting ABMs, though adoption in marketing remains incomplete.

---

## 6. Commercial and Industry Applications

### 6.1 CPG Companies

The best-documented commercial application is **North et al. (2010)** at Procter & Gamble, using household panel data from Nielsen and IRI for a multiscale consumer market model. The model was calibrated against actual market shares and validated with out-of-sample predictions. Practitioners confirmed that the value of ABM lies in comparing scenarios and understanding which combinations of marketing measures yield what results.

### 6.2 Digital Twin Platforms (2024–2026)

Several commercial platforms have emerged that combine ABM with "digital twin" concepts:

- **ZIO Analytics "TWINS"**: A commercial platform that "virtualizes your consumer market with Digital Twins powered by Agentic AI and Causal Science," combining agent-based modeling, predictive simulations, AI calibration, and causal inference.
- **Ario "Twin Persona"**: Uses item-level purchase data to build digital twins of consumer segments, simulating responses to pricing changes, product launches, and competitive threats.
- **CDRC Retail Loyalty Digital Twin**: A proof-of-concept digital twin of a retail loyalty scheme developed in collaboration with a large retailer, using ABM to generate synthetic purchasing scenarios from consumer agents integrated with a cloud-based platform.

### 6.3 Consulting and Marketing Applications

Vanderlynden, Mathieu & Warlop (2024) presented a simulation of consumer behavior facing discounts and promotions, and a 2024 study in the *Journal of Revenue and Pricing Management* analyzed retail promotional pricing effectiveness using ABM, indicating growing applied interest.

---

## 7. Frontier Directions

### 7.1 LLM-Powered Agents

The most significant recent development is replacing hand-coded decision rules with large language model reasoning:

**Chu et al. (2025)** — *"LLM-Based Multi-Agent System for Simulating and Analyzing Marketing and Consumer Behavior"* (arXiv:2510.18155, accepted at IEEE ICEBE 2025). This introduced an LLM-powered multi-agent framework for simulating consumer decision-making, moving beyond rule-based ABMs to capture the complexity of human behavior and social interaction.

**Choi et al. (2026)** — *"What Makes a Sale? Rethinking End-to-End Seller–Buyer Retail Dynamics with LLM Agents"* (arXiv:2604.04468, RetailSim). This is the most comprehensive LLM-based retail simulation to date. Key features:

- **End-to-end pipeline**: Models seller persuasion → buyer-seller interaction → purchase decision → post-purchase support → reviews
- **Persona-driven agents**: Buyers characterized by pickiness, price consciousness, and rationality; sellers by assertiveness, friendliness, and rationality
- **Economic consistency validation**: Reproduces real-world patterns including demographic purchasing behavior, the price-demand relationship, and heterogeneous price elasticity
- **Multi-LLM evaluation**: Tested with 8 backbone models (Qwen3, GPT-oss, DeepSeek, Gemini, GPT-5.4)
- **Human evaluation**: Task fidelity (Likert scale) and persona fidelity (A/B comparison) with Krippendorff's α ≥ 0.67

RetailSim represents a paradigm shift from traditional ABMs: instead of encoding decision rules, the simulation leverages the implicit world knowledge in LLMs to generate realistic multi-stage retail interactions.

### 7.2 Related LLM-Agent Work

- **Li et al. (2024)** — "EconAgent: Large Language Model-Empowered Agents for Simulating Macroeconomic Activities" (ACL)
- **Gao et al. (2024)** — Survey of LLMs empowering ABM in *Humanities and Social Sciences Communications*
- **Zhu et al. (2025)** — "The Automated but Risky Game: Modeling Agent-to-Agent Negotiations and Transactions in Consumer Markets"
- **Bansal et al. (2025)** — "Magentic Marketplace: An Open-Source Environment for Studying Agentic Markets"
- **Zhang et al. (2026)** — "SHOP-R1: Rewarding LLMs to Simulate Human Behavior in Online Shopping via Reinforcement Learning" (ICLR)

### 7.3 Open Challenges

1. **Calibration at scale**: LLM-based agents are harder to calibrate than rule-based agents because their behavior depends on prompt engineering and model-specific biases
2. **Computational cost**: Running thousands of LLM-agent simulations is orders of magnitude more expensive than traditional ABMs (RetailSim reports per-simulation costs from $0.002 to $0.20 depending on backbone model)
3. **Reproducibility**: LLM outputs are stochastic and model-dependent; results may not replicate across model versions
4. **Disentangling effects**: Separating consumer innovativeness, WOM, social influence, and advertising effects remains an open research challenge even in traditional ABMs
5. **Supply-side realism**: Most consumer goods ABMs still assume infinite supply; integrating production constraints, inventory dynamics, and supply chain disruptions is a frontier
6. **Empirical validation standards**: The field lacks standardized validation protocols; many published ABMs have minimal empirical grounding

---

## Open Questions

1. Can LLM-based consumer agents be calibrated to match specific real-world market data (scanner data, panel data) as effectively as hand-crafted rule-based agents?
2. What is the right level of cognitive realism for consumer agents — simple heuristics, utility maximization, BDI architectures, or full LLM reasoning?
3. How should network structures be modeled in the era of social media, where influence topologies change rapidly?
4. Can ABM-based digital twins become standard tools for CPG marketing strategy, or will they remain niche academic exercises?
5. How do we validate ABMs when the systems they model are themselves changing (Lucas critique)?

---

## Sources

1. Rand, W. & Rust, R.T. (2011). "Agent-based modeling in marketing: Guidelines for rigor." *IJRM* 28(3):181-193. https://ideas.repec.org/a/eee/ijrema/v28y2011i3p181-193.html
2. Rand, W. & Stummer, C. (2021). "Agent-based modeling of new product market diffusion: an overview of strengths and criticisms." *Annals of Operations Research* 305:425-447. https://link.springer.com/article/10.1007/s10479-021-03944-1
3. Kiesling, E. et al. (2012). "Agent-based simulation of innovation diffusion: A review." *CEJOR* 20(2):183-230. https://econpapers.repec.org/article/sprcejnor/v_3a20_3ay_3a2012_3ai_3a2_3ap_3a183-230.htm
4. Negahban, A. & Yilmaz, L. (2014). "Agent-based simulation applications in marketing research: An integrated review." *J Simulation* 8(2):129-142.
5. Romero, E. et al. (2023). "Two Decades of Agent-Based Modeling in Marketing: A Bibliometric Analysis." SSRN. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4503664
6. Glavin, S.E. & Sengupta, A. (2015). "Modelling of Consumer Goods Markets: An Agent-Based Computational Approach." IGI Global. https://www.igi-global.com/gateway/chapter/121972
7. North, M.J. et al. (2010). "Multiscale agent-based consumer market modeling." *Complexity* 15(5):37-47.
8. Schenk, T.A. et al. (2007). "Agent-based simulation of consumer behavior in grocery shopping on a regional level." *J Business Research* 60(8):894-903. https://ideas.repec.org/a/eee/jbrese/v60y2007i8p894-903.html
9. Sturley, C. et al. (2018). "Evaluating the potential of agent-based modelling to capture consumer grocery retail store choice behaviours." *Int Rev Retail* 28(1):27-46. https://eprints.whiterose.ac.uk/id/eprint/123605/
10. Delre, S.A. et al. (2007). "Targeting and timing promotional activities." *J Business Research* 60(8):826-835.
11. Stummer, C. et al. (2015). "Innovation diffusion of repeat purchase products in a competitive market." *EJOR* 245(1):157-167.
12. Chica, M. & Rand, W. (2017). "Building agent-based decision support systems for word-of-mouth programs." *JMR* 54(5):752-767.
13. Chu, M. et al. (2025). "LLM-Based Multi-Agent System for Simulating and Analyzing Marketing and Consumer Behavior." arXiv:2510.18155. https://arxiv.org/abs/2510.18155
14. Choi, J. et al. (2026). "What Makes a Sale? Rethinking End-to-End Seller-Buyer Retail Dynamics with LLM Agents." arXiv:2604.04468. https://arxiv.org/abs/2604.04468
15. Gao, C. et al. (2024). "Large language models empowered agent-based modeling and simulation: a survey." *Humanities & Social Sciences Communications*.
16. Windrum, P. et al. (2007). "Empirical Validation of Agent-Based Models." *JASSS* 10(2):8. https://www.jasss.org/10/2/8/8.pdf
17. Midgley, D. et al. (2007). "Validating agent-based marketing models through conjoint analysis." *J Business Research*. https://www.sciencedirect.com/science/article/abs/pii/S0148296307000410
18. ZIO Analytics TWINS platform. https://www.zio-analytics.com/
19. Ario Twin Persona. http://www.ariodata.com/use-cases/twin-persona.html
20. CDRC Digital Twin of Retail Loyalty Scheme. https://www.cdrc.ac.uk/case-study-developing-a-digital-twin-of-a-retail-loyalty-scheme/
21. Vanderlynden, J. et al. (2024). "Simulation of Consumers Behavior Facing Discounts and Promotions." https://inria.hal.science/hal-04587812/document
22. J Revenue & Pricing Management (2024). "An analysis of retail promotional pricing effectiveness using agent-based modeling." https://link.springer.com/article/10.1057/s41272-024-00512-7
23. Mesa ABM framework. JOSS paper. https://www.theoj.org/joss-papers/joss.07668/10.21105.joss.07668.pdf
24. Repast Simphony. North & Macal (2013). https://casmodeling.springeropen.com/articles/10.1186/2194-3206-1-3
25. Wilensky, U. & Rand, W. (2015). *An Introduction to Agent-Based Modeling*. MIT Press.
