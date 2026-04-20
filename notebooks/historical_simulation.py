import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # UK Housing Market Historical Simulation (2013-2024)

        Drives the housing ABM with actual Bank Rate, mortgage rate, and income
        data, applying regulatory events (MMR, stamp duty changes, COVID measures)
        at their historical dates.  Compares simulated house prices against the
        actual UK HPI.

        Based on the methodology of Farmer (2025), Baptista et al. (2016), and
        Carro et al. (2022).
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt

    from companies_house_abm.abm.historical import HistoricalSimulation
    from companies_house_abm.abm.scenarios import build_uk_2013_2024

    mo.md("## Setup")
    return HistoricalSimulation, build_uk_2013_2024, plt


@app.cell
def _(mo):
    backward_weight = mo.ui.slider(
        0.3,
        0.9,
        value=0.65,
        step=0.05,
        label="Backward expectation weight",
    )
    search_intensity = mo.ui.slider(
        5,
        30,
        value=10,
        step=1,
        label="Search intensity",
    )
    seed = mo.ui.number(start=0, stop=9999, value=42, label="Random seed")
    mo.md(
        f"""
        ### Sensitivity Controls

        Adjust these to explore how behavioural parameters affect the fit to
        historical data.

        {backward_weight}
        {search_intensity}
        {seed}
        """
    )
    return backward_weight, search_intensity, seed


@app.cell
def _(
    HistoricalSimulation,
    backward_weight,
    build_uk_2013_2024,
    mo,
    search_intensity,
    seed,
):
    from dataclasses import replace

    from companies_house_abm.abm.config import (
        HousingMarketConfig,
        ModelConfig,
        SimulationConfig,
    )

    scenario = build_uk_2013_2024()

    config = ModelConfig(
        simulation=SimulationConfig(seed=int(seed.value)),
        housing_market=HousingMarketConfig(
            backward_expectation_weight=float(backward_weight.value),
            search_intensity=int(search_intensity.value),
        ),
    )

    mo.md("Running historical simulation...")
    hsim = HistoricalSimulation(scenario, base_config=config)
    result = hsim.run()
    mo.md(f"Simulation complete: **{len(result.records)} quarters**")
    return (
        HousingMarketConfig,
        ModelConfig,
        SimulationConfig,
        config,
        hsim,
        replace,
        result,
        scenario,
    )


@app.cell
def _(mo, result):
    mo.md(
        f"""
        ## Summary

        ```
        {result.summary()}
        ```
        """
    )
    return ()


@app.cell
def _(mo, plt, result, scenario):
    # House prices: simulated vs actual
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    quarters = list(range(len(result.records)))
    sim_prices = result.simulated_prices
    act_prices = result.actual_hpi[: len(quarters)]

    ax1.plot(quarters, act_prices, "b-", linewidth=2, label="Actual UK HPI")
    ax1.plot(
        quarters,
        sim_prices,
        "r--",
        linewidth=2,
        label="Simulated",
        alpha=0.8,
    )

    # Shade regulatory events
    for _event in scenario.regulatory_events:
        if _event.period < len(quarters):
            ax1.axvline(
                _event.period,
                color="grey",
                linestyle=":",
                alpha=0.4,
            )

    # X-axis labels (every 4 quarters = 1 year)
    tick_positions = list(range(0, len(quarters), 4))
    tick_labels = [
        result.quarter_labels[i] if i < len(result.quarter_labels) else ""
        for i in tick_positions
    ]
    ax1.set_xticks(tick_positions)
    ax1.set_xticklabels(tick_labels, rotation=45, ha="right")
    ax1.set_ylabel("Average House Price (GBP)")
    ax1.set_title("UK House Prices: Simulated vs Actual (2013-2024)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()

    mo.md("## House Price Trajectory")
    return act_prices, ax1, fig1, quarters, sim_prices, tick_labels, tick_positions


@app.cell
def _(fig1, mo):
    mo.output.replace(fig1)
    return ()


@app.cell
def _(mo, plt, result, scenario):
    # Input paths: Bank Rate and mortgage rate
    fig2, (ax2a, ax2b) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    n = len(result.records)

    # Bank Rate
    br = result.bank_rate_input[:n]
    mr = result.mortgage_rate_input[:n]
    ax2a.plot(
        range(n),
        [r * 100 for r in br],
        "b-",
        linewidth=2,
        label="Bank Rate",
    )
    ax2a.plot(
        range(n),
        [r * 100 for r in mr],
        "r-",
        linewidth=2,
        label="Mortgage Rate",
    )
    ax2a.set_ylabel("Rate (%)")
    ax2a.set_title("Interest Rates (exogenous inputs)")
    ax2a.legend()
    ax2a.grid(True, alpha=0.3)

    # Regulatory events
    for _event in scenario.regulatory_events:
        if _event.period < n:
            ax2a.axvline(_event.period, color="grey", linestyle=":", alpha=0.4)
            ax2b.axvline(_event.period, color="grey", linestyle=":", alpha=0.4)

    # Transactions
    sim_txns = [r.housing_transactions for r in result.records]
    ax2b.plot(range(n), sim_txns, "g-", linewidth=2, label="Simulated")
    ax2b.set_ylabel("Transactions per quarter")
    ax2b.set_title("Housing Transactions")
    ax2b.legend()
    ax2b.grid(True, alpha=0.3)

    tick_positions2 = list(range(0, n, 4))
    tick_labels2 = [
        result.quarter_labels[i] if i < len(result.quarter_labels) else ""
        for i in tick_positions2
    ]
    ax2b.set_xticks(tick_positions2)
    ax2b.set_xticklabels(tick_labels2, rotation=45, ha="right")
    fig2.tight_layout()

    mo.md("## Inputs & Transactions")
    return ax2a, ax2b, br, fig2, mr, n, sim_txns, tick_labels2, tick_positions2


@app.cell
def _(fig2, mo):
    mo.output.replace(fig2)
    return ()


@app.cell
def _(mo, plt, result):
    # Homeownership rate and foreclosures
    fig3, (ax3a, ax3b) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    periods = list(range(len(result.records)))

    ownership = [r.homeownership_rate * 100 for r in result.records]
    ax3a.plot(periods, ownership, "b-", linewidth=2)
    ax3a.axhline(64, color="grey", linestyle="--", alpha=0.5, label="Target (64%)")
    ax3a.set_ylabel("Homeownership Rate (%)")
    ax3a.set_title("Homeownership Rate")
    ax3a.legend()
    ax3a.grid(True, alpha=0.3)

    foreclosures = [r.foreclosures for r in result.records]
    ax3b.bar(periods, foreclosures, color="red", alpha=0.6)
    ax3b.set_ylabel("Foreclosures")
    ax3b.set_title("Foreclosures per Quarter")
    ax3b.grid(True, alpha=0.3)

    tick_pos3 = list(range(0, len(periods), 4))
    tick_lab3 = [
        result.quarter_labels[i] if i < len(result.quarter_labels) else ""
        for i in tick_pos3
    ]
    ax3b.set_xticks(tick_pos3)
    ax3b.set_xticklabels(tick_lab3, rotation=45, ha="right")
    fig3.tight_layout()

    mo.md("## Market Health")
    return ax3a, ax3b, fig3, foreclosures, ownership, periods, tick_lab3, tick_pos3


@app.cell
def _(fig3, mo):
    mo.output.replace(fig3)
    return ()


@app.cell
def _(mo, result, scenario):
    # Regulatory event timeline
    events_md = "## Regulatory Event Timeline\n\n| Period | Quarter | Description |\n|--------|---------|-------------|\n"
    for _event in scenario.regulatory_events:
        events_md += f"| {_event.period} | {_event.quarter} | {_event.description} |\n"

    events_md += f"\n**Price correlation**: {result.price_correlation():.3f}  \n"
    events_md += f"**Price RMSE**: £{result.price_rmse():,.0f}  \n"
    events_md += f"**Directional accuracy**: {result.directional_accuracy():.1%}  \n"

    mo.md(events_md)
    return (events_md,)


if __name__ == "__main__":
    app.run()
