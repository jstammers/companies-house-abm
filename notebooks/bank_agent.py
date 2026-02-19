import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Bank Agent Explorer

        This notebook explores the **Bank** agent.  Banks accept deposits,
        extend loans, earn interest income, and must maintain regulatory
        capital ratios (Basel III style).
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt
    import numpy as np

    from companies_house_abm.abm.agents.bank import Bank
    from companies_house_abm.abm.config import BankBehaviorConfig, BankConfig

    mo.md("## 1. Bank Configuration")
    return Bank, BankBehaviorConfig, BankConfig, np, plt


@app.cell
def _(mo):
    capital_req = mo.ui.slider(
        0.04, 0.20, value=0.10, step=0.01, label="Capital requirement"
    )
    buffer = mo.ui.slider(0.00, 0.05, value=0.02, step=0.005, label="Capital buffer")
    markup = mo.ui.slider(
        0.005, 0.05, value=0.02, step=0.005, label="Base interest markup"
    )
    risk_sens = mo.ui.slider(
        0.01, 0.20, value=0.05, step=0.01, label="Risk premium sensitivity"
    )
    mo.md(
        f"""
        ### Regulatory & Pricing Parameters

        {capital_req}
        {buffer}
        {markup}
        {risk_sens}
        """
    )
    return buffer, capital_req, markup, risk_sens


@app.cell
def _(Bank, BankBehaviorConfig, BankConfig, buffer, capital_req, markup, mo, risk_sens):
    cfg = BankConfig(
        capital_requirement=capital_req.value,
        reserve_requirement=0.01,
    )
    beh = BankBehaviorConfig(
        base_interest_markup=markup.value,
        risk_premium_sensitivity=risk_sens.value,
        capital_buffer=buffer.value,
    )
    bank = Bank(
        agent_id="demo_bank",
        capital=1_000_000.0,
        reserves=100_000.0,
        loans=5_000_000.0,
        deposits=4_000_000.0,
        config=cfg,
        behavior=beh,
    )
    mo.md(
        f"""
        ### Bank State

        | Metric | Value |
        |--------|-------|
        | Capital | £{bank.capital:,.0f} |
        | Loans | £{bank.loans:,.0f} |
        | Deposits | £{bank.deposits:,.0f} |
        | Capital ratio | {bank.capital_ratio:.2%} |
        | Required ratio | {capital_req.value + buffer.value:.2%} |
        | Meets requirement | {bank.meets_capital_requirement} |
        | Reserve ratio | {bank.reserve_ratio:.2%} |
        """
    )
    return bank, beh, cfg


@app.cell
def _(mo):
    mo.md("## 2. Lending Decision")
    return ()


@app.cell
def _(bank, mo):
    bank.set_policy_rate(0.05)

    test_cases = [
        ("Low risk", 50_000, 100_000, 200_000),
        ("Medium risk", 100_000, 80_000, 150_000),
        ("High risk", 200_000, 50_000, 80_000),
        ("Very high risk", 300_000, 10_000, 20_000),
    ]

    rows = []
    for label, amount, equity, revenue in test_cases:
        approved = bank.evaluate_loan(amount, equity, revenue)
        rows.append(
            f"| {label} | £{amount:,} | £{equity:,} | £{revenue:,} | "
            f"{'Approved' if approved else 'Rejected'} |"
        )

    table = "\n".join(rows)
    mo.md(
        f"""
        ### Loan Evaluation (policy rate = 5%)

        | Scenario | Amount | Equity | Revenue | Decision |
        |----------|--------|--------|---------|----------|
        {table}

        Interest rate charged: **{bank.interest_rate:.2%}**
        """
    )
    return rows, table, test_cases


@app.cell
def _(mo):
    mo.md("## 3. NPL Impact on Lending Rate")
    return ()


@app.cell
def _(Bank, BankBehaviorConfig, BankConfig, capital_req, markup, np, plt, risk_sens):
    npl_fractions = np.linspace(0, 0.15, 50)
    rates = []

    for npl_frac in npl_fractions:
        _b = Bank(
            capital=1_000_000.0,
            loans=5_000_000.0,
            deposits=4_000_000.0,
            config=BankConfig(capital_requirement=capital_req.value),
            behavior=BankBehaviorConfig(
                base_interest_markup=markup.value,
                risk_premium_sensitivity=risk_sens.value,
            ),
        )
        _b.non_performing_loans = npl_frac * _b.loans
        _b.set_policy_rate(0.05)
        rates.append(_b.interest_rate)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(npl_fractions * 100, [r * 100 for r in rates], linewidth=2)
    ax.set_xlabel("NPL ratio (%)")
    ax.set_ylabel("Lending rate (%)")
    ax.set_title("How Non-Performing Loans Affect the Lending Rate")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig
    return ax, fig, npl_fractions, rates


if __name__ == "__main__":
    app.run()
