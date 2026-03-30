"""Linear trend forecasting for financial metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class ForecastResult:
    """Linear trend forecast for a single metric."""

    metric: str
    display_name: str
    historical_years: list[int]
    historical_values: list[float]
    forecast_years: list[int]
    forecast_values: list[float]
    slope: float  # per year
    r_squared: float
    trend_direction: str  # "improving", "declining", "flat"
    confidence_note: str


def _trend_direction(slope: float, scale: float) -> str:
    if scale == 0:
        return "flat"
    rel = slope / abs(scale)
    if rel > 0.02:
        return "improving"
    if rel < -0.02:
        return "declining"
    return "flat"


def forecast_metric(
    years: list[int],
    values: list[float],
    metric: str,
    display_name: str,
    horizon: int = 3,
) -> ForecastResult | None:
    """Fit a linear trend and project *horizon* years ahead.

    Returns ``None`` if fewer than 2 non-null data points are available.
    """
    clean = [
        (y, v)
        for y, v in zip(years, values, strict=False)
        if v is not None and not np.isnan(v)
    ]
    if len(clean) < 2:
        return None

    xs = np.array([c[0] for c in clean], dtype=float)
    ys = np.array([c[1] for c in clean], dtype=float)

    slope, intercept, r_value, _p, _se = stats.linregress(xs, ys)
    r_squared = r_value**2

    last_year = round(xs[-1])
    forecast_years = list(range(last_year + 1, last_year + horizon + 1))
    forecast_values = [float(slope * y + intercept) for y in forecast_years]

    n_obs = len(clean)
    if n_obs < 3:
        confidence_note = (
            f"Low confidence: only {n_obs} data point(s) -- treat as indicative only."
        )
    elif r_squared < 0.5:
        confidence_note = f"Moderate confidence: R^2={r_squared:.2f} -- trend is noisy."
    else:
        confidence_note = f"Good fit: R^2={r_squared:.2f}."

    return ForecastResult(
        metric=metric,
        display_name=display_name,
        historical_years=[round(y) for y in xs],
        historical_values=ys.tolist(),
        forecast_years=forecast_years,
        forecast_values=forecast_values,
        slope=float(slope),
        r_squared=r_squared,
        trend_direction=_trend_direction(slope, float(np.mean(np.abs(ys)))),
        confidence_note=confidence_note,
    )
