import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Policy Agents: Central Bank & Government

        This notebook explores the **Central Bank** and **Government** agents.
        The central bank sets monetary policy via a Taylor rule; the government
        collects taxes, spends, and manages the deficit.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt
    import numpy as np

    from companies_house_abm.abm.agents.central_bank import CentralBank
    from companies_house_abm.abm.agents.government import Government
    from companies_house_abm.abm.config import (
        FiscalRuleConfig,
        TaylorRuleConfig,
        TransfersConfig,
    )

    mo.md("## 1. Taylor Rule Explorer")
    return (
        CentralBank,
        FiscalRuleConfig,
        Government,
        TaylorRuleConfig,
        TransfersConfig,
        np,
        plt,
    )


@app.cell
def _(mo):
    pi_coef = mo.ui.slider(1.0, 3.0, value=1.5, step=0.1, label="Inflation coefficient")
    y_coef = mo.ui.slider(0.0, 1.5, value=0.5, step=0.1, label="Output gap coefficient")
    smoothing = mo.ui.slider(
        0.0, 0.95, value=0.8, step=0.05, label="Interest rate smoothing"
    )
    mo.md(
        f"""
        ### Taylor Rule Parameters

        {pi_coef}
        {y_coef}
        {smoothing}
        """
    )
    return pi_coef, smoothing, y_coef


@app.cell
def _(CentralBank, TaylorRuleConfig, np, pi_coef, plt, smoothing, y_coef):
    cfg_taylor = TaylorRuleConfig(
        inflation_coefficient=pi_coef.value,
        output_gap_coefficient=y_coef.value,
        interest_rate_smoothing=smoothing.value,
    )

    # Simulate: inflation oscillates, output gap varies
    rng = np.random.default_rng(42)
    inflation_path = 0.02 + 0.01 * np.sin(np.linspace(0, 4 * np.pi, 80))
    inflation_path += rng.normal(0, 0.002, 80)
    output_gap_path = 0.005 * np.sin(np.linspace(0, 3 * np.pi, 80))

    cb = CentralBank(taylor_rule=cfg_taylor)
    rate_path = []

    for pi_val, yg in zip(inflation_path, output_gap_path, strict=True):
        cb.update_observations(float(pi_val), float(yg))
        cb.step()
        rate_path.append(cb.policy_rate)

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    periods_arr = np.arange(1, 81)

    axes[0].plot(periods_arr, inflation_path * 100, label="Inflation")
    axes[0].axhline(2.0, color="red", linestyle="--", alpha=0.5, label="Target")
    axes[0].set_ylabel("Inflation (%)")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(periods_arr, output_gap_path * 100, color="orange")
    axes[1].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[1].set_ylabel("Output gap (%)")
    axes[1].grid(alpha=0.3)

    axes[2].plot(periods_arr, [r * 100 for r in rate_path], color="green")
    axes[2].set_ylabel("Policy rate (%)")
    axes[2].set_xlabel("Period")
    axes[2].grid(alpha=0.3)

    fig.suptitle("Taylor Rule: Central Bank Response", fontsize=14)
    fig.tight_layout()
    fig
    return (
        axes,
        cb,
        cfg_taylor,
        fig,
        inflation_path,
        output_gap_path,
        periods_arr,
        rate_path,
        rng,
    )


@app.cell
def _(mo):
    mo.md("## 2. Government Fiscal Dynamics")
    return ()


@app.cell
def _(mo):
    spending_ratio = mo.ui.slider(
        0.30, 0.50, value=0.40, step=0.01, label="Spending / GDP"
    )
    corp_tax = mo.ui.slider(
        0.10, 0.30, value=0.19, step=0.01, label="Corporate tax rate"
    )
    income_tax = mo.ui.slider(
        0.10, 0.30, value=0.20, step=0.01, label="Income tax rate"
    )
    mo.md(
        f"""
        ### Fiscal Parameters

        {spending_ratio}
        {corp_tax}
        {income_tax}
        """
    )
    return corp_tax, income_tax, spending_ratio


@app.cell
def _(
    FiscalRuleConfig,
    Government,
    TransfersConfig,
    corp_tax,
    income_tax,
    np,
    plt,
    spending_ratio,
):
    fiscal = FiscalRuleConfig(
        spending_gdp_ratio=spending_ratio.value,
        tax_rate_corporate=corp_tax.value,
        tax_rate_income_base=income_tax.value,
    )
    transfers = TransfersConfig()
    gov = Government(fiscal_rule=fiscal, transfers=transfers)

    gdp_base = 1_000_000.0
    _rng2 = np.random.default_rng(99)
    _n_periods = 60

    revenue_hist: list[float] = []
    spending_hist: list[float] = []
    deficit_hist: list[float] = []
    debt_hist: list[float] = []

    for t in range(_n_periods):
        gov.begin_period()
        gdp = gdp_base * (1 + 0.005 * t + _rng2.normal(0, 0.02))
        gov.gdp_estimate = gdp

        gov.calculate_spending()

        corp_profits = gdp * 0.12
        gov.collect_corporate_tax(corp_profits)
        total_income = gdp * 0.55
        gov.collect_income_tax(total_income)

        gov.step()
        gov.end_period()

        revenue_hist.append(gov.tax_revenue)
        spending_hist.append(gov.expenditure + gov.transfer_spending)
        deficit_hist.append(gov.deficit)
        debt_hist.append(gov.debt)

    fig2, axes2 = plt.subplots(2, 2, figsize=(12, 8))
    periods2 = np.arange(1, _n_periods + 1)

    axes2[0, 0].plot(periods2, revenue_hist, label="Revenue")
    axes2[0, 0].plot(periods2, spending_hist, label="Spending")
    axes2[0, 0].legend()
    axes2[0, 0].set_title("Revenue vs Spending")
    axes2[0, 0].grid(alpha=0.3)

    axes2[0, 1].bar(
        periods2,
        deficit_hist,
        color=["green" if d > 0 else "red" for d in deficit_hist],
        alpha=0.7,
    )
    axes2[0, 1].axhline(0, color="black", linewidth=0.5)
    axes2[0, 1].set_title("Deficit (+) / Surplus (-)")
    axes2[0, 1].grid(alpha=0.3)

    axes2[1, 0].plot(periods2, debt_hist, color="darkred")
    axes2[1, 0].set_title("Government Debt")
    axes2[1, 0].grid(alpha=0.3)

    if gdp_base > 0:
        debt_gdp = [d / (gdp_base * (1 + 0.005 * t)) for t, d in enumerate(debt_hist)]
        axes2[1, 1].plot(periods2, debt_gdp, color="purple")
        axes2[1, 1].set_title("Debt / GDP Ratio")
        axes2[1, 1].grid(alpha=0.3)

    fig2.suptitle("Government Fiscal Dynamics", fontsize=14)
    fig2.tight_layout()
    fig2
    return (
        axes2,
        debt_hist,
        deficit_hist,
        fig2,
        fiscal,
        gdp_base,
        gov,
        periods2,
        revenue_hist,
        spending_hist,
        transfers,
    )


if __name__ == "__main__":
    app.run()
