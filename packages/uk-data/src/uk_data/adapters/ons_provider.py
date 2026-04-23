"""pandasdmx-backed ONS provider helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uk_data.adapters.ons_manifest import ONSSeriesManifestEntry

_ONS_PROVIDER_ID = "ONS"
_ONS_PROVIDER_INFO = {
    "id": _ONS_PROVIDER_ID,
    "name": "Office for National Statistics",
    "url": "https://api.ons.gov.uk/v1",
    "documentation": "https://developer.ons.gov.uk/",
}


def _load_pandasdmx() -> Any:
    try:
        import pandasdmx
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised in tests
        msg = "pandasdmx is required for ONS SDMX series; install uk-data[sdmx]"
        raise ModuleNotFoundError(msg) from exc

    return pandasdmx


def register_ons_provider() -> None:
    """Register the custom ONS pandasdmx source once."""
    pandasdmx = _load_pandasdmx()
    sources = pandasdmx.source.sources
    if _ONS_PROVIDER_ID in sources:
        return

    try:
        pandasdmx.add_source(_ONS_PROVIDER_INFO)
    except ValueError:
        if _ONS_PROVIDER_ID not in sources:
            raise


def build_ons_request() -> Any:
    """Build a pandasdmx request for the custom ONS provider."""
    pandasdmx = _load_pandasdmx()
    register_ons_provider()
    return pandasdmx.Request(_ONS_PROVIDER_ID)


def fetch_sdmx_series(
    entry: ONSSeriesManifestEntry,
    *,
    limit: int = 20,
) -> list[dict[str, str]]:
    """Fetch and normalize SDMX observations for one manifest entry."""
    if entry.transport != "sdmx":
        msg = f"ONS series {entry.source_series_id} is not SDMX-backed"
        raise ValueError(msg)
    if entry.dataset_id is None:
        msg = f"ONS series {entry.source_series_id} is missing an SDMX dataset id"
        raise ValueError(msg)

    pandasdmx = _load_pandasdmx()
    request = build_ons_request()
    message = request.data(
        resource_id=entry.dataset_id,
        key=entry.sdmx_key or entry.source_series_id,
        params={"lastNObservations": str(limit)},
    )
    converted = pandasdmx.to_pandas(message)
    return _normalize_sdmx_payload(converted, limit=limit)


def _normalize_sdmx_payload(payload: Any, *, limit: int) -> list[dict[str, str]]:
    if limit <= 0:
        return []

    series_like = _unwrap_sdmx_payload(payload)
    rows = [
        {"date": _format_observation_label(label), "value": str(value)}
        for label, value in _iter_observations(series_like)
        if value not in (None, "")
    ]
    return rows[-limit:]


def _unwrap_sdmx_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        if len(payload) != 1:
            msg = f"Expected a single series in pandasdmx payload, got {len(payload)}"
            raise ValueError(msg)
        payload = next(iter(payload.values()))

    squeeze = getattr(payload, "squeeze", None)
    if callable(squeeze):
        payload = squeeze()

    return payload


def _iter_observations(payload: Any) -> list[tuple[Any, Any]]:
    if hasattr(payload, "items"):
        return [(label, _coerce_scalar(value)) for label, value in payload.items()]
    if isinstance(payload, list):
        return [(label, _coerce_scalar(value)) for label, value in payload]

    msg = f"Unsupported pandasdmx payload type: {type(payload)!r}"
    raise TypeError(msg)


def _coerce_scalar(value: Any) -> Any:
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except (TypeError, ValueError):
            return value
    return value


def _format_observation_label(label: Any) -> str:
    to_timestamp = getattr(label, "to_timestamp", None)
    if callable(to_timestamp):
        timestamp = to_timestamp()
        isoformat = getattr(timestamp, "isoformat", None)
        if callable(isoformat):
            return str(isoformat())

    isoformat = getattr(label, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())

    return str(label)
