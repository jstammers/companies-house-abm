import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Firm Agent Explorer

        This notebook lets you interactively explore the **Firm** agent from the
        Companies House ABM.  Firms are the core productive agents: they hold a
        balance sheet, set prices, hire workers, produce goods and make investment
        decisions.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt
    import numpy as np

    from companies_house_abm.abm.agents.firm import Firm
    from companies_house_abm.abm.config import FirmBehaviorConfig

    mo.md("## 1. Create a Single Firm")
    return FirmBehaviorConfig, Firm, np, plt


@app.cell
def _(mo):
    markup_slider = mo.ui.slider(
        0.01, 0.50, value=0.15, step=0.01, label="Price markup"
    )
    employees_slider = mo.ui.slider(1, 200, value=20, step=1, label="Employees")
    turnover_slider = mo.ui.slider(
        10_000, 1_000_000, value=200_000, step=10_000, label="Turnover (£)"
    )
    capital_slider = mo.ui.slider(
        10_000, 500_000, value=100_000, step=10_000, label="Capital (£)"
    )
    mo.md(
        f"""
        ### Firm Parameters

        {markup_slider}
        {employees_slider}
        {turnover_slider}
        {capital_slider}
        """
    )
    return capital_slider, employees_slider, markup_slider, turnover_slider


@app.cell
def _(
    Firm,
    FirmBehaviorConfig,
    capital_slider,
    employees_slider,
    markup_slider,
    mo,
    turnover_slider,
):
    behavior = FirmBehaviorConfig(price_markup=markup_slider.value)
    firm = Firm(
        agent_id="demo_firm",
        sector="manufacturing",
        employees=employees_slider.value,
        wage_bill=employees_slider.value * 8_750,
        turnover=float(turnover_slider.value),
        capital=float(capital_slider.value),
        cash=50_000.0,
        equity=float(capital_slider.value) + 50_000.0,
        behavior=behavior,
    )
    state = firm.get_state()
    mo.md(
        f"""
        ### Initial State

        | Attribute | Value |
        |-----------|-------|
        | Sector | {state["sector"]} |
        | Employees | {state["employees"]} |
        | Turnover | £{state["turnover"]:,.0f} |
        | Capital | £{state["capital"]:,.0f} |
        | Cash | £{state["cash"]:,.0f} |
        | Equity | £{state["equity"]:,.0f} |
        | Price | {state["price"]:.2f} |
        | Markup | {state["markup"]:.2%} |
        """
    )
    return behavior, firm, state


@app.cell
def _(mo):
    mo.md("## 2. Simulate Multiple Periods")
    return ()


@app.cell
def _(mo):
    n_periods_slider = mo.ui.slider(5, 100, value=30, step=5, label="Number of periods")
    mo.md(f"{n_periods_slider}")
    return (n_periods_slider,)


@app.cell
def _(
    Firm,
    FirmBehaviorConfig,
    capital_slider,
    employees_slider,
    markup_slider,
    n_periods_slider,
    np,
    plt,
    turnover_slider,
):
    _behavior = FirmBehaviorConfig(price_markup=markup_slider.value)
    _firm = Firm(
        agent_id="sim_firm",
        sector="manufacturing",
        employees=employees_slider.value,
        wage_bill=employees_slider.value * 8_750,
        turnover=float(turnover_slider.value),
        capital=float(capital_slider.value),
        cash=50_000.0,
        equity=float(capital_slider.value) + 50_000.0,
        behavior=_behavior,
    )

    history: dict[str, list[float]] = {
        "turnover": [],
        "profit": [],
        "inventory": [],
        "price": [],
        "cash": [],
        "equity": [],
    }

    for _t in range(n_periods_slider.value):
        _firm.step()
        for key in history:
            history[key].append(getattr(_firm, key))

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.suptitle("Firm Dynamics Over Time", fontsize=14)
    periods = np.arange(1, n_periods_slider.value + 1)

    for ax, (label, values) in zip(axes.flat, history.items(), strict=True):
        ax.plot(periods, values, linewidth=1.5)
        ax.set_title(label.replace("_", " ").title())
        ax.set_xlabel("Period")
        ax.grid(alpha=0.3)

    fig.tight_layout()
    fig
    return axes, fig, history, periods


@app.cell
def _(mo):
    mo.md(
        """
        ## 3. Key Insights

        - **Turnover** depends on how much inventory the firm can sell at its
          posted price.
        - **Markup** is adapted in response to excess demand signals from the
          goods market — here the firm operates in isolation so the signal is
          flat.
        - **Inventory** accumulates when output exceeds sales.
        - **Cash** and **equity** track profitability over time.

        Connect this firm to a `GoodsMarket` and `LaborMarket` (see the
        *ecosystem* notebook) to see richer dynamics.
        """
    )
    return ()


if __name__ == "__main__":
    app.run()
