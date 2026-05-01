"""ONS (Office for National Statistics) data adapter.

Wraps the ONS dataset API (https://api.beta.ons.gov.uk/v1/) using a
three-stage schema-on-read pipeline:

1. :meth:`ONSAdapter.extract` fetches raw observation JSON for a given
   ``(dataset_id, edition, version, **dimensions)`` tuple and persists it
   to the configured :class:`~uk_data.storage.raw.RawStore` *unvalidated*.
2. :meth:`ONSAdapter.transform` loads a previously extracted raw payload,
   validates it through pydantic (:class:`~uk_data.adapters.ons_models.ONSObservation`),
   builds a canonical :class:`~uk_data.models.TimeSeries`, and upserts it to
   the configured :class:`~uk_data.storage.canonical.CanonicalStore`.
3. :meth:`ONSAdapter.fetch_series` reads only from the canonical store; it
   raises :class:`FileNotFoundError` if no extract+transform has run for the
   requested series.

Datasets used
-------------
- **ABMI** - UK GDP at market prices (GBP million, seasonally adjusted, quarterly).
- **RPHQ** - UK households' disposable income (GBP million, seasonally adjusted,
  quarterly).
- **NRJS** - Household saving ratio (%), seasonally adjusted, quarterly.
- **MGSX** / **KAB9** - Labour Force Survey: unemployment rate and average
  weekly earnings.
- **HP7A** - House price to workplace-based earnings affordability ratio.
- **D7RA** - Index of Private Housing Rental Prices (monthly).

All data is Crown Copyright, reproduced under the Open Government Licence.
See https://www.ons.gov.uk/methodology/geography/licences for details.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

if TYPE_CHECKING:
    from uk_data.models.timeseries import TimeSeries
    from uk_data.storage.canonical import CanonicalStore
    from uk_data.storage.raw import RawStore

from uk_data.adapters.base import BaseAdapter
from uk_data.adapters.ons_models import (
    Observation,
    ONSDatasetInfo,
    ONSDatasetVersionInfo,
    ONSObservation,
)
from uk_data.transformers.timeseries import (
    frame_to_timeseries,
    series_from_observations,
    timeseries_to_frame,
)
from uk_data.utils.http import get_json, retry

logger = logging.getLogger(__name__)

_ONS_API = "https://api.beta.ons.gov.uk/v1"

# Canonical Parquet path used by transform()/fetch_series() under the
# CanonicalStore root.
_CANONICAL_PATH = "timeseries/ons.parquet"

# Series IDs ----------------------------------------------------------------

_GDP_SERIES = "ABMI"
_HOUSEHOLD_INCOME_SERIES = "RPHQ"
_SAVINGS_RATIO_SERIES = "NRJS"
_UNEMPLOYMENT_RATE_SERIES = "MGSX"
_AVERAGE_EARNINGS_SERIES = "KAB9"
_AFFORDABILITY_SERIES = "HP7A"
_RENTAL_INDEX_SERIES = "D7RA"

# Series → human-readable metadata used by transform() to build the canonical
# TimeSeries. Keyed by upper-case ONS time-series identifier.
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

# Series → ONS dataset-API extract parameters.
#
# Each entry maps an ONS time-series ID to the ``(dataset_id, edition,
# version, dimensions)`` tuple that ``extract()`` will request. The five
# national-accounts / labour-market series live under the ``ukea`` and
# ``lms`` time-series datasets; HP7A and D7RA live in their own
# topic-specific datasets.
#
# The HP7A / D7RA dataset_ids have not been verified against the live API
# from this sandbox. If they turn out to differ from the values below, the
# workflow-level helpers in ``uk_data.workflows.ons`` will fall back to the
# package-level constants documented in that module so calibration remains
# robust until the IDs are corrected.
_SERIES_DATASET: dict[str, dict[str, Any]] = {
    "ABMI": {
        "dataset_id": "ukea",
        "edition": "time-series",
        "version": "latest",
        "dimensions": {"timeseries": "ABMI", "time": "*"},
    },
    "RPHQ": {
        "dataset_id": "ukea",
        "edition": "time-series",
        "version": "latest",
        "dimensions": {"timeseries": "RPHQ", "time": "*"},
    },
    "NRJS": {
        "dataset_id": "ukea",
        "edition": "time-series",
        "version": "latest",
        "dimensions": {"timeseries": "NRJS", "time": "*"},
    },
    "MGSX": {
        "dataset_id": "lms",
        "edition": "time-series",
        "version": "latest",
        "dimensions": {"timeseries": "MGSX", "time": "*"},
    },
    "KAB9": {
        "dataset_id": "lms",
        "edition": "time-series",
        "version": "latest",
        "dimensions": {"timeseries": "KAB9", "time": "*"},
    },
    "HP7A": {
        "dataset_id": "housing-affordability-in-england-and-wales",
        "edition": "time-series",
        "version": "latest",
        "dimensions": {"timeseries": "HP7A", "time": "*"},
    },
    "D7RA": {
        "dataset_id": "index-of-private-housing-rental-prices",
        "edition": "time-series",
        "version": "latest",
        "dimensions": {"timeseries": "D7RA", "time": "*"},
    },
}


def _fetch_timeseries(series_id: str, limit: int = 20) -> list[dict[str, str]]:
    """Return the latest *limit* observations for an ONS time series.

    Backward-compatibility helper for callers that pre-date the
    schema-on-read pipeline. Hits the dataset-API observations endpoint
    directly (via ``retry(get_json, url)``) and returns the unvalidated
    payload reduced to ``[{"date": ..., "value": ...}, ...]``.

    Args:
        series_id: ONS time-series identifier (e.g. ``"ABMI"``, ``"L2KL"``).
        limit: Maximum number of observations to return (most recent first).

    Returns:
        List of observation dicts ``{"date": str, "value": str}``, oldest
        first. Returns ``[]`` on any API failure.
    """
    sid = series_id.upper()
    cfg = _SERIES_DATASET.get(sid)
    if cfg is not None:
        dataset_id = cfg["dataset_id"]
        edition = cfg["edition"]
        version = cfg["version"]
        dimensions = dict(cfg["dimensions"])
    else:
        dataset_id = "ukea"
        edition = "time-series"
        version = "latest"
        dimensions = {"timeseries": sid, "time": "*"}

    base = (
        f"{_ONS_API}/datasets/{dataset_id}/editions/{edition}/versions/{version}"
        "/observations"
    )
    params = {k: v for k, v in dimensions.items() if isinstance(v, str)}
    url = f"{base}?{urlencode(params)}" if params else base

    try:
        payload = retry(get_json, url)
    except Exception:
        logger.warning("ONS API unavailable for series %s, returning []", series_id)
        return []

    observations: list[dict[str, str]] = []
    if isinstance(payload, dict):
        # Dataset API: {"observations": [{"dimensions": {"time": {"id": ...}},
        #                                  "observation": "..."}, ...]}
        raw_rows = payload.get("observations") or []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            dims = row.get("dimensions") or {}
            time_dim = dims.get("time") if isinstance(dims, dict) else None
            date_id: str | None = None
            if isinstance(time_dim, dict):
                date_id = time_dim.get("id")
            value = row.get("observation")
            if date_id and value not in (None, ""):
                observations.append({"date": str(date_id), "value": str(value)})

        # Legacy Zebedee-shape payload (used by older test fixtures): the
        # observations are bucketed under "quarters"/"months"/"years".
        if not observations:
            legacy = (
                payload.get("quarters")
                or payload.get("months")
                or payload.get("years")
                or []
            )
            for row in legacy:
                if isinstance(row, dict) and row.get("value") not in (None, ""):
                    date_str = str(row.get("date", ""))
                    observations.append({"date": date_str, "value": str(row["value"])})

    return observations[-limit:] if len(observations) > limit else observations


def _latest_float(series_id: str) -> float | None:
    """Return the most recent numeric value for an ONS time series.

    Backward-compatibility helper used by
    :mod:`companies_house_abm.data_sources.input_output` to read GVA series
    by ID without going through the full extract+transform pipeline.
    """
    obs = _fetch_timeseries(series_id, limit=1)
    if not obs:
        return None
    try:
        return float(obs[-1]["value"])
    except (KeyError, ValueError, TypeError):
        return None


def _coerce_iso_date(value: object) -> str | None:
    """Coerce a date-bound input to an ISO-8601 ``YYYY-MM-DD`` string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    msg = f"Invalid ONS date bound: {value!r}"
    raise ValueError(msg)


class ONSAdapter(BaseAdapter):
    """Schema-on-read adapter for Office for National Statistics data."""

    _source_name = "ons"

    def __init__(
        self,
        store: RawStore | None = None,
        *,
        canonical_store: CanonicalStore | None = None,
    ) -> None:
        super().__init__(store=store, canonical_store=canonical_store)
        self._datasets_cache: dict[
            tuple[int, int, str | None], list[ONSDatasetInfo]
        ] = {}

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Raw key construction
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_key(
        dataset_id: str,
        edition: str,
        version: str | int,
        dimensions: dict[str, str],
    ) -> str:
        """Build a deterministic, filesystem-safe RawStore key."""
        dim_part = "_".join(
            f"{k}={v}" for k, v in sorted(dimensions.items()) if isinstance(v, str)
        )
        return (
            f"{dataset_id}/{edition}/{version}/{dim_part}"
            if dim_part
            else f"{dataset_id}/{edition}/{version}"
        )

    @staticmethod
    def _series_id_for_key(key: str) -> str:
        """Recover the ``timeseries`` dimension from a RawStore key."""
        last = key.rsplit("/", maxsplit=1)[-1]
        for chunk in last.split("_"):
            if "=" not in chunk:
                continue
            k, v = chunk.split("=", maxsplit=1)
            if k == "timeseries":
                return v.upper()
        msg = f"Cannot recover series_id from key: {key!r}"
        raise ValueError(msg)

    # ------------------------------------------------------------------
    # Discovery API — kept typed (no schema-on-read)
    # ------------------------------------------------------------------

    def get_datasets(
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
        """Query the observations endpoint and return a typed payload."""
        url = self._build_dataset_url(
            f"datasets/{dataset_id}/editions/{edition}/versions/{version}/observations"
        )
        params = {k: v for k, v in dimensions.items() if isinstance(v, str)}
        full_url = f"{url}?{urlencode(params)}" if params else url
        payload = get_json(full_url)
        return ONSObservation.model_validate(payload)

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

    # ------------------------------------------------------------------
    # Stage 1: extract — fetch raw JSON, write to RawStore, no validation
    # ------------------------------------------------------------------

    def extract(
        self,
        dataset_id: str,
        edition: str,
        version: str | int,
        **dimensions: str,
    ) -> str:
        """Fetch raw observation JSON and persist it to the RawStore.

        ``dataset_id`` corresponds to :attr:`ONSDatasetInfo.id` returned by
        :meth:`get_datasets`. ``edition`` and ``version`` select the snapshot;
        ``dimensions`` filter the observation rows.

        No pydantic validation is performed here — the unparsed JSON is
        written verbatim. Use :meth:`transform` to validate and convert it
        into a canonical :class:`~uk_data.models.TimeSeries`.

        Args:
            dataset_id: ONS dataset identifier.
            edition: Edition slug (e.g. ``"time-series"``).
            version: Version identifier (e.g. ``"latest"`` or an integer).
            **dimensions: Dimension filters (e.g. ``timeseries="ABMI"``,
                ``time="*"``).

        Returns:
            The RawStore key under which the payload was written. Pass this
            to :meth:`transform`.
        """
        url = self._build_dataset_url(
            f"datasets/{dataset_id}/editions/{edition}/versions/{version}/observations"
        )
        params = {k: v for k, v in dimensions.items() if isinstance(v, str)}
        full_url = f"{url}?{urlencode(params)}" if params else url
        payload = get_json(full_url)
        key = self._raw_key(dataset_id, edition, version, params)
        self.save(key, payload)
        return key

    def extract_series(self, series_id: str) -> str:
        """Convenience wrapper: extract the raw payload for a known series ID.

        Looks up the dataset/edition/version/dimensions from the
        ``_SERIES_DATASET`` registry and forwards to :meth:`extract`.
        """
        sid = series_id.upper()
        if sid not in _SERIES_DATASET:
            msg = f"Unsupported ONS series for extract_series: {series_id}"
            raise ValueError(msg)
        cfg = _SERIES_DATASET[sid]
        return self.extract(
            cfg["dataset_id"],
            cfg["edition"],
            cfg["version"],
            **cfg["dimensions"],
        )

    # ------------------------------------------------------------------
    # Stage 2: transform — load raw, validate, write canonical
    # ------------------------------------------------------------------

    def transform(self, key: str) -> TimeSeries:
        """Load a raw payload from the RawStore and persist canonical rows.

        Validates the raw JSON via
        :class:`~uk_data.adapters.ons_models.ONSObservation`, builds a
        canonical :class:`~uk_data.models.TimeSeries`, and upserts it into
        the configured :class:`~uk_data.storage.canonical.CanonicalStore`
        at ``timeseries/ons.parquet``.

        Args:
            key: RawStore key returned by :meth:`extract` /
                :meth:`extract_series`.

        Returns:
            The canonical :class:`~uk_data.models.TimeSeries` produced.

        Raises:
            FileNotFoundError: If no raw payload exists for *key*.
            ValueError: If the raw payload's series ID is unknown.
        """
        raw = self.load(key)
        if raw is None:
            msg = f"No raw payload found for key={key!r}"
            raise FileNotFoundError(msg)

        parsed = ONSObservation.model_validate(raw)
        observations = [
            {"date": date_id, "value": str(item.observation)}
            for item in parsed.observations
            if (date_id := item.dimensions.get_time_id())
        ]

        series_id = self._series_id_for_key(key)
        metadata = _SERIES_METADATA.get(series_id)
        if metadata is None:
            msg = f"Unsupported ONS series in raw key {key!r}: {series_id}"
            raise ValueError(msg)

        ts = series_from_observations(
            series_id=metadata["concept"],
            name=metadata["name"],
            frequency=metadata["frequency"],
            units=metadata["units"],
            seasonal_adjustment=metadata["seasonal_adjustment"],
            geography="UK",
            observations=observations,
            source="ons",
            source_series_id=series_id,
        )

        if self._canonical is not None and ts.values.size > 0:
            self._canonical.upsert(timeseries_to_frame(ts), _CANONICAL_PATH)

        return ts

    # ------------------------------------------------------------------
    # Stage 3: fetch_series — read canonical only
    # ------------------------------------------------------------------

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

    def fetch_series(self, series_id: str, **kwargs: object) -> TimeSeries:
        """Read a canonical ONS time series from the canonical store.

        Args:
            series_id: ONS series identifier (case-insensitive).
            **kwargs: Optional ``start_date``, ``end_date``, ``limit``.

        Returns:
            The canonical :class:`~uk_data.models.TimeSeries` filtered by the
            provided date window and (optional) ``limit``.

        Raises:
            ValueError: If *series_id* is not in :meth:`available_series`.
            FileNotFoundError: If no canonical store is configured, or if
                the canonical Parquet file does not yet contain rows for
                *series_id*. Run :meth:`extract_series` and :meth:`transform`
                first.
        """
        sid = series_id.upper()
        if sid not in _SERIES_METADATA:
            msg = f"Unsupported ONS series: {series_id}"
            raise ValueError(msg)
        if self._canonical is None:
            msg = (
                "ONSAdapter has no canonical store configured; "
                "run extract+transform with a CanonicalStore first."
            )
            raise FileNotFoundError(msg)

        start_iso = _coerce_iso_date(kwargs.get("start_date"))
        end_iso = _coerce_iso_date(kwargs.get("end_date"))
        limit = self._coerce_limit(kwargs.get("limit", 20))

        try:
            frame = self._canonical.query_typed(
                _CANONICAL_PATH,
                entity=sid,
                start=start_iso,
                end=end_iso,
            )
        except FileNotFoundError as exc:
            msg = (
                f"No canonical ONS data for series_id={sid!r}; "
                "run extract+transform first."
            )
            raise FileNotFoundError(msg) from exc

        if frame.is_empty():
            msg = (
                f"No canonical ONS data for series_id={sid!r}; "
                "run extract+transform first."
            )
            raise FileNotFoundError(msg)

        if limit >= 0:
            frame = frame.tail(limit)

        return frame_to_timeseries(frame, series_id=sid)

    # ------------------------------------------------------------------
    # Entity / event surface (unchanged)
    # ------------------------------------------------------------------

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
