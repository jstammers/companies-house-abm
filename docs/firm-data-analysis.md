# Firm Data Analysis

The firm data analysis pipeline profiles Companies House accounts data,
fits statistical distributions to key financial fields, and generates
per-sector, per-year parameters for initialising firm agents in the ABM.

## Overview

Companies House publishes annual accounts for millions of UK companies.
These filings contain balance-sheet and (for larger companies)
profit-and-loss data.  The `profile-firms` pipeline extracts the fields
relevant to the [`Firm`][companies_house_abm.abm.agents.firm.Firm] agent
and fits probability distributions so the simulation can draw
statistically representative samples.

### Data Flow

```
companies_house_accounts.parquet
        │
        ▼
  ┌──────────────┐
  │ Load & Clean │  Drop dormant, errors, date outliers
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │Assign Sectors│  SIC code lookup → 13-sector ABM taxonomy
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │   Profile    │  Null rates, outliers, summary stats
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Fit Dists   │  Per sector × financial year × field
  └──────┬───────┘
         │
         ▼
  firm_distribution_parameters.yml
```

## Field Mapping

The following Companies House fields map to `Firm` agent constructor
arguments:

| Firm attribute | Parquet column | Typical null % |
|----------------|----------------|---------------|
| `employees` | `average_number_employees_during_period` | ~60% |
| `turnover` | `turnover_gross_operating_revenue` | ~98% |
| `capital` | `tangible_fixed_assets` | ~47% |
| `cash` | `cash_bank_in_hand` | ~46% |
| `debt` | `creditors_due_within_one_year` + `creditors_due_after_one_year` | ~72–95% |
| `equity` | `shareholder_funds` | ~7% |

!!! note "P&L sparsity"
    Most small UK companies file abbreviated (micro-entity) accounts that
    omit turnover and cost breakdowns.  The `turnover` and `staff_costs`
    fields are only populated for ~1–3% of filings.  Distribution fits
    for these fields will therefore be based on the subset of larger
    companies that report full accounts.

## Sector Assignment

Sectors are assigned via **SIC 2007** (Standard Industrial
Classification) codes mapped to the 13-sector taxonomy used by the ABM
(see `FirmConfig.sectors`).

If a SIC code lookup file is provided (as a CSV or parquet with
`companies_house_registered_number` and `sic_code` columns), sectors are
joined.  Otherwise all firms default to `other_services`.

SIC codes can be obtained from the [Companies House bulk data
product](http://download.companieshouse.gov.uk/en_output.html).

## Distribution Fitting

For each (sector, financial year, field) group the pipeline tries five
candidate distributions:

1. **Log-normal** (`lognorm`) — typical for firm sizes and financial values
2. **Exponential** (`expon`)
3. **Gamma** (`gamma`)
4. **Normal** (`norm`)
5. **Pareto** (`pareto`) — power-law tail

The best fit is selected by **Akaike Information Criterion (AIC)**.
A Kolmogorov–Smirnov test is also reported for each fit.

Groups with fewer than 30 observations are skipped.

## CLI Usage

```bash
# Full dataset (may take several minutes)
companies_house_abm profile-firms \
    --parquet data/companies_house_accounts.parquet \
    --output data/firm_distribution_parameters.yml

# Fast: 1% sample
companies_house_abm profile-firms --sample 0.01

# With SIC code sector assignment
companies_house_abm profile-firms \
    --sic-file data/sic_codes.csv \
    --output data/firm_distribution_parameters.yml

# JSON output
companies_house_abm profile-firms --format json -o data/params.json
```

## Interactive Notebook

The `notebooks/firm_data_analysis.py` marimo notebook provides an
interactive version of the pipeline with visualisations:

```bash
marimo edit notebooks/firm_data_analysis.py
```

The notebook includes:

- **Data profiling** tables showing null rates and outlier counts
- **Sector distribution** stacked bar charts per financial year
- **Aggregate trend** line plots of median financials over time
- **Distribution fit** histograms with overlaid best-fit curves
- **Parameter export** to YAML

## Output Format

The generated YAML file has this structure:

```yaml
generated_at: '2025-01-15T12:00:00+00:00'
total_companies: 5000000
sectors:
  - agriculture
  - construction
  - ...
financial_years:
  - 2015
  - 2016
  - ...
parameters:
  - sector: manufacturing
    financial_year: 2020
    n_companies: 45000
    distributions:
      - field: employees
        distribution: lognorm
        params:
          s: 1.2
          loc: 0.0
          scale: 8.5
        aic: 125000.0
        ks_statistic: 0.03
        ks_pvalue: 0.45
        n_observations: 18000
      - field: equity
        distribution: norm
        params:
          loc: 50000.0
          scale: 120000.0
        aic: 280000.0
        ks_statistic: 0.05
        ks_pvalue: 0.12
        n_observations: 42000
```

## Python API

```python
from pathlib import Path
from companies_house_abm.data_sources.firm_distributions import (
    run_profile_pipeline,
    load_accounts,
    assign_sectors,
    profile_accounts,
    compute_sector_year_parameters,
    build_summary,
    save_parameters_yaml,
)

# High-level: run the full pipeline
summary = run_profile_pipeline(
    Path("data/companies_house_accounts.parquet"),
    sic_path=Path("data/sic_codes.csv"),
    output_path=Path("data/firm_distribution_parameters.yml"),
    sample_fraction=0.01,
)

# Low-level: step by step
lf = load_accounts(Path("data/companies_house_accounts.parquet"))
lf = assign_sectors(lf, Path("data/sic_codes.csv"))
df = lf.collect()

profile = profile_accounts(df)
params = compute_sector_year_parameters(df)
summary = build_summary(params, profile.total_companies)
save_parameters_yaml(summary, Path("data/firm_distribution_parameters.yml"))
```
