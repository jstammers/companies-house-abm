# Implementation Roadmap: UK Economy ABM

This document outlines the phased implementation strategy for building the Agent-Based Model of the UK Economy, from the current Python data pipeline to a full-scale Rust simulation engine with Python bindings.

## Current State (v0.1.0)

**Capabilities:**
- Companies House XBRL data ingestion (streaming and batch)
- Polars-based ETL pipeline
- Parquet output format
- CLI interface via Typer
- Basic data cleaning and deduplication

**Technology Stack:**
- Python 3.13+
- Polars for DataFrame operations
- stream-read-xbrl for data streaming
- uv for package management
- Ruff & ty for code quality

## Target Architecture

**Vision:** A high-performance ABM with:
- Rust core simulation engine (5M+ agents)
- Python bindings via PyO3/Maturin
- Researcher-friendly Jupyter notebook interface
- Real-time visualisation capabilities
- Distributed computation support (future)

## Implementation Phases

### Phase 1: Foundation & Data Pipeline Enhancement (Months 1–3)

**Status:** In Progress

**Goals:**
- ✅ Establish current data ingestion pipeline
- 🔲 Enhance Companies House data extraction
- 🔲 Add ONS data integration
- 🔲 Create firm initialisation dataset
- 🔲 Build synthetic household population generator

**Deliverables:**
1. **Enhanced data pipeline** (`src/companies_house_abm/data/`)
   - `companies_house.py`: Extended CH data extraction with SIC parsing, postcode → NUTS-2 mapping
   - `ons_io_tables.py`: ONS Supply-Use Tables parser
   - `ons_demographics.py`: Household population calibration
   - `boe_rates.py`: Bank of England historical rate data

2. **Firm initialisation dataset**
   - Combine CH BasicCompanyData + XBRL accounts
   - Impute missing financial variables (capital, revenue, employees)
   - Output: `firms_init.parquet` with ~5M active firms

3. **Household synthetic population**
   - Generate ~30M synthetic households calibrated to ONS income/wealth distributions
   - Output: `households_init.parquet`

4. **Documentation**
   - ✅ ABM architecture document
   - ✅ Model description (ODD+D protocol)
   - 🔲 Data processing guide
   - 🔲 Calibration methodology

**Dependencies:**
- `polars>=1.38.1` (existing)
- `stream-read-xbrl>=0.1.1` (existing)
- New: `requests`, `beautifulsoup4` (for ONS data scraping)

**Testing:**
- Unit tests for each data module
- Integration test: full pipeline from raw data → initialisation files
- Validation: check firm size distribution matches empirical power law

**Estimated Effort:** 3 person-months

---

### Phase 2: Python ABM Prototype (Months 4–6)

**Status:** Not Started

**Goals:**
- Build a working Python-based ABM (small scale: ~10K firms, ~50K households)
- Validate core mechanisms (production, consumption, markets)
- Establish baseline for Rust performance comparison

**Deliverables:**
1. **Agent classes** (`src/companies_house_abm/agents/`)
   - `base.py`: Abstract `Agent` base class
   - `firm.py`: `Firm` agent with production, pricing, labour demand
   - `household.py`: `Household` agent with consumption, labour supply
   - `bank.py`: `Bank` agent with credit supply
   - `central_bank.py`: `CentralBank` with Taylor rule
   - `government.py`: `Government` with fiscal policy

2. **Market mechanisms** (`src/companies_house_abm/markets/`)
   - `goods_market.py`: Consumer goods matching
   - `labour_market.py`: Job matching with search frictions
   - `credit_market.py`: Bank lending with screening

3. **Network module** (`src/companies_house_abm/network/`)
   - `supply_chain.py`: Input-output network using `networkx`
   - `spatial.py`: NUTS-2 regional structure

4. **Simulation engine** (`src/companies_house_abm/simulation.py`)
   - `Simulation` class: orchestrates monthly time steps
   - State management
   - Statistics collection

5. **Example notebook** (`notebooks/baseline_simulation.ipynb`)
   - Load initialisation data
   - Configure simulation (10K firms, 120 months)
   - Run and visualise results (GDP, unemployment, firm size distribution)

**Dependencies:**
- New: `networkx>=3.0` (network topology)
- New: `numpy>=1.24` (numerical operations)
- New: `matplotlib>=3.8`, `plotly>=5.18` (visualisation)

**Testing:**
- Unit tests for each agent type
- Market mechanism tests (matching, price clearing)
- End-to-end simulation test (10K firms, 12 months)
- Validation: check emergence of stylised facts (firm size distribution, growth rate distribution)

**Performance Target:**
- 10K firms, 50K households: <1 hour for 120 months on laptop

**Estimated Effort:** 6 person-months

---

### Phase 3: Rust Core Engine (Months 7–12)

**Status:** Not Started

**Goals:**
- Migrate core simulation to Rust for 100x speed improvement
- Scale to 5M firms, 30M households
- Maintain Python interface via PyO3

**Deliverables:**
1. **Rust workspace setup**
   ```
   rust/
   ├── core/          # Simulation engine library
   ├── pyo3_bindings/ # Python bindings
   └── cli/           # Optional Rust CLI (future)
   ```

2. **Core simulation** (`rust/core/src/`)
   - `agents/`: Rust structs for Firm, Household, Bank, etc.
   - `markets/`: Market clearing algorithms
   - `network/`: Supply chain using `petgraph`
   - `scheduler.rs`: Integration with `krabmaga` for parallel agent stepping
   - `state.rs`: `EconomyState` managing all agents and markets
   - `config.rs`: Simulation configuration (deserialized from JSON/TOML)

3. **krabmaga integration**
   - Implement `Agent` trait for Firm, Household, Bank
   - Use `krabmaga::engine::schedule::Schedule` for parallel execution
   - Exploit ECS-like data layout for cache efficiency

4. **PyO3 bindings** (`rust/pyo3_bindings/src/lib.rs`)
   - `#[pyclass] Simulation`: exposes `new()`, `step()`, `run()`, `get_state()`
   - Zero-copy data transfer via Apache Arrow (firm/household data → Polars DataFrames)
   - Python-side wrapper: `uk_econ_abm.Simulation`

5. **Maturin build**
   - `pyproject.toml` update: add `[build-system]` for Maturin
   - CI: build wheels for Linux/macOS/Windows × Python 3.10–3.13

6. **Migration guide**
   - Document differences between Python and Rust implementations
   - Benchmarks: show 100x speedup for 100K agents

**Dependencies (Rust):**
- `krabmaga = "0.3"` (ABM framework)
- `petgraph = "0.6"` (network graphs)
- `rand = "0.8"`, `rand_distr = "0.4"` (stochastic processes)
- `serde = { version = "1.0", features = ["derive"] }` (config serialization)
- `pyo3 = { version = "0.20", features = ["extension-module"] }` (Python bindings)
- `arrow2 = "0.18"` (zero-copy data transfer)

**Dependencies (Python):**
- `maturin>=1.0` (build tool)

**Testing:**
- Rust unit tests for all agent behaviours
- Property-based tests (using `proptest`) for market clearing
- Integration test: 100K agents, 120 months
- Validation: reproduce Python prototype results (within stochastic bounds)

**Performance Target:**
- 5M firms, 30M households: ~10 hours for 120 months on workstation (64 cores)

**Estimated Effort:** 12 person-months

---

### Phase 4: Calibration & Validation (Months 13–16)

**Status:** Not Started

**Goals:**
- Calibrate behavioural parameters to match UK macro time-series
- Validate against stylised facts
- Establish baseline scenario

**Deliverables:**
1. **Calibration pipeline** (`src/companies_house_abm/calibration/`)
   - `macro_targets.py`: Define target statistics (GDP growth mean/variance, inflation, unemployment)
   - `distance_metrics.py`: Distance functions for ABC
   - `optimizer.py`: Bayesian calibration using `pyabc`
   - Parallelised simulation runs (100+ parameter combinations)

2. **Validation suite** (`src/companies_house_abm/validation/`)
   - `stylised_facts.py`: Tests for firm size distribution, growth rates, Phillips curve, Beveridge curve
   - `historical_comparison.py`: Compare simulated vs. actual UK 2010–2025 time-series
   - `scenario_tests.py`: Out-of-sample tests (COVID-19 shock, Brexit)

3. **Baseline scenario**
   - Calibrated parameter file: `conf/base/parameters.toml`
   - Baseline run: 600 months (50 years), starting from 2025 initial conditions
   - Output: time-series of all macro variables, firm-level snapshots every 12 months

4. **Documentation**
   - Calibration report: parameter estimates, convergence diagnostics
   - Validation report: stylised fact reproduction, historical fit, out-of-sample tests

**Dependencies:**
- New: `pyabc>=0.12` (Approximate Bayesian Computation)
- New: `scipy>=1.11` (optimisation, statistical tests)
- New: `statsmodels>=0.14` (econometric validation)

**Testing:**
- Test calibration pipeline with dummy model
- Reproducibility test: same seed → same calibration results

**Performance Consideration:**
- ABC requires 1000+ simulation runs; use cluster/cloud (AWS Batch, Azure Batch) for parallelisation

**Estimated Effort:** 8 person-months (including compute time)

---

### Phase 5: Scenario Analysis & Policy Tools (Months 17–20)

**Status:** Not Started

**Goals:**
- Build scenario library
- Create policy analysis tools
- Develop interactive dashboard

**Deliverables:**
1. **Scenario library** (`src/companies_house_abm/scenarios/`)
   - `base.py`: Baseline (no shocks)
   - `rate_hike.py`: +200bp interest rate shock
   - `supply_chain_shock.py`: Remove 5% of firms in key sector
   - `fiscal_expansion.py`: £50bn infrastructure spend
   - `tax_reform.py`: Corporation tax ±5%
   - `pandemic.py`: Sector-specific demand collapse + furlough
   - `brexit.py`: Trade friction on import-dependent sectors
   - `industrial_policy.py`: Green sector subsidies

2. **Policy analysis tools** (`src/companies_house_abm/policy/`)
   - `multiplier_analysis.py`: Compute fiscal multipliers
   - `distributional_impact.py`: Analyse effects by income decile, region, sector
   - `counterfactual.py`: Compare scenario vs. baseline

3. **Interactive dashboard** (Streamlit or Dash)
   - Configure scenario parameters
   - Run simulation (or load pre-computed)
   - Visualise results: time-series, distributions, networks
   - Export reports

4. **Example notebooks**
   - `04_scenario_analysis.ipynb`: Run multiple scenarios, compare results
   - `05_policy_evaluation.ipynb`: Fiscal multiplier analysis
   - `06_distributional_effects.ipynb`: Inequality dynamics under different policies

**Dependencies:**
- New: `streamlit>=1.30` or `dash>=2.14` (dashboard)
- New: `jupyterlab>=4.0` (interactive notebooks)

**Testing:**
- Test each scenario runs without error
- Validate scenario outputs against known results (e.g., interest rate shock should reduce investment)

**Estimated Effort:** 6 person-months

---

### Phase 6: Advanced Features (Months 21+)

**Status:** Future Work

**Potential Extensions:**

1. **Heterogeneous expectations**
   - Replace adaptive expectations with hybrid models (some agents rational, some adaptive)
   - Survey-based expectation anchoring (BoE inflation expectations survey)

2. **Detailed financial sector**
   - Shadow banking
   - Interbank network contagion
   - Asset bubbles (housing, stock market)

3. **International trade**
   - Multi-country model (UK + EU + US + China)
   - Exchange rate dynamics
   - Global supply chains

4. **Climate/energy transition**
   - Green vs. brown sectors
   - Carbon tax scenarios
   - Renewable energy investment

5. **Distributed simulation**
   - Partition agents across multiple nodes (MPI)
   - Cloud-native deployment (Kubernetes)

6. **Machine learning integration**
   - RL-based firm strategies
   - Neural network emulator for fast scenario exploration

**Estimated Effort:** TBD (depends on specific features)

---

## Technology Roadmap

### Current (v0.1.0)
- Python-only
- Data ingestion and storage
- CLI tool

### Near-term (v0.2.0 - v0.5.0)
- Enhanced data pipeline (Phases 1–2)
- Python ABM prototype
- Initial calibration

### Medium-term (v1.0.0)
- Rust core engine (Phase 3)
- PyO3 bindings
- Production-ready ABM (5M firms)
- Baseline scenario calibrated

### Long-term (v2.0.0+)
- Advanced financial sector
- International trade
- Climate scenarios
- Distributed simulation

## Resource Requirements

### Personnel
- **Lead developer** (Rust + Python): 1 FTE for 24 months
- **Data scientist** (calibration, validation): 0.5 FTE for 12 months
- **Economics researcher** (model design, validation): 0.5 FTE for 18 months
- **DevOps engineer** (CI/CD, cloud deployment): 0.25 FTE for 6 months

### Compute
- **Development**: Workstation (32-core, 128GB RAM)
- **Calibration**: Cloud compute (AWS/Azure): ~500 core-hours for ABC
- **Production**: Cluster (1000+ cores) for large-scale runs or sensitivity analysis

### Data
- Companies House bulk data: Free (200GB compressed)
- ONS data: Free (10GB)
- Historical time-series: Free (Bank of England, ONS)
- FAME database (optional, for richer firm data): £5K/year licence

## Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Calibration fails to match macro data | High | Use multiple calibration targets; accept imperfect fit for emerging phenomena |
| Rust performance lower than expected | Medium | Profile early; optimise hot paths; consider GPU acceleration |
| Model too complex for interpretation | Medium | Build simple version first; add complexity incrementally |
| Data quality issues (CH, ONS) | Medium | Robust imputation; sensitivity analysis |
| Researcher adoption low (learning curve) | Medium | Invest in documentation, tutorials, workshops |
| Compute costs too high | Low | Start small; scale only when validated; use spot instances |

## Success Metrics

### Technical
- **Performance**: 5M firms, 120 months in <12 hours (on 64-core workstation)
- **Accuracy**: Reproduce 5+ stylised facts without tuning
- **Coverage**: 95%+ UK firms represented in initialisation data

### Scientific
- **Validation**: Historical GDP/inflation/unemployment within 1 std dev of actual
- **Publication**: 2+ peer-reviewed papers on model methodology and applications
- **Impact**: Used by Bank of England, HMT, or academic researchers for policy analysis

### Community
- **Adoption**: 10+ external users (researchers, policymakers) within 1 year of v1.0
- **Contributions**: 3+ external code contributions
- **Documentation**: 90%+ function coverage in API docs; 5+ tutorial notebooks

## Next Steps (Immediate)

1. **Review this roadmap** with stakeholders; refine priorities.
2. **Complete Phase 1** (data pipeline enhancement):
   - Implement ONS data parsers
   - Build firm initialisation dataset
   - Generate synthetic household population
3. **Set up project tracking**:
   - GitHub project board with roadmap phases
   - Monthly progress reviews
4. **Establish testing infrastructure**:
   - CI for Python unit tests
   - Integration test suite for data pipeline
5. **Community engagement**:
   - Create mailing list / Discord for interested researchers
   - Present roadmap at conferences (e.g., WEHIA, ACE)

## References

- Dawid, H., & Delli Gatti, D. (2018). Agent-based macroeconomics. *Handbook of computational economics*, 4, 63-156.
- Fagiolo, G., & Roventini, A. (2017). Macroeconomic policy in DSGE and agent-based models redux: New developments and challenges ahead. *Journal of Artificial Societies and Social Simulation*, 20(1).
- Poledna, S., Miess, M. G., Hommes, C., & Rabitsch, K. (2023). Economic forecasting with an agent-based model. *European Economic Review*, 151, 104306.
