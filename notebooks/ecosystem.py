import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # ABM Ecosystem Simulation

        This notebook runs the **full agent-based model** — firms, households,
        banks, central bank and government interacting through goods, labour
        and credit markets.  Use the sliders to change parameters and observe
        emergent macroeconomic dynamics.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt
    import numpy as np

    from companies_house_abm.abm.config import (
        FirmBehaviorConfig,
        FiscalRuleConfig,
        HouseholdBehaviorConfig,
        ModelConfig,
        SimulationConfig,
        TaylorRuleConfig,
    )
    from companies_house_abm.abm.model import Simulation

    mo.md("## 1. Configure the Simulation")
    return (
        FirmBehaviorConfig,
        FiscalRuleConfig,
        HouseholdBehaviorConfig,
        ModelConfig,
        Simulation,
        SimulationConfig,
        TaylorRuleConfig,
        np,
        plt,
    )


@app.cell
def _(mo):
    n_firms = mo.ui.slider(20, 200, value=50, step=10, label="Number of firms")
    n_hh = mo.ui.slider(50, 500, value=100, step=50, label="Number of households")
    n_periods_eco = mo.ui.slider(10, 100, value=40, step=10, label="Simulation periods")
    seed = mo.ui.slider(1, 100, value=42, step=1, label="Random seed")
    mo.md(
        f"""
        ### Population & Duration

        {n_firms}
        {n_hh}
        {n_periods_eco}
        {seed}
        """
    )
    return n_firms, n_hh, n_periods_eco, seed


@app.cell
def _(mo):
    markup_eco = mo.ui.slider(
        0.05, 0.40, value=0.15, step=0.05, label="Firm price markup"
    )
    mpc_eco = mo.ui.slider(0.5, 0.95, value=0.80, step=0.05, label="Household MPC")
    pi_target = mo.ui.slider(
        0.01, 0.05, value=0.02, step=0.005, label="Inflation target"
    )
    mo.md(
        f"""
        ### Behavioural Parameters

        {markup_eco}
        {mpc_eco}
        {pi_target}
        """
    )
    return markup_eco, mpc_eco, pi_target


@app.cell
def _(
    FirmBehaviorConfig,
    FiscalRuleConfig,
    HouseholdBehaviorConfig,
    ModelConfig,
    Simulation,
    SimulationConfig,
    TaylorRuleConfig,
    markup_eco,
    mo,
    mpc_eco,
    n_firms,
    n_hh,
    n_periods_eco,
    pi_target,
    seed,
):
    config = ModelConfig(
        simulation=SimulationConfig(
            periods=n_periods_eco.value,
            seed=seed.value,
        ),
        firm_behavior=FirmBehaviorConfig(price_markup=markup_eco.value),
        household_behavior=HouseholdBehaviorConfig(),
        taylor_rule=TaylorRuleConfig(inflation_target=pi_target.value),
        fiscal_rule=FiscalRuleConfig(),
    )
    # Override counts via the config objects
    config_dict = {
        "firms": config.firms,
        "households": config.households,
    }
    sim = Simulation(config)

    # Manually set desired counts before initializing
    sim.config = ModelConfig(
        simulation=SimulationConfig(
            periods=n_periods_eco.value,
            seed=seed.value,
        ),
        firms=config.firms,
        firm_behavior=FirmBehaviorConfig(price_markup=markup_eco.value),
        households=config.households,
        household_behavior=HouseholdBehaviorConfig(),
        banks=config.banks,
        taylor_rule=TaylorRuleConfig(inflation_target=pi_target.value),
        fiscal_rule=FiscalRuleConfig(),
    )
    sim._rng = __import__("numpy").random.default_rng(seed.value)
    sim.central_bank = __import__(
        "companies_house_abm.abm.agents.central_bank", fromlist=["CentralBank"]
    ).CentralBank(taylor_rule=TaylorRuleConfig(inflation_target=pi_target.value))

    sim.initialize_agents()

    # Trim to requested sizes
    sim.firms = sim.firms[: n_firms.value]
    sim.households = sim.households[: n_hh.value]

    # Update MPC for households
    for _h in sim.households:
        _h.mpc = mpc_eco.value

    # Rewire markets
    sim.goods_market.set_agents(sim.firms, sim.households, sim.government)
    sim.labor_market.set_agents(sim.firms, sim.households, sim._rng)
    sim.credit_market.set_agents(sim.firms, sim.banks)

    result = sim.run(periods=n_periods_eco.value)
    mo.md(
        f"""
        ## 2. Results

        Ran **{n_periods_eco.value}** periods with **{n_firms.value}** firms
        and **{n_hh.value}** households.
        """
    )
    return config, config_dict, result, sim


@app.cell
def _(np, plt, result):
    records = result.records
    periods_arr = np.arange(1, len(records) + 1)

    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle("Macroeconomic Dynamics", fontsize=14)

    # GDP
    axes[0, 0].plot(periods_arr, [r.gdp for r in records])
    axes[0, 0].set_title("GDP")
    axes[0, 0].grid(alpha=0.3)

    # Inflation
    axes[0, 1].plot(periods_arr, [r.inflation * 100 for r in records])
    axes[0, 1].set_title("Inflation (%)")
    axes[0, 1].grid(alpha=0.3)

    # Unemployment
    axes[1, 0].plot(
        periods_arr, [r.unemployment_rate * 100 for r in records], color="red"
    )
    axes[1, 0].set_title("Unemployment Rate (%)")
    axes[1, 0].grid(alpha=0.3)

    # Policy rate
    axes[1, 1].plot(periods_arr, [r.policy_rate * 100 for r in records], color="green")
    axes[1, 1].set_title("Policy Rate (%)")
    axes[1, 1].grid(alpha=0.3)

    # Government deficit
    axes[2, 0].bar(
        periods_arr,
        [r.government_deficit for r in records],
        color=[
            "green" if d > 0 else "red" for d in [r.government_deficit for r in records]
        ],
        alpha=0.7,
    )
    axes[2, 0].set_title("Government Deficit (+) / Surplus (-)")
    axes[2, 0].grid(alpha=0.3)

    # Employment
    axes[2, 1].plot(periods_arr, [r.total_employment for r in records], color="teal")
    axes[2, 1].set_title("Total Employment")
    axes[2, 1].grid(alpha=0.3)

    fig.tight_layout()
    fig
    return axes, fig, periods_arr, records


@app.cell
def _(mo):
    mo.md("## 3. Firm-Level Distributions")
    return ()


@app.cell
def _(plt, sim):
    active = [f for f in sim.firms if not f.bankrupt]

    fig3, axes3 = plt.subplots(1, 3, figsize=(14, 4))

    turnovers = [f.turnover for f in active if f.turnover > 0]
    if turnovers:
        axes3[0].hist(turnovers, bins=30, edgecolor="black", alpha=0.7)
    axes3[0].set_title("Turnover Distribution")
    axes3[0].set_xlabel("Turnover (£)")

    profits = [f.profit for f in active]
    if profits:
        axes3[1].hist(profits, bins=30, edgecolor="black", alpha=0.7, color="green")
    axes3[1].set_title("Profit Distribution")
    axes3[1].set_xlabel("Profit (£)")

    employees = [f.employees for f in active if f.employees > 0]
    if employees:
        axes3[2].hist(employees, bins=20, edgecolor="black", alpha=0.7, color="orange")
    axes3[2].set_title("Employment Distribution")
    axes3[2].set_xlabel("Employees")

    fig3.suptitle("Firm-Level Heterogeneity (Final Period)", fontsize=14)
    fig3.tight_layout()
    fig3
    return active, axes3, employees, fig3, profits, turnovers


@app.cell
def _(mo, result, sim):
    bankrupt_count = sum(1 for f in sim.firms if f.bankrupt)
    final = result.records[-1]
    mo.md(
        f"""
        ## 4. Summary Statistics

        | Metric | Value |
        |--------|-------|
        | Final GDP | £{final.gdp:,.0f} |
        | Final unemployment | {final.unemployment_rate:.1%} |
        | Final policy rate | {final.policy_rate:.2%} |
        | Government debt | £{final.government_debt:,.0f} |
        | Bankrupt firms | {bankrupt_count} / {len(sim.firms)} |
        | Total employment | {final.total_employment:,} |
        """
    )
    return bankrupt_count, final


if __name__ == "__main__":
    app.run()
