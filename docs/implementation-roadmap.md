# Implementation Roadmap

This document provides a concrete roadmap for implementing the agent-based model.

## Phase 1: Foundation (Months 1-3)

### Week 1-2: Setup and Basic Infrastructure

- [x] Create ABM module structure
- [x] Define configuration system
- [x] Implement base agent class
- [ ] Set up Mesa integration
- [ ] Create model class skeleton
- [ ] Implement basic scheduler

**Deliverable**: Empty model that can run but has no agents yet

### Week 3-4: Firm Agent - Data Loading

- [ ] Implement data loader for Companies House parquet files
- [ ] Create Firm agent class with attributes from data schema
- [ ] Implement firm initialization from real data
- [ ] Add firm sampling strategies (stratified by sector/size)
- [ ] Validate firm agent creation

**Deliverable**: Can load real firm data and create firm agents

### Week 5-6: Firm Agent - Basic Behavior

- [ ] Implement production decision (simple capacity-based rule)
- [ ] Implement pricing decision (markup pricing)
- [ ] Add inventory tracking
- [ ] Implement basic financial accounting (update balance sheet)
- [ ] Add firm exit condition (bankruptcy)

**Deliverable**: Firms that produce, price, and can go bankrupt

### Week 7-8: Simple Goods Market

- [ ] Implement basic goods market mechanism
- [ ] Firms post prices and quantities
- [ ] Implement demand side (exogenous for now)
- [ ] Match supply and demand
- [ ] Firms receive revenue and update cash

**Deliverable**: Firms interact through goods market

### Week 9-12: Testing and Validation

- [ ] Write unit tests for all components
- [ ] Validate firm behavior (sensible decisions)
- [ ] Run small simulation (1000 firms, 100 periods)
- [ ] Check stock-flow consistency
- [ ] Basic output visualization (GDP, production)
- [ ] Documentation of phase 1

**Deliverable**: Working prototype with firms and goods market

## Phase 2: Core Model (Months 4-6)

### Month 4: Household and Labor Market

- [ ] Implement Household agent class
- [ ] Initialize household population (calibrated to UK)
- [ ] Implement consumption decision
- [ ] Create labor market mechanism
- [ ] Job matching algorithm
- [ ] Wage determination
- [ ] Firms hire workers and pay wages

**Deliverable**: Households consume and work

### Month 5: Banking and Credit

- [ ] Implement Bank agent class
- [ ] Create bank-firm lending relationships
- [ ] Implement credit application and approval process
- [ ] Interest rate setting
- [ ] Loan repayment and default
- [ ] Bank balance sheet management

**Deliverable**: Credit market functioning

### Month 6: Policy Agents

- [ ] Implement Central Bank agent
- [ ] Taylor rule for interest rate policy
- [ ] Implement Government agent
- [ ] Taxation system (corporate, income)
- [ ] Government spending and transfers
- [ ] Unemployment benefits
- [ ] Stock-flow consistency validation across all sectors

**Deliverable**: Complete set of agent types

## Phase 3: Networks and Heterogeneity (Months 7-9)

### Month 7: Supply Chain Network

- [ ] Load ONS input-output tables
- [ ] Build sectoral input-output matrix
- [ ] Create firm-level supply chain network
- [ ] Implement input purchasing by firms
- [ ] Add production constraints (need inputs)
- [ ] Test supply chain shock propagation

**Deliverable**: Network-based production

### Month 8: Credit Network and Financial Fragility

- [ ] Build bank-firm credit network
- [ ] Implement preferential attachment dynamics
- [ ] Add credit rationing mechanism
- [ ] Implement Minsky fragility classification
- [ ] Track systemic risk indicators
- [ ] Implement bank failure and contagion

**Deliverable**: Financial network and systemic risk

### Month 9: Heterogeneity and Adaptation

- [ ] Add sector-specific parameters and behaviors
- [ ] Implement adaptive expectations (firms, households)
- [ ] Add learning mechanisms (firms adjust markups)
- [ ] Implement firm entry process
- [ ] Calibrate entry/exit dynamics
- [ ] Test structural change over time

**Deliverable**: Heterogeneous adaptive agents

## Phase 4: Validation and Analysis (Months 10-12)

### Month 10: Empirical Validation

- [ ] Collect UK validation targets (ONS, BoE data)
- [ ] Implement calibration algorithm (e.g., simulated method of moments)
- [ ] Calibrate model to match UK stylized facts
- [ ] Sensitivity analysis
- [ ] Document parameter choices and justifications

**Deliverable**: Calibrated model

### Month 11: Policy Experiments

- [ ] Implement policy shock scenarios
- [ ] Run monetary policy experiments (rate changes, QE)
- [ ] Run fiscal policy experiments (spending, tax changes)
- [ ] Macroprudential policy (capital requirements)
- [ ] Structural policies (sector support)
- [ ] Generate policy analysis reports

**Deliverable**: Policy analysis toolkit

### Month 12: Documentation and Release

- [ ] Complete API documentation
- [ ] Write user guide with examples
- [ ] Create tutorial notebooks
- [ ] Performance optimization
- [ ] Code review and refactoring
- [ ] Comprehensive test suite (>80% coverage)
- [ ] Release v1.0

**Deliverable**: Production-ready ABM

## Phase 5: Advanced Features (Optional, Months 13+)

### Advanced Features Backlog

- [ ] Port performance-critical components to Rust
- [ ] PyO3 bindings for Rust ABM core
- [ ] Regional dimension (model UK regions)
- [ ] International trade and exchange rates
- [ ] Housing market
- [ ] Innovation and R&D
- [ ] Detailed tax system (VAT, NICs, etc.)
- [ ] Climate/environmental dimension
- [ ] Distributional analysis tools
- [ ] Interactive web dashboard (Mesa server or Dash)

## Development Workflow

### Branch Strategy

- `main`: Stable releases
- `develop`: Integration branch
- `feature/agent-firms`: Feature branches for specific components

### Code Review

- All PRs require review
- Must pass CI (lint, type-check, tests)
- Test coverage must not decrease

### Testing Strategy

- Unit tests for individual agent behaviors
- Integration tests for market mechanisms
- System tests for full model runs
- Property-based tests for invariants (stock-flow consistency)
- Regression tests to prevent breaking changes

### Documentation

- Docstrings for all public APIs (Google style)
- Update docs/ for design changes
- Maintain CHANGELOG.md

## Milestones and Checkpoints

| Milestone | Target | Criteria |
|-----------|--------|----------|
| M1: Prototype | Month 3 | 1000 firms, goods market, runs 100 periods |
| M2: Core Model | Month 6 | All agent types, basic validation |
| M3: Networks | Month 9 | Supply chain + credit networks, heterogeneity |
| M4: Validated | Month 10 | Matches UK stylized facts |
| M5: Policy Ready | Month 11 | Policy experiments working |
| M6: Release | Month 12 | v1.0 release, full documentation |

## Resource Requirements

### Computational

- Development: Standard laptop (8GB RAM)
- Testing: Mid-range workstation (16GB RAM)
- Large-scale runs: HPC cluster or cloud (64GB+ RAM, multi-core)

### Data

- Companies House XBRL data: ~50GB (already available)
- ONS input-output tables: ~100MB
- ONS macroeconomic time series: ~50MB
- Bank of England statistics: ~20MB

### Personnel

- 1-2 developers (full-time equivalent)
- 1 economist (for calibration and validation)
- Access to domain experts (central banking, ABM modeling)

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Performance insufficient | Medium | High | Start with small scale, plan Rust port |
| Calibration fails | Medium | High | Use multiple calibration targets, sensitivity analysis |
| Data quality issues | Low | Medium | Extensive data validation, synthetic fallbacks |
| Complexity management | Medium | Medium | Modular design, comprehensive tests |
| Scope creep | High | Medium | Strict phasing, defer advanced features |

## Success Criteria

The model is successful if it:

1. **Runs reliably**: Can complete 400-period simulations without crashes
2. **Is calibrated**: Matches UK stylized facts (see validation targets in design doc)
3. **Is consistent**: Passes stock-flow consistency checks
4. **Is documented**: Full API docs and user guide
5. **Is tested**: >80% code coverage, all tests passing
6. **Is useful**: Can be used for policy experiments and analysis
7. **Is performant**: Can run 50k agents in reasonable time (<1 hour/100 periods)

## Next Steps

1. Set up Mesa framework integration
2. Implement model class and scheduler
3. Begin firm agent implementation
4. Set up continuous integration for ABM tests

---

**Last Updated**: 2026-02-15  
**Status**: Planning Complete, Implementation Starting
