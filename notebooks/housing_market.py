import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Housing Market Validation

        End-to-end simulation using the full `Simulation` orchestrator, validated against
        the six targets from the [housing market design document](../docs/housing-market.md).

        | Metric | Target |
        |--------|--------|
        | Homeownership rate | ~64% |
        | Average house price | ~£285,000 |
        | Price-to-income ratio | ~8.3x |
        | Average mortgage LTV | ~70% |
        | Months of supply (time to sell) | 3-4 months |
        | Gross rental yield | 4-5% |
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt
    import numpy as np

    from companies_house_abm.abm.config import (
        HousingMarketConfig,
        ModelConfig,
        MortgageConfig,
        PropertyConfig,
        SimulationConfig,
    )
    from companies_house_abm.abm.model import Simulation

    mo.md("## Configuration")
    return (
        HousingMarketConfig,
        ModelConfig,
        MortgageConfig,
        PropertyConfig,
        Simulation,
        SimulationConfig,
        np,
        plt,
    )


@app.cell
def _(mo):
    # Simulation controls
    n_periods = mo.ui.slider(
        12, 120, value=36, step=6, label="Periods (months/quarters)"
    )
    seed = mo.ui.number(start=0, stop=9999, value=42, label="Random seed")
    mo.md(
        f"""
        ### Simulation
        {n_periods}
        {seed}
        """
    )
    return n_periods, seed


@app.cell
def _(mo):
    # Housing stock controls
    avg_price_k = mo.ui.slider(
        150, 500, value=285, step=5, label="Average property price (£k)"
    )
    n_properties = mo.ui.slider(
        2000, 20000, value=12000, step=1000, label="Housing stock size"
    )
    mo.md(
        f"""
        ### Housing Stock
        {avg_price_k}
        {n_properties}
        """
    )
    return avg_price_k, n_properties


@app.cell
def _(mo):
    # Market mechanism controls
    search_intensity = mo.ui.slider(
        1, 30, value=10, step=1, label="Search intensity (properties visited per buyer)"
    )
    price_reduction = mo.ui.slider(
        0.01, 0.30, value=0.10, step=0.01, label="Price reduction rate per period"
    )
    rental_yield = mo.ui.slider(
        0.03, 0.08, value=0.045, step=0.005, label="Gross rental yield"
    )
    mo.md(
        f"""
        ### Market Mechanism
        {search_intensity}
        {price_reduction}
        {rental_yield}
        """
    )
    return price_reduction, rental_yield, search_intensity


@app.cell
def _(mo):
    # Mortgage policy controls
    max_ltv = mo.ui.slider(0.50, 1.00, value=0.90, step=0.05, label="Max LTV (FPC cap)")
    max_dti = mo.ui.slider(
        2.0, 7.0, value=4.5, step=0.25, label="Max DTI multiple (FPC cap)"
    )
    mo.md(
        f"""
        ### Mortgage Policy (FPC Toolkit)
        {max_ltv}
        {max_dti}
        """
    )
    return max_dti, max_ltv


@app.cell
def _(
    HousingMarketConfig,
    ModelConfig,
    MortgageConfig,
    PropertyConfig,
    Simulation,
    SimulationConfig,
    avg_price_k,
    max_dti,
    max_ltv,
    mo,
    n_periods,
    n_properties,
    price_reduction,
    rental_yield,
    search_intensity,
    seed,
):
    config = ModelConfig(
        simulation=SimulationConfig(
            periods=int(n_periods.value),
            seed=int(seed.value),
        ),
        properties=PropertyConfig(
            count=int(n_properties.value),
            average_price=float(avg_price_k.value) * 1_000.0,
        ),
        housing_market=HousingMarketConfig(
            search_intensity=int(search_intensity.value),
            price_reduction_rate=float(price_reduction.value),
            rental_yield=float(rental_yield.value),
        ),
        mortgage=MortgageConfig(
            max_ltv=float(max_ltv.value),
            max_dti=float(max_dti.value),
        ),
    )

    sim = Simulation(config)
    sim.initialize_agents()
    result = sim.run(periods=int(n_periods.value))

    n_records = len(result.records)
    n_mortgages = len(sim.mortgages)
    mo.md(
        f"**Simulation complete** — {n_records} periods, "
        f"{len(sim.households):,} households, "
        f"{len(sim.properties):,} properties, "
        f"{n_mortgages:,} active mortgages."
    )
    return config, n_mortgages, n_records, result, sim


@app.cell
def _(mo, result, sim):
    import statistics

    records = result.records
    final = records[-1]

    # --- Compute validation metrics ---

    # 1. Homeownership rate (final period)
    homeownership_pct = final.homeownership_rate * 100.0

    # 2. Average house price (mean over last quarter of simulation)
    tail = records[max(0, len(records) - 3) :]
    avg_price = statistics.mean(r.average_house_price for r in tail)

    # 3. Price-to-income ratio
    avg_annual_income = sim.config.households.income_mean
    price_to_income = avg_price / avg_annual_income

    # 4. Average mortgage LTV
    ltvs = [m.ltv_at_origination for m in sim.mortgages]
    avg_ltv_pct = (statistics.mean(ltvs) * 100.0) if ltvs else float("nan")

    # 5. Months of supply (listings / transactions, averaged over last quarter)
    def _months_supply(r):
        return (
            (r.housing_listings / r.housing_transactions)
            if r.housing_transactions > 0
            else float("nan")
        )

    supply_vals = [_months_supply(r) for r in tail if r.housing_transactions > 0]
    avg_months_supply = statistics.mean(supply_vals) if supply_vals else float("nan")

    # 6. Gross rental yield (configured value)
    gross_rental_yield_pct = sim.config.housing_market.rental_yield * 100.0

    # --- Scorecard ---
    def _check(value, lo, hi, fmt=".1f"):
        icon = "PASS" if lo <= value <= hi else "FAIL"
        return f"{value:{fmt}} [{icon}]"

    scorecard = mo.md(
        f"""
        ## Validation Scorecard

        | Metric | Value | Target | Status |
        |--------|-------|--------|--------|
        | Homeownership rate | {homeownership_pct:.1f}% | ~64% (60-68%) | {"PASS" if 60 <= homeownership_pct <= 68 else "FAIL"} |
        | Average house price | £{avg_price / 1_000:.0f}k | ~£285k (£250k-£320k) | {"PASS" if 250_000 <= avg_price <= 320_000 else "FAIL"} |
        | Price-to-income ratio | {price_to_income:.1f}x | ~8.3x (7-10x) | {"PASS" if 7.0 <= price_to_income <= 10.0 else "FAIL"} |
        | Average mortgage LTV | {avg_ltv_pct:.1f}% | ~70% (60-80%) | {"PASS" if 60 <= avg_ltv_pct <= 80 else "FAIL"} |
        | Months of supply | {avg_months_supply:.1f} | 3-4 months | {"PASS" if 3.0 <= avg_months_supply <= 4.0 else "FAIL"} |
        | Gross rental yield | {gross_rental_yield_pct:.1f}% | 4-5% | {"PASS" if 4.0 <= gross_rental_yield_pct <= 5.0 else "FAIL"} |
        """
    )
    scorecard
    return (
        avg_annual_income,
        avg_ltv_pct,
        avg_months_supply,
        avg_price,
        final,
        gross_rental_yield_pct,
        homeownership_pct,
        ltvs,
        price_to_income,
        records,
        scorecard,
        statistics,
        supply_vals,
        tail,
    )


@app.cell
def _(mo, plt, records):
    mo.md("## Time Series")

    periods = [r.period for r in records]
    avg_prices = [r.average_house_price for r in records]
    homeownership = [r.homeownership_rate * 100.0 for r in records]
    transactions = [r.housing_transactions for r in records]
    listings = [r.housing_listings for r in records]
    hpi = [r.house_price_inflation * 100.0 for r in records]
    months_supply = [
        (r.housing_listings / r.housing_transactions)
        if r.housing_transactions > 0
        else 0.0
        for r in records
    ]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle(
        "Housing Market Dynamics — Full Simulation", fontsize=14, fontweight="bold"
    )

    # Average house price
    axes[0, 0].plot(periods, avg_prices, color="steelblue", linewidth=2)
    axes[0, 0].axhline(
        285_000, color="red", linestyle="--", alpha=0.7, label="Target £285k"
    )
    axes[0, 0].set_title("Average House Price")
    axes[0, 0].set_xlabel("Period")
    axes[0, 0].set_ylabel("£")
    axes[0, 0].yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"£{x / 1000:.0f}k")
    )
    axes[0, 0].legend(fontsize=8)

    # Homeownership rate
    axes[0, 1].plot(periods, homeownership, color="green", linewidth=2)
    axes[0, 1].axhline(64, color="red", linestyle="--", alpha=0.7, label="Target 64%")
    axes[0, 1].set_title("Homeownership Rate")
    axes[0, 1].set_xlabel("Period")
    axes[0, 1].set_ylabel("%")
    axes[0, 1].set_ylim(0, 100)
    axes[0, 1].legend(fontsize=8)

    # House price inflation
    axes[0, 2].bar(
        periods,
        hpi,
        color=["green" if v >= 0 else "red" for v in hpi],
        alpha=0.7,
    )
    axes[0, 2].axhline(0, color="black", linewidth=0.8)
    axes[0, 2].set_title("House Price Inflation")
    axes[0, 2].set_xlabel("Period")
    axes[0, 2].set_ylabel("%")

    # Transactions
    axes[1, 0].bar(periods, transactions, color="coral", alpha=0.8)
    axes[1, 0].set_title("Transactions per Period")
    axes[1, 0].set_xlabel("Period")
    axes[1, 0].set_ylabel("Count")

    # Listings
    axes[1, 1].plot(periods, listings, color="darkorange", linewidth=2)
    axes[1, 1].set_title("Active Listings")
    axes[1, 1].set_xlabel("Period")
    axes[1, 1].set_ylabel("Count")

    # Months of supply
    axes[1, 2].plot(periods, months_supply, color="purple", linewidth=2)
    axes[1, 2].axhspan(3, 4, color="green", alpha=0.12, label="Target 3-4 months")
    axes[1, 2].set_title("Months of Supply")
    axes[1, 2].set_xlabel("Period")
    axes[1, 2].set_ylabel("Months")
    axes[1, 2].legend(fontsize=8)

    plt.tight_layout()
    mo.ui.matplotlib(plt.gca())
    return (
        avg_prices,
        fig,
        homeownership,
        hpi,
        listings,
        months_supply,
        periods,
        transactions,
    )


@app.cell
def _(avg_annual_income, avg_prices, mo, plt, records):
    mo.md("## Price-to-Income Ratio")

    pti_series = [p / avg_annual_income for p in avg_prices]
    periods2 = [r.period for r in records]

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(periods2, pti_series, color="steelblue", linewidth=2, label="P/I ratio")
    ax2.axhline(8.3, color="red", linestyle="--", alpha=0.7, label="Target 8.3x")
    ax2.axhspan(7.0, 10.0, color="green", alpha=0.08, label="Acceptable range 7-10x")
    ax2.set_title("Price-to-Income Ratio Over Time")
    ax2.set_xlabel("Period")
    ax2.set_ylabel("Ratio")
    ax2.legend()
    plt.tight_layout()
    mo.ui.matplotlib(plt.gca())
    return ax2, fig2, periods2, pti_series


@app.cell
def _(ltvs, mo, plt):
    mo.md("## Mortgage LTV Distribution")

    if ltvs:
        _fig3, ax3 = plt.subplots(figsize=(9, 4))
        ax3.hist(
            ltvs, bins=25, color="steelblue", alpha=0.8, edgecolor="white", density=True
        )
        ax3.axvline(
            0.70, color="green", linestyle="--", linewidth=2, label="Target avg 70%"
        )
        ax3.axvline(
            0.90, color="red", linestyle="--", linewidth=1.5, label="FPC LTV cap"
        )
        ax3.set_title(f"Loan-to-Value at Origination  (n={len(ltvs):,})")
        ax3.set_xlabel("LTV")
        ax3.set_ylabel("Density")
        ax3.legend()
        plt.tight_layout()
        mo.ui.matplotlib(plt.gca())
    else:
        mo.md("_No mortgages originated in this run._")
    return


@app.cell
def _(
    avg_ltv_pct,
    avg_months_supply,
    avg_price,
    gross_rental_yield_pct,
    homeownership_pct,
    mo,
    price_to_income,
):
    mo.md(
        f"""
        ## Summary

        | Metric | Simulated | Target | Band |
        |--------|-----------|--------|------|
        | Homeownership rate | **{homeownership_pct:.1f}%** | 64% | 60-68% |
        | Average house price | **£{avg_price / 1_000:.0f}k** | £285k | £250k-£320k |
        | Price-to-income | **{price_to_income:.1f}x** | 8.3x | 7-10x |
        | Avg mortgage LTV | **{avg_ltv_pct:.1f}%** | 70% | 60-80% |
        | Months of supply | **{avg_months_supply:.1f}** | 3-4 | 3-4 |
        | Gross rental yield | **{gross_rental_yield_pct:.1f}%** | 4.5% | 4-5% |
        """
    )
    return


if __name__ == "__main__":
    app.run()
