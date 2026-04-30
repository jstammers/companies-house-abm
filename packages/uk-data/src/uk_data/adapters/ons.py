"""ONS (Office for National Statistics) data fetcher.

Wraps the ONS API (https://api.ons.gov.uk/v1/) and selected static datasets
to provide UK macroeconomic and housing data for ABM calibration.

Datasets used
-------------
- **ABMI** - UK GDP at market prices (GBP million, seasonally adjusted,
  quarterly).
- **RPHQ** - UK households' disposable income (GBP million, seasonally
  adjusted, quarterly).
- **NRJS** - Household saving ratio (%), seasonally adjusted, quarterly.
- **MGSX** / **KAB9** - Labour Force Survey: unemployment rate and average
  weekly earnings.
- **HP7A** - House price to workplace-based earnings affordability ratio.
- **D7RA** - Index of Private Housing Rental Prices (monthly).
- **Supply and Use Tables** - ONS Input-Output supply and use tables
  (parsed into a coefficient matrix).

All data is Crown Copyright, reproduced under the Open Government Licence.
See https://www.ons.gov.uk/methodology/geography/licences for details.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

if TYPE_CHECKING:
    from uk_data.storage.raw import RawStore

from uk_data._http import get_json
from uk_data.adapters.base import BaseAdapter
from uk_data.adapters.ons_models import (
    Observation,
    ONSDatasetInfo,
    ONSDatasetVersionInfo,
    ONSObservation,
)
from uk_data.models import point_timeseries, series_from_observations
from uk_data.utils.http import retry
from uk_data.utils.timeseries import filter_observations_by_date_window

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ONS API root
# ---------------------------------------------------------------------------

_ONS_API = "https://api.beta.ons.gov.uk/v1"

# ---------------------------------------------------------------------------
# Dataset series IDs
# ---------------------------------------------------------------------------

# UK GDP at market prices (SA, GBP m, quarterly)
_GDP_SERIES = "ABMI"

# Households' & NPISH gross disposable income (SA, GBP m, quarterly)
_HOUSEHOLD_INCOME_SERIES = "RPHQ"

# HH & NPISH saving ratio (%, SA, quarterly)
_SAVINGS_RATIO_SERIES = "NRJS"

# Unemployment rate (%, SA, monthly)
_UNEMPLOYMENT_RATE_SERIES = "MGSX"

# Average weekly earnings (GBP, SA, monthly)
_AVERAGE_EARNINGS_SERIES = "KAB9"

# House price to workplace-based earnings affordability ratio (annual)
_AFFORDABILITY_SERIES = "HP7A"

# Index of Private Housing Rental Prices (monthly)
_RENTAL_INDEX_SERIES = "D7RA"

# ---------------------------------------------------------------------------
# Fallback values for housing statistics
# ---------------------------------------------------------------------------

# English Housing Survey 2023-24 tenure shares
_FALLBACK_TENURE: dict[str, float] = {
    "owner_occupier": 0.64,
    "private_renter": 0.19,
    "social_renter": 0.17,
}

# ONS affordability ratio (median house price / median workplace earnings)
_FALLBACK_AFFORDABILITY = 8.3

# Annual private rental price growth (ONS IPHRP, 2024)
_FALLBACK_RENTAL_GROWTH = 0.065

# ---------------------------------------------------------------------------
# Series → ONS Zebedee content URI mapping
#
# The ONS Zebedee reader API uses GET /v1/data?uri=<path> where <path> is
# the full content URI for the timeseries page on ons.gov.uk.  The old
# /v1/timeseries/{id}/dataset/{dataset}/data path pattern is no longer
# served (returns 404).
#
# URIs confirmed against the live API.  Series not listed here fall back to
# the _DEFAULT_URI_TEMPLATE which uses the GDP topic and ukea dataset —
# suitable for national-accounts series.
# ---------------------------------------------------------------------------

_SERIES_URI: dict[str, str] = {
    # National accounts (UK Economic Accounts / GDP topic)
    "ABMI": "/economy/grossdomesticproductgdp/timeseries/abmi/ukea",
    "RPHQ": "/economy/grossdomesticproductgdp/timeseries/rphq/ukea",
    "NRJS": "/economy/grossdomesticproductgdp/timeseries/nrjs/ukea",
    # Labour market (Labour Market Statistics bulletin)
    "MGSX": (
        "/employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms"
    ),
    "KAB9": (
        "/employmentandlabourmarket/peopleinwork"
        "/earningsandworkinghours/timeseries/kab9/lms"
    ),
    # GVA by industry (UK Economic Accounts) — confirmed working subset.
    # L2KL: Agriculture; L2N8: Construction; L2NC: Total Services;
    # L2NE: Wholesale & Retail Trade.  Other SIC-division series
    # (L2KP, L2ND, L2NF-L2NM) return 404 from the Zebedee API and are
    # therefore omitted.  These are consumed by the ABM's input-output
    # table builder (see companies_house_abm.data_sources.input_output).
    "L2KL": "/economy/grossdomesticproductgdp/timeseries/l2kl/ukea",
    "L2N8": "/economy/grossdomesticproductgdp/timeseries/l2n8/ukea",
    "L2NC": "/economy/grossdomesticproductgdp/timeseries/l2nc/ukea",
    "L2NE": "/economy/grossdomesticproductgdp/timeseries/l2ne/ukea",
    # HP7A (affordability ratio) and D7RA (rental index) are not
    # available via the Zebedee API; fetch_affordability_ratio and
    # fetch_rental_growth use their hardcoded fallback values.
}

_DEFAULT_URI_TEMPLATE = "/economy/grossdomesticproductgdp/timeseries/{sid}/ukea"

_SERIES_METADATA: dict[str, dict[str, str]] = {
    "ABMI": {
        "concept": "gdp",
        "name": "UK GDP at market prices",
        "frequency": "Q",
        "units": "GBP_M",
        "seasonal_adjustment": "SA",
    },
    "RPHQ": {
        "concept": "household_income",
        "name": "UK household disposable income",
        "frequency": "Q",
        "units": "GBP_M",
        "seasonal_adjustment": "SA",
    },
    "NRJS": {
        "concept": "savings_ratio",
        "name": "UK household savings ratio",
        "frequency": "Q",
        "units": "%",
        "seasonal_adjustment": "SA",
    },
    "MGSX": {
        "concept": "unemployment",
        "name": "UK unemployment rate",
        "frequency": "M",
        "units": "%",
        "seasonal_adjustment": "SA",
    },
    "KAB9": {
        "concept": "average_earnings",
        "name": "Average weekly earnings",
        "frequency": "M",
        "units": "GBP",
        "seasonal_adjustment": "SA",
    },
    "HP7A": {
        "concept": "affordability",
        "name": "House price affordability ratio",
        "frequency": "A",
        "units": "ratio",
        "seasonal_adjustment": "NSA",
    },
    "D7RA": {
        "concept": "rental_growth",
        "name": "Private rental growth",
        "frequency": "M",
        "units": "fraction",
        "seasonal_adjustment": "NSA",
    },
}


def _normalize_period_bound(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _fetch_timeseries(series_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch the latest *limit* observations for an ONS time series.

    Uses the ONS Zebedee reader API (``GET /v1/data?uri=<path>``).  Each
    series has a content URI registered in ``_SERIES_URI``; unknown series
    fall back to the GDP topic template.

    Args:
        series_id: ONS time-series identifier (e.g. ``"ABMI"``).
        limit: Maximum number of observations to return (most recent first).

    Returns:
        List of observation dicts with keys ``"date"`` (str) and
        ``"value"`` (str).
    """
    sid_upper = series_id.upper()
    content_uri = _SERIES_URI.get(
        sid_upper,
        _DEFAULT_URI_TEMPLATE.format(sid=series_id.lower()),
    )
    import urllib.parse

    url = f"{_ONS_API}/data?uri={urllib.parse.quote(content_uri, safe='/')}"
    try:
        data = retry(get_json, url)
    except Exception:
        logger.warning("ONS API unavailable for series %s, returning []", series_id)
        return []

    # The ONS API returns observations in frequency-keyed arrays:
    # "quarters" for quarterly series, "months" for monthly, "years" for annual.
    observations: list[dict[str, Any]] = (
        data.get("quarters")
        or data.get("months")
        or data.get("years")
        or data.get("observations")
        or []
    )
    return observations[-limit:] if len(observations) > limit else observations


def _latest_float(series_id: str) -> float | None:
    """Return the most recent numeric value for an ONS time series.

    Args:
        series_id: ONS time-series identifier.

    Returns:
        The latest observation as a float, or ``None`` if unavailable.
    """
    obs = _fetch_timeseries(series_id, limit=1)
    if not obs:
        return None
    try:
        return float(obs[-1]["value"])
    except (KeyError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Public fetch functions
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Housing statistics (private helpers — public interface in workflows/ons.py)
# ---------------------------------------------------------------------------


def _fetch_affordability_ratio() -> float:
    """Return the median house price to earnings affordability ratio."""
    try:
        obs = _fetch_timeseries(_AFFORDABILITY_SERIES, limit=1)
        if obs:
            value = float(obs[-1]["value"])
            if value > 0:
                logger.info("Fetched affordability ratio: %.1f", value)
                return value
    except Exception:
        logger.warning("ONS affordability series unavailable, using fallback")

    return _FALLBACK_AFFORDABILITY


def _fetch_rental_growth() -> float:
    """Return the annual private rental price growth rate."""
    try:
        obs = _fetch_timeseries(_RENTAL_INDEX_SERIES, limit=13)
        if len(obs) >= 13:
            latest = float(obs[-1]["value"])
            year_ago = float(obs[0]["value"])
            if year_ago > 0 and latest > 0:
                growth = (latest / year_ago) - 1.0
                logger.info("Fetched rental growth: %.1f%%", growth * 100)
                return growth
    except Exception:
        logger.warning("ONS rental index unavailable, using fallback")

    return _FALLBACK_RENTAL_GROWTH


class ONSAdapter(BaseAdapter):
    """Canonical adapter for Office for National Statistics data."""

    _source_name = "ons"

    def __init__(self, store: RawStore | None = None) -> None:
        super().__init__(store=store)
        self._datasets_cache: dict[
            tuple[int, int, str | None], list[ONSDatasetInfo]
        ] = {}

    def _build_dataset_url(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> str:
        base = f"{_ONS_API}/{path.lstrip('/')}"
        if not params:
            return base
        return f"{base}?{urlencode(params)}"

    @staticmethod
    def _coerce_limit(value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        msg = f"Invalid ONS limit value: {value!r}"
        raise ValueError(msg)

    @staticmethod
    def _coerce_date_bound(value: object) -> str | date | datetime | None:
        if value is None:
            return None
        if isinstance(value, (str, date, datetime)):
            return value
        msg = f"Invalid ONS date bound: {value!r}"
        raise ValueError(msg)

    @staticmethod
    def _series_dataset_id(series_id: str) -> str:
        if series_id in {_UNEMPLOYMENT_RATE_SERIES, _AVERAGE_EARNINGS_SERIES}:
            return "lms"
        return "ukea"

    def _fetch_series_observations(self, series_id: str) -> list[dict[str, str]]:
        dataset_id = self._series_dataset_id(series_id)
        rows = self.get_observation_series(
            dataset_id,
            "time-series",
            "latest",
            timeseries=series_id,
            time="*",
        )
        return [
            {"date": date_id, "value": str(item.observation)}
            for item in rows
            if (date_id := item.dimensions.get_time_id())
        ]

    def get_observation_series(
        self,
        dataset_id: str,
        edition: str,
        version: str | int,
        **dimensions: str,
    ) -> list[Observation]:
        """Return individual observation rows from a dataset endpoint."""
        return self.get_observation(
            dataset_id, edition, version, **dimensions
        ).observations

    def list_datasets(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        dataset_type: str | None = None,
    ) -> list[ONSDatasetInfo]:
        """Return catalog datasets from the ONS dataset API (cached by args)."""
        cache_key = (limit, offset, dataset_type)
        if cache_key in self._datasets_cache:
            return self._datasets_cache[cache_key]
        params: dict[str, str] = {"limit": str(limit), "offset": str(offset)}
        if dataset_type is not None:
            params["type"] = dataset_type
        url = self._build_dataset_url("datasets", params=params)
        payload = get_json(url)
        raw_items = payload.get("items", []) if isinstance(payload, dict) else payload
        result = [ONSDatasetInfo.model_validate(item) for item in raw_items]
        self._datasets_cache[cache_key] = result
        return result

    def clear_dataset_cache(self) -> None:
        """Clear process-local dataset catalog cache."""
        self._datasets_cache.clear()

    def get_dataset(self, dataset_id: str) -> ONSDatasetInfo:
        """Return typed metadata for a single ONS dataset."""
        payload = get_json(self._build_dataset_url(f"datasets/{dataset_id}"))
        if not isinstance(payload, dict):
            msg = f"Malformed ONS dataset payload for {dataset_id!r}"
            raise ValueError(msg)
        return ONSDatasetInfo.model_validate(payload)

    def get_version(
        self,
        dataset_id: str,
        edition: str,
        version: str | int,
    ) -> ONSDatasetVersionInfo:
        """Return typed metadata for a specific dataset edition/version."""
        payload = get_json(
            self._build_dataset_url(
                f"datasets/{dataset_id}/editions/{edition}/versions/{version}"
            )
        )
        return ONSDatasetVersionInfo.model_validate(payload)

    def get_observation(
        self,
        dataset_id: str,
        edition: str,
        version: str | int,
        **dimensions: str,
    ) -> ONSObservation:
        url = self._build_dataset_url(
            f"datasets/{dataset_id}/editions/{edition}/versions/{version}/observations"
        )
        params = {k: v for k, v in dimensions.items() if isinstance(v, str)}
        full_url = f"{url}?{urlencode(params)}" if params else url
        payload = get_json(full_url)
        return ONSObservation.model_validate(payload)

    def available_series(self) -> list[str]:
        """Return the ONS series IDs supported by this adapter."""
        return [
            _GDP_SERIES,
            _HOUSEHOLD_INCOME_SERIES,
            _SAVINGS_RATIO_SERIES,
            _UNEMPLOYMENT_RATE_SERIES,
            _AVERAGE_EARNINGS_SERIES,
            _AFFORDABILITY_SERIES,
            _RENTAL_INDEX_SERIES,
        ]

    def fetch_series(self, series_id: str, **kwargs: object):
        """Fetch a canonical ONS time series."""
        series_id = series_id.upper()
        metadata = _SERIES_METADATA.get(series_id)
        if metadata is None:
            msg = f"Unsupported ONS series: {series_id}"
            raise ValueError(msg)

        limit = self._coerce_limit(kwargs.get("limit", 20))
        start_date = self._coerce_date_bound(kwargs.get("start_date"))
        end_date = self._coerce_date_bound(kwargs.get("end_date"))
        concept = str(kwargs.get("concept", metadata["concept"]))

        if series_id in {
            _GDP_SERIES,
            _HOUSEHOLD_INCOME_SERIES,
            _SAVINGS_RATIO_SERIES,
            _UNEMPLOYMENT_RATE_SERIES,
            _AVERAGE_EARNINGS_SERIES,
        }:
            observations = self._fetch_series_observations(series_id)
            observations = filter_observations_by_date_window(
                observations,
                start_date=start_date,
                end_date=end_date,
            )
            if limit >= 0:
                observations = observations[-limit:]
            return series_from_observations(
                series_id=concept,
                name=metadata["name"],
                frequency=metadata["frequency"],
                units=metadata["units"],
                seasonal_adjustment=metadata["seasonal_adjustment"],
                geography="UK",
                observations=observations,
                source="ons",
                source_series_id=series_id,
            )

        if series_id == _AFFORDABILITY_SERIES:
            return point_timeseries(
                series_id=concept,
                name=metadata["name"],
                value=_fetch_affordability_ratio(),
                units=metadata["units"],
                source="ons",
                source_series_id=series_id,
                frequency=metadata["frequency"],
                seasonal_adjustment=metadata["seasonal_adjustment"],
                geography="UK",
                metadata={"source_quality": "fallback"},
            )

        if series_id == _RENTAL_INDEX_SERIES:
            return point_timeseries(
                series_id=concept,
                name=metadata["name"],
                value=_fetch_rental_growth(),
                units=metadata["units"],
                source="ons",
                source_series_id=series_id,
                frequency=metadata["frequency"],
                seasonal_adjustment=metadata["seasonal_adjustment"],
                geography="UK",
                metadata={"source_quality": "fallback"},
            )

        msg = f"Unsupported ONS transport branch for series: {series_id}"
        raise ValueError(msg)

    def available_entity_types(self) -> list[str]:
        """ONS adapter does not support entity lookup."""
        return []

    def available_event_types(self) -> list[str]:
        """ONS adapter does not support event fetching."""
        return []

    def fetch_entity(self, entity_id: str, **kwargs: object) -> object:
        """Not supported by ONS adapter."""
        raise NotImplementedError

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[object]:
        """Not supported by ONS adapter."""
        raise NotImplementedError
