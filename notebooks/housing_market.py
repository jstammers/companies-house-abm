import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Housing Market Explorer

        This notebook explores the **HousingMarket** mechanism: a bilateral-matching
        market with aspiration-level pricing following Farmer (2025) and Baptista et al.
        (2016).

        Unlike goods or labour markets, the housing market does **not** clear to
        equilibrium.  Prices adjust sluggishly through aspiration-level adaptation,
        buyers search a limited number of listings, and supply-demand imbalances persist.

        The key actors are:
        - **Properties** - housing units with asking prices that fall each period they
          remain unsold.
        - **Households** - buyers (renters who want to purchase) and sellers (owners who
          want to move).
        - **Banks** - lenders that approve or reject mortgages based on LTV and DTI
          constraints.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import matplotlib.pyplot as plt
    import numpy as np

    from companies_house_abm.abm.agents.bank import Bank
    from companies_house_abm.abm.agents.household import Household
    from companies_house_abm.abm.assets.property import Property
    from companies_house_abm.abm.config import (
        BankConfig,
        HousingMarketConfig,
        MortgageConfig,
    )
    from companies_house_abm.abm.markets.housing import HousingMarket

    mo.md("## 1. Market Configuration")
    return (
        Bank,
        BankConfig,
        Household,
        HousingMarket,
        HousingMarketConfig,
        MortgageConfig,
        Property,
        np,
        plt,
    )


@app.cell
def _(mo):
    # --- Market mechanism parameters ---
    search_intensity = mo.ui.slider(
        1, 30, value=10, step=1, label="Search intensity (properties visited per buyer)"
    )
    price_reduction = mo.ui.slider(
        0.01, 0.30, value=0.10, step=0.01, label="Price reduction rate per period"
    )
    max_months = mo.ui.slider(
        2, 12, value=6, step=1, label="Max months listed before delist"
    )
    initial_markup = mo.ui.slider(
        0.00, 0.20, value=0.05, step=0.01, label="Initial asking price markup"
    )
    mo.md(
        f"""
        ### Market Mechanism Parameters

        {search_intensity}
        {price_reduction}
        {max_months}
        {initial_markup}
        """
    )
    return initial_markup, max_months, price_reduction, search_intensity


@app.cell
def _(mo):
    # --- Mortgage policy parameters ---
    max_ltv = mo.ui.slider(
        0.50, 1.00, value=0.90, step=0.05, label="Max LTV (loan-to-value)"
    )
    max_dti = mo.ui.slider(
        2.0, 7.0, value=4.5, step=0.25, label="Max DTI (debt-to-income multiple)"
    )
    mo.md(
        f"""
        ### Mortgage Policy Parameters (FPC toolkit)

        {max_ltv}
        {max_dti}
        """
    )
    return max_dti, max_ltv


@app.cell
def _(mo):
    # --- Population parameters ---
    n_properties = mo.ui.slider(
        20, 200, value=80, step=10, label="Number of properties"
    )
    n_buyers = mo.ui.slider(5, 80, value=30, step=5, label="Number of buyer households")
    listing_fraction = mo.ui.slider(
        0.05,
        0.50,
        value=0.20,
        step=0.05,
        label="Fraction of properties initially listed",
    )
    buyer_wealth_k = mo.ui.slider(
        10, 100, value=40, step=5, label="Mean buyer wealth (£k)"
    )
    buyer_wage_k = mo.ui.slider(
        1, 8, value=3, step=0.5, label="Mean buyer monthly wage (£k)"
    )
    mean_price_k = mo.ui.slider(
        100, 500, value=250, step=25, label="Mean property price (£k)"
    )
    mo.md(
        f"""
        ### Population Parameters

        {n_properties}
        {n_buyers}
        {listing_fraction}
        {buyer_wealth_k}
        {buyer_wage_k}
        {mean_price_k}
        """
    )
    return (
        buyer_wage_k,
        buyer_wealth_k,
        listing_fraction,
        mean_price_k,
        n_buyers,
        n_properties,
    )


@app.cell
def _(mo):
    # --- Simulation parameters ---
    n_periods = mo.ui.slider(
        10, 60, value=24, step=2, label="Simulation periods (months)"
    )
    seed = mo.ui.number(start=0, stop=999, value=42, label="Random seed")
    mo.md(
        f"""
        ### Simulation Parameters

        {n_periods}
        {seed}
        """
    )
    return n_periods, seed


@app.cell
def _(
    Bank,
    BankConfig,
    Household,
    HousingMarket,
    HousingMarketConfig,
    MortgageConfig,
    Property,
    buyer_wage_k,
    buyer_wealth_k,
    initial_markup,
    listing_fraction,
    max_dti,
    max_ltv,
    max_months,
    mean_price_k,
    mo,
    n_buyers,
    n_periods,
    n_properties,
    np,
    price_reduction,
    search_intensity,
    seed,
):
    rng = np.random.default_rng(int(seed.value))

    # Build config objects
    hm_config = HousingMarketConfig(
        search_intensity=int(search_intensity.value),
        price_reduction_rate=float(price_reduction.value),
        max_months_listed=int(max_months.value),
        initial_markup=float(initial_markup.value),
    )
    mc_config = MortgageConfig(
        max_ltv=float(max_ltv.value),
        max_dti=float(max_dti.value),
    )
    bank_config = BankConfig()

    # --- Create properties ---
    n_props = int(n_properties.value)
    mean_price = float(mean_price_k.value) * 1_000.0
    prices = rng.lognormal(mean=np.log(mean_price), sigma=0.35, size=n_props)
    n_listed = max(1, int(n_props * float(listing_fraction.value)))
    listed_mask = np.zeros(n_props, dtype=bool)
    listed_mask[:n_listed] = True
    rng.shuffle(listed_mask)

    properties: list[Property] = []
    for i, (price, on_mkt) in enumerate(zip(prices, listed_mask, strict=True)):
        p = Property(
            property_id=f"prop_{i}",
            market_value=float(price),
            on_market=bool(on_mkt),
            asking_price=float(price) * (1.0 + hm_config.initial_markup)
            if on_mkt
            else 0.0,
            quality=float(rng.uniform(0.2, 0.9)),
        )
        properties.append(p)

    # --- Create households (mix of buyers and owner-sellers) ---
    mean_wealth = float(buyer_wealth_k.value) * 1_000.0
    mean_wage = float(buyer_wage_k.value) * 1_000.0

    n_buy = int(n_buyers.value)
    households: list[Household] = []

    # Buyer households
    for _ in range(n_buy):
        wealth = float(max(1_000.0, rng.lognormal(np.log(mean_wealth), 0.8)))
        wage = float(max(500.0, rng.normal(mean_wage, mean_wage * 0.3)))
        hh = Household(income=wage * 12.0, wealth=wealth, mpc=0.8)
        hh.employed = True
        hh.wage = wage
        hh.tenure = "renter"
        hh.wants_to_buy = True
        hh.months_searching = 0
        households.append(hh)

    # Owner-seller households (one per listed property)
    for prop in properties:
        if prop.on_market:
            owner = Household(income=mean_wage * 12.0, wealth=50_000.0, mpc=0.7)
            owner.employed = True
            owner.wage = mean_wage
            owner.tenure = "owner_occupier"
            owner.property_id = prop.property_id
            prop.owner_id = owner.agent_id
            owner.wants_to_sell = True
            households.append(owner)

    # --- Create a single representative bank ---
    bank = Bank(
        capital=50_000_000.0,
        reserves=10_000_000.0,
        loans=200_000_000.0,
        deposits=180_000_000.0,
        config=bank_config,
        mortgage_config=mc_config,
    )
    bank.mortgage_rate = 0.045

    # --- Run simulation ---
    market = HousingMarket(config=hm_config)
    mortgages: list = []

    history: list[dict] = []
    for period in range(int(n_periods.value)):
        market.set_agents(properties, households, [bank], mortgages, rng=rng)
        market.set_period(period)
        state = market.clear()
        history.append({"period": period, **state})

    mo.md(
        f"**Simulation complete** — {len(history)} periods, {len(mortgages)} mortgages originated."
    )
    return (
        bank,
        bank_config,
        history,
        hm_config,
        households,
        market,
        mc_config,
        mortgages,
        n_buy,
        n_listed,
        n_props,
        period,
        properties,
        rng,
    )


@app.cell
def _(history, mo, plt):
    periods = [h["period"] for h in history]
    avg_prices = [h["average_price"] for h in history]
    transactions = [h["transactions"] for h in history]
    listings = [h["listings"] for h in history]
    homeownership = [h["homeownership_rate"] for h in history]
    months_supply = [h["months_supply"] for h in history]
    hpi = [h["house_price_inflation"] * 100 for h in history]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.suptitle("Housing Market Dynamics", fontsize=14, fontweight="bold")

    # Average price
    axes[0, 0].plot(periods, avg_prices, color="steelblue", linewidth=2)
    axes[0, 0].set_title("Average House Price")
    axes[0, 0].set_xlabel("Period (months)")
    axes[0, 0].set_ylabel("£")
    axes[0, 0].yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"£{x / 1000:.0f}k")
    )

    # Transactions per period
    axes[0, 1].bar(periods, transactions, color="coral", alpha=0.7)
    axes[0, 1].set_title("Transactions per Period")
    axes[0, 1].set_xlabel("Period (months)")
    axes[0, 1].set_ylabel("Count")

    # Listings
    axes[0, 2].plot(periods, listings, color="darkorange", linewidth=2)
    axes[0, 2].set_title("Active Listings")
    axes[0, 2].set_xlabel("Period (months)")
    axes[0, 2].set_ylabel("Count")

    # Homeownership rate
    axes[1, 0].plot(
        periods, [r * 100 for r in homeownership], color="green", linewidth=2
    )
    axes[1, 0].set_title("Homeownership Rate")
    axes[1, 0].set_xlabel("Period (months)")
    axes[1, 0].set_ylabel("%")
    axes[1, 0].set_ylim(0, 100)

    # Months of supply
    axes[1, 1].plot(periods, months_supply, color="purple", linewidth=2)
    axes[1, 1].axhline(
        6, color="red", linestyle="--", alpha=0.6, label="6-month benchmark"
    )
    axes[1, 1].set_title("Months of Supply")
    axes[1, 1].set_xlabel("Period (months)")
    axes[1, 1].set_ylabel("Months")
    axes[1, 1].legend()

    # House price inflation
    axes[1, 2].bar(
        periods,
        hpi,
        color=["green" if v >= 0 else "red" for v in hpi],
        alpha=0.7,
    )
    axes[1, 2].axhline(0, color="black", linewidth=0.8)
    axes[1, 2].set_title("Monthly House Price Inflation")
    axes[1, 2].set_xlabel("Period (months)")
    axes[1, 2].set_ylabel("%")

    plt.tight_layout()
    mo.pyplot(fig)
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
def _(history, mo, mortgages):
    total_tx = sum(h["transactions"] for h in history)
    total_lending = sum(h["total_mortgage_lending"] for h in history)
    final_ownership = history[-1]["homeownership_rate"] * 100 if history else 0.0
    final_price = history[-1]["average_price"] if history else 0.0
    final_supply = history[-1]["months_supply"] if history else 0.0

    mo.md(
        f"""
        ## 2. Summary Statistics

        | Metric | Value |
        |--------|-------|
        | Total transactions | {total_tx} |
        | Total mortgage lending | £{total_lending / 1_000_000:.1f}m |
        | Mortgages originated | {len(mortgages)} |
        | Final homeownership rate | {final_ownership:.1f}% |
        | Final average price | £{final_price / 1_000:.0f}k |
        | Final months of supply | {final_supply:.1f} |
        """
    )
    return final_ownership, final_price, final_supply, total_lending, total_tx


@app.cell
def _(mo, mortgages, plt):
    mo.md("## 3. Mortgage Book Analysis")

    if mortgages:
        ltvs = [m.ltv_at_origination for m in mortgages]
        dtis = [m.dti_at_origination for m in mortgages]
        principals = [m.principal for m in mortgages]

        fig2, axes2 = plt.subplots(1, 3, figsize=(14, 4))
        fig2.suptitle(
            "Originated Mortgage Characteristics", fontsize=13, fontweight="bold"
        )

        axes2[0].hist(ltvs, bins=20, color="steelblue", alpha=0.8, edgecolor="white")
        axes2[0].axvline(0.90, color="red", linestyle="--", label="LTV cap")
        axes2[0].set_title("Loan-to-Value Distribution")
        axes2[0].set_xlabel("LTV")
        axes2[0].set_ylabel("Count")
        axes2[0].legend()

        axes2[1].hist(dtis, bins=20, color="coral", alpha=0.8, edgecolor="white")
        axes2[1].axvline(4.5, color="red", linestyle="--", label="DTI cap")
        axes2[1].set_title("Debt-to-Income Distribution")
        axes2[1].set_xlabel("DTI multiple")
        axes2[1].set_ylabel("Count")
        axes2[1].legend()

        axes2[2].hist(
            [p / 1_000 for p in principals],
            bins=20,
            color="green",
            alpha=0.8,
            edgecolor="white",
        )
        axes2[2].set_title("Mortgage Size Distribution")
        axes2[2].set_xlabel("Principal (£k)")
        axes2[2].set_ylabel("Count")

        plt.tight_layout()
        mo.pyplot(fig2)
    else:
        mo.md("_No mortgages originated in this simulation run._")
    return


@app.cell
def _(mo, properties):
    mo.md("## 4. Property State at End of Simulation")

    n_sold = sum(1 for p in properties if not p.on_market and p.owner_id is not None)
    n_still_listed = sum(1 for p in properties if p.on_market)
    n_vacant = sum(1 for p in properties if not p.on_market and p.owner_id is None)
    sold_prices = [
        p.last_transaction_price for p in properties if p.last_transaction_period > 0
    ]
    avg_sold_price = sum(sold_prices) / len(sold_prices) if sold_prices else 0.0

    mo.md(
        f"""
        | Status | Count |
        |--------|-------|
        | Sold / owner-occupied | {n_sold} |
        | Still listed | {n_still_listed} |
        | Unlisted / vacant | {n_vacant} |
        | Average transaction price | £{avg_sold_price / 1_000:.0f}k |
        """
    )
    return avg_sold_price, n_sold, n_still_listed, n_vacant, sold_prices


@app.cell
def _(mo, plt, properties):
    sold_props = [p for p in properties if p.last_transaction_period > 0]
    unsold_props = [p for p in properties if p.last_transaction_period == 0]

    if sold_props or unsold_props:
        fig3, ax3 = plt.subplots(figsize=(9, 5))
        if sold_props:
            ax3.scatter(
                [p.quality for p in sold_props],
                [p.last_transaction_price / 1_000 for p in sold_props],
                color="steelblue",
                alpha=0.6,
                label=f"Sold ({len(sold_props)})",
                s=40,
            )
        if unsold_props:
            ax3.scatter(
                [p.quality for p in unsold_props],
                [p.market_value / 1_000 for p in unsold_props],
                color="lightcoral",
                alpha=0.4,
                marker="x",
                label=f"Unsold ({len(unsold_props)})",
                s=40,
            )
        ax3.set_title("Quality vs. Price (sold vs. unsold)")
        ax3.set_xlabel("Property quality score")
        ax3.set_ylabel("Price (£k)")
        ax3.legend()
        plt.tight_layout()
        mo.pyplot(fig3)
    else:
        mo.md("_No properties to plot._")
    return ax3, fig3, sold_props, unsold_props


@app.cell
def _(avg_prices, mo, plt):
    mo.md("## 5. Price Expectations & Momentum")

    if len(avg_prices) > 3:
        returns = [
            (avg_prices[i] / avg_prices[i - 1] - 1.0) * 100
            for i in range(1, len(avg_prices))
        ]
        window = min(6, len(returns) // 2)
        rolling_avg = [
            sum(returns[max(0, i - window) : i + 1]) / min(i + 1, window + 1)
            for i in range(len(returns))
        ]

        fig4, ax4 = plt.subplots(figsize=(10, 4))
        ax4.bar(
            range(len(returns)),
            returns,
            color=["green" if r >= 0 else "red" for r in returns],
            alpha=0.6,
            label="Monthly return",
        )
        ax4.plot(
            rolling_avg, color="navy", linewidth=2, label=f"{window}-period moving avg"
        )
        ax4.axhline(0, color="black", linewidth=0.8)
        ax4.set_title("Monthly House Price Returns")
        ax4.set_xlabel("Period")
        ax4.set_ylabel("Return (%)")
        ax4.legend()
        plt.tight_layout()
        mo.pyplot(fig4)
    else:
        mo.md("_Run more periods to see return dynamics._")
    return


if __name__ == "__main__":
    app.run()
