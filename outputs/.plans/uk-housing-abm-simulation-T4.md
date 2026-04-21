# T4: ABM Calibration, Validation, Platform Engineering & Production Considerations

## Objective
Investigate calibration and validation methods for housing ABMs, suitable platforms/frameworks, and engineering considerations for a production-grade commercial product.

## Calibration Methods
- How are housing ABMs calibrated to real data (manual tuning, grid search, Bayesian estimation, surrogate-assisted)?
- What target moments/statistics are matched (price distributions, transaction volumes, LTV distributions, default rates)?
- Method of Simulated Moments (MSM) for ABMs
- Approximate Bayesian Computation (ABC) for ABM calibration
- Machine learning surrogate models for fast calibration
- Sensitivity analysis approaches (Sobol indices, Morris screening)

## Validation Approaches
- Out-of-sample forecasting tests
- Reproducing stylised facts (fat tails, autocorrelation, spatial correlation)
- Cross-validation against historical episodes (2008 GFC, COVID, 2022 rate rises)
- Comparison with VAR/DSGE benchmarks
- What validation standards exist for regulatory acceptance?

## ABM Platforms & Engineering
- **Mesa** (Python) — capabilities, performance limits, current state
- **MASON** (Java) — used in housing ABMs, scalability
- **FLAME / FLAME GPU** — HPC-scale ABMs
- **Agents.jl** (Julia) — performance advantages
- **Custom C++/Rust implementations** — when are they needed?
- How many agents are needed for realistic UK housing (27M households, ~1M transactions/year)?
- Spatial representation options (grid, GIS, network)
- Runtime considerations: can a scenario run complete in minutes for interactive use?

## Production/Commercial Considerations
- API design for scenario submission and result retrieval
- Visualization and reporting for non-technical users
- Uncertainty quantification (ensemble runs, confidence intervals)
- Model governance and explainability for regulated users
- Cloud deployment architecture
- Comparison with existing ABM commercial platforms (e.g., Simudyne)

## Questions to Answer
1. What is the state of the art in ABM calibration for housing models?
2. What validation evidence would regulators/banks need to trust an ABM?
3. What platform choice best balances development speed, performance, and maintainability?
4. What scale of simulation is needed and is real-time scenario analysis feasible?

## Output
Write findings to `outputs/.drafts/uk-housing-abm-simulation-research-T4.md` with full source citations and URLs. Use web search and paper search. Do NOT fetch PDF files directly.
