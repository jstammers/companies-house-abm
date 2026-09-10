"""Experiments for the financial-crash module's validation report.

Runs four scenarios against the standalone daily :class:`FinancialSimulation`
(``docs/financial-market-crash.md``, Phase 1) and writes a JSON summary of
real (not hand-picked) numbers used in the accompanying report:

1. ``baseline``       — long calm-regime run, for Tier 1 return stylised
                         facts (Cont 2001).
2. ``ldi_shock``       — a sharp fundamental shock to a subset of assets
                         ("gilts"), with and without procyclical haircuts
                         (the M2-off counterfactual), shaped after the 2022
                         UK LDI episode.
3. ``covid_shock``     — a broad common-factor shock across all assets, with
                         and without procyclical haircuts, shaped after the
                         March 2020 "dash for cash".
4. ``ai_concentration`` — an illustrative (not calibrated) scenario with few,
                          highly correlated, high-leverage-tail assets,
                          standing in for a market dominated by a handful of
                          AI-related mega-caps.

Usage::

    uv run python scripts/financial_crash_experiments.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_SRC_ROOTS = [
    "packages/companies-house-abm/src",
    "packages/uk-data/src",
    "packages/companies-house/src",
]
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _root in _SRC_ROOTS:
    sys.path.insert(0, str(_REPO_ROOT / _root))

from companies_house_abm.abm.config import (  # noqa: E402
    FinancialMarketConfig,
    InvestorConfig,
    MarginConfig,
    RiskyAssetConfig,
)
from companies_house_abm.abm.financial_model import FinancialSimulation  # noqa: E402
from companies_house_abm.reporting.financial_metrics import (  # noqa: E402
    max_drawdown,
    procyclicality,
    stylised_facts_report,
)

OUTPUT_PATH = _REPO_ROOT / "docs" / "financial-market-crash-results.json"


def run_baseline(days: int = 1500, seed: int = 42) -> dict:
    cfg = FinancialMarketConfig(
        days=days,
        seed=seed,
        assets=RiskyAssetConfig(count=8),
        investors=InvestorConfig(count=200),
    )
    sim = FinancialSimulation.from_config(cfg)
    result = sim.run(days)
    returns = result.return_series
    pooled_returns = returns.mean(axis=1)  # cross-asset average daily return
    report = stylised_facts_report(pooled_returns, max_lag=20)
    report["per_asset_std"] = returns.std(axis=0).tolist()
    report["total_defaults"] = int(sum(result.default_series))
    report["total_margin_calls"] = int(sum(r.n_margin_calls for r in result.records))
    report["leverage_mean"] = float(
        np.nanmean([x for x in result.leverage_series if np.isfinite(x)])
    )
    report["procyclicality_leverage_vs_price"] = procyclicality(
        np.array(result.leverage_series), result.price_paths.mean(axis=1)
    )
    return report


def run_shock_scenario(
    name: str,
    *,
    days: int,
    shock_day: int,
    shocked_asset_classes: tuple[str, ...] | None,
    shock_magnitude: float,
    seed: int = 7,
    n_assets: int = 8,
    n_investors: int = 200,
    target_leverage_mean: float = 3.5,
) -> dict:
    """Run the same shock day with procyclical haircuts on vs. off (M2)."""

    def _run(procyclical: bool) -> dict:
        cfg = FinancialMarketConfig(
            days=days,
            seed=seed,
            assets=RiskyAssetConfig(count=n_assets),
            investors=InvestorConfig(
                count=n_investors, target_leverage_mean=target_leverage_mean
            ),
            margin=MarginConfig(procyclical_haircuts=procyclical),
        )
        sim = FinancialSimulation.from_config(cfg)
        price_index = []
        leverage = []
        margin_calls = []
        defaults = []
        for day in range(days):
            if day == shock_day:
                for asset in sim.assets:
                    if (
                        shocked_asset_classes is None
                        or asset.asset_class in shocked_asset_classes
                    ):
                        asset.fundamental_value *= 1.0 - shock_magnitude
            sim.step()
            price_index.append(float(np.mean([a.price for a in sim.assets])))
            leverage.append(sim.latest_record.aggregate_leverage)
            margin_calls.append(sim.latest_record.n_margin_calls)
            defaults.append(sim.latest_record.n_defaults)

        price_index = np.array(price_index)
        pre_shock = price_index[:shock_day].mean()
        trough = price_index[shock_day:].min()
        trough_day = int(shock_day + np.argmin(price_index[shock_day:]))
        post_shock_window = slice(shock_day, min(shock_day + 40, days))
        baseline_window = slice(0, shock_day)
        return {
            "peak_to_trough_pct": float(trough / pre_shock - 1.0),
            "max_drawdown_pct": max_drawdown(price_index),
            "days_to_trough": trough_day - shock_day,
            "total_defaults": int(sum(defaults)),
            "total_margin_calls": int(sum(margin_calls)),
            "margin_calls_post_shock": int(sum(margin_calls[post_shock_window])),
            "margin_calls_pre_shock_rate_per_day": float(
                np.mean(margin_calls[baseline_window])
            )
            if shock_day > 0
            else 0.0,
            "min_dealer_capital": float("nan"),  # filled by caller if needed
        }

    on = _run(procyclical=True)
    off = _run(procyclical=False)
    amplification = (
        on["max_drawdown_pct"] / off["max_drawdown_pct"]
        if off["max_drawdown_pct"] != 0
        else float("nan")
    )
    return {
        "scenario": name,
        "shock_day": shock_day,
        "shock_magnitude": shock_magnitude,
        "shocked_asset_classes": shocked_asset_classes,
        "procyclical_haircuts_on": on,
        "procyclical_haircuts_off": off,
        "amplification_ratio": amplification,
    }


def run_ai_concentration_scenario(days: int = 750, seed: int = 99) -> dict:
    """Illustrative (not calibrated) scenario: a small number of highly
    correlated, high-leverage-tail assets standing in for a market dominated
    by a handful of mega-cap AI-related names."""
    cfg = FinancialMarketConfig(
        days=days,
        seed=seed,
        assets=RiskyAssetConfig(
            count=4,
            classes=("equity",),
            common_factor_share=0.9,
            fundamental_vol=0.015,
        ),
        investors=InvestorConfig(
            count=200,
            target_leverage_mean=3.5,
            target_leverage_std=2.0,  # fatter leverage tail (options/margin)
            portfolio_overlap=0.9,  # nearly everyone holds the same names
            basket_size=4,
        ),
    )
    sim = FinancialSimulation.from_config(cfg)
    result = sim.run(days)
    returns = result.return_series
    pooled_returns = returns.mean(axis=1)
    report = stylised_facts_report(pooled_returns, max_lag=20)
    report["cross_asset_return_correlation"] = float(
        np.mean(np.corrcoef(returns.T)[np.triu_indices(returns.shape[1], k=1)])
    )
    report["total_defaults"] = int(sum(result.default_series))
    report["total_margin_calls"] = int(sum(r.n_margin_calls for r in result.records))
    report["leverage_p90"] = float(
        np.nanpercentile([x for x in result.leverage_series if np.isfinite(x)], 90)
    )
    return report


def main() -> None:
    results = {}

    print("Running baseline (Tier 1 stylised facts)...")
    results["baseline"] = run_baseline()

    print("Running 2022-LDI-shaped scenario (gilt shock, M2 on/off)...")
    results["ldi_shock"] = run_shock_scenario(
        "ldi_shock",
        days=400,
        shock_day=150,
        shocked_asset_classes=("gilt",),
        shock_magnitude=0.12,
        target_leverage_mean=5.0,
    )

    print("Running March-2020-shaped scenario (broad shock, M2 on/off)...")
    results["covid_shock"] = run_shock_scenario(
        "covid_shock",
        days=400,
        shock_day=150,
        shocked_asset_classes=None,
        shock_magnitude=0.25,
        target_leverage_mean=3.5,
    )

    print("Running illustrative AI-concentration scenario...")
    results["ai_concentration"] = run_ai_concentration_scenario()

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, default=str))
    print(f"Wrote {OUTPUT_PATH}")
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
