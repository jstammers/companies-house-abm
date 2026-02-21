# API Reference

::: companies_house_abm
    options:
      show_root_heading: true
      show_source: true
      members_order: source

## CLI Module

::: companies_house_abm.cli
    options:
      show_root_heading: true
      show_source: true

## ABM Module

### Simulation

::: companies_house_abm.abm.model.Simulation
    options:
      show_root_heading: true
      show_source: true

### Configuration

::: companies_house_abm.abm.config.ModelConfig
    options:
      show_root_heading: true
      show_source: true

::: companies_house_abm.abm.config.load_config
    options:
      show_root_heading: true
      show_source: true

### Agents

::: companies_house_abm.abm.agents.firm.Firm
    options:
      show_root_heading: true
      show_source: true

::: companies_house_abm.abm.agents.household.Household
    options:
      show_root_heading: true
      show_source: true

::: companies_house_abm.abm.agents.bank.Bank
    options:
      show_root_heading: true
      show_source: true

::: companies_house_abm.abm.agents.central_bank.CentralBank
    options:
      show_root_heading: true
      show_source: true

::: companies_house_abm.abm.agents.government.Government
    options:
      show_root_heading: true
      show_source: true

## Data Sources

### Firm Distributions

::: companies_house_abm.data_sources.firm_distributions
    options:
      show_root_heading: true
      show_source: true
      members:
        - SIC_TO_SECTOR
        - FIRM_FIELD_MAP
        - CANDIDATE_DISTRIBUTIONS
        - FieldProfile
        - DataProfile
        - FittedDistribution
        - SectorYearParameters
        - FirmDistributionSummary
        - load_accounts
        - assign_sectors
        - map_sic_to_sector
        - profile_accounts
        - profile_field
        - fit_distribution
        - compute_sector_year_parameters
        - build_summary
        - save_parameters_yaml
        - save_parameters_json
        - run_profile_pipeline

### Markets

::: companies_house_abm.abm.markets.goods.GoodsMarket
    options:
      show_root_heading: true
      show_source: true

::: companies_house_abm.abm.markets.Labour.LabourMarket
    options:
      show_root_heading: true
      show_source: true

::: companies_house_abm.abm.markets.credit.CreditMarket
    options:
      show_root_heading: true
      show_source: true
