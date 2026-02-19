import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Household Agent Explorer

        This notebook lets you interactively explore the **Household** agent.
        Households supply labour, earn income, consume goods, and accumulate
        savings.  Their *marginal propensity to consume* (MPC) is a key
        parameter controlling aggregate demand.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt
    import numpy as np

    from companies_house_abm.abm.agents.household import Household
    from companies_house_abm.abm.config import HouseholdBehaviorConfig

    mo.md("## 1. Single Household")
    return Household, HouseholdBehaviorConfig, np, plt


@app.cell
def _(mo):
    income_slider = mo.ui.slider(
        0, 100_000, value=35_000, step=5_000, label="Annual income (£)"
    )
    wealth_slider = mo.ui.slider(
        0, 200_000, value=20_000, step=5_000, label="Initial wealth (£)"
    )
    mpc_slider = mo.ui.slider(
        0.1, 0.99, value=0.80, step=0.05, label="Marginal propensity to consume"
    )
    smoothing_slider = mo.ui.slider(
        0.0, 1.0, value=0.70, step=0.05, label="Consumption smoothing"
    )
    mo.md(
        f"""
        ### Parameters

        {income_slider}
        {wealth_slider}
        {mpc_slider}
        {smoothing_slider}
        """
    )
    return income_slider, mpc_slider, smoothing_slider, wealth_slider


@app.cell
def _(
    Household,
    HouseholdBehaviorConfig,
    income_slider,
    mo,
    mpc_slider,
    smoothing_slider,
    wealth_slider,
):
    _behavior = HouseholdBehaviorConfig(
        consumption_smoothing=smoothing_slider.value,
    )
    hh = Household(
        agent_id="demo_hh",
        income=income_slider.value / 4,
        wealth=float(wealth_slider.value),
        mpc=mpc_slider.value,
        employed=True,
        employer_id="firm_0",
        wage=income_slider.value / 4,
        behavior=_behavior,
    )
    state = hh.get_state()
    mo.md(
        f"""
        ### Initial State

        | Attribute | Value |
        |-----------|-------|
        | Quarterly income | £{state["income"]:,.0f} |
        | Wealth | £{state["wealth"]:,.0f} |
        | MPC | {state["mpc"]:.2f} |
        | Employed | {state["employed"]} |
        """
    )
    return hh, state


@app.cell
def _(mo):
    mo.md("## 2. Simulate Consumption & Saving Dynamics")
    return ()


@app.cell
def _(mo):
    n_periods = mo.ui.slider(5, 100, value=40, step=5, label="Number of periods")
    mo.md(f"{n_periods}")
    return (n_periods,)


@app.cell
def _(
    Household,
    HouseholdBehaviorConfig,
    income_slider,
    mpc_slider,
    n_periods,
    np,
    plt,
    smoothing_slider,
    wealth_slider,
):
    _beh = HouseholdBehaviorConfig(consumption_smoothing=smoothing_slider.value)
    _hh = Household(
        income=income_slider.value / 4,
        wealth=float(wealth_slider.value),
        mpc=mpc_slider.value,
        employed=True,
        wage=income_slider.value / 4,
        behavior=_beh,
    )

    hist: dict[str, list[float]] = {
        "income": [],
        "consumption": [],
        "savings": [],
        "wealth": [],
    }

    for _ in range(n_periods.value):
        _hh.step()
        for k in hist:
            hist[k].append(getattr(_hh, k))

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Household Dynamics", fontsize=14)
    periods = np.arange(1, n_periods.value + 1)

    for ax, (label, values) in zip(axes.flat, hist.items(), strict=True):
        ax.plot(periods, values, linewidth=1.5)
        ax.set_title(label.title())
        ax.set_xlabel("Period")
        ax.grid(alpha=0.3)

    fig.tight_layout()
    fig
    return axes, fig, hist, periods


@app.cell
def _(mo):
    mo.md(
        """
        ## 3. MPC and Wealth Distribution

        The distribution of MPCs across households shapes the aggregate
        consumption function and therefore the fiscal multiplier.
        """
    )
    return ()


@app.cell
def _(Household, HouseholdBehaviorConfig, np, plt, smoothing_slider):
    rng = np.random.default_rng(42)
    _n = 500
    _beh2 = HouseholdBehaviorConfig(consumption_smoothing=smoothing_slider.value)
    pop = [
        Household(
            income=float(rng.lognormal(np.log(8_750), 0.4)),
            wealth=float(rng.pareto(1.5) * 10_000),
            mpc=float(np.clip(rng.normal(0.8, 0.1), 0.1, 0.99)),
            employed=bool(rng.random() > 0.05),
            wage=float(rng.lognormal(np.log(8_750), 0.4)),
            behavior=_beh2,
        )
        for _ in range(_n)
    ]

    for _ in range(10):
        for h in pop:
            h.step()

    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.hist([h.wealth for h in pop], bins=30, edgecolor="black", alpha=0.7)
    ax1.set_title("Wealth Distribution (after 10 periods)")
    ax1.set_xlabel("Wealth (£)")

    ax2.scatter(
        [h.mpc for h in pop],
        [h.consumption for h in pop],
        alpha=0.4,
        s=10,
    )
    ax2.set_title("MPC vs Consumption")
    ax2.set_xlabel("MPC")
    ax2.set_ylabel("Consumption (£)")
    fig2.tight_layout()
    fig2
    return ax1, ax2, fig2, pop, rng


if __name__ == "__main__":
    app.run()
