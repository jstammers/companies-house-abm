"""Margin/funding helpers for the financial-crash module (M2)."""

from __future__ import annotations

import numpy as np


def compute_haircuts(
    volatility: np.ndarray,
    var_multiplier: float,
    haircut_min: float,
    haircut_max: float,
    procyclical: bool = True,
) -> np.ndarray:
    """Lender-set haircuts from a VaR-style multiple of realised volatility.

    ``haircut = clip(var_multiplier * volatility, haircut_min, haircut_max)``
    (M2; Geanakoplos 2010; Brunnermeier & Pedersen 2009; CGFS 2010). When
    ``procyclical`` is False the haircut is pinned at ``haircut_min`` — the
    counterfactual used to test whether the amplifier is doing the work
    (docs/financial-market-crash.md §7, Tier 3).
    """
    if not procyclical:
        return np.full_like(volatility, haircut_min)
    return np.clip(var_multiplier * volatility, haircut_min, haircut_max)
