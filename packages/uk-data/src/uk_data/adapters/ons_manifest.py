"""Declarative manifest for ONS-supported series."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Transport = Literal["sdmx", "fallback"]


@dataclass(frozen=True)
class ONSSeriesManifestEntry:
    """Metadata describing one advertised ONS series."""

    source_series_id: str
    concept: str
    name: str
    frequency: str
    units: str
    seasonal_adjustment: str
    geography: str = "UK"
    transport: Transport = "sdmx"
    provider_id: str = "ONS"
    dataset_id: str | None = None
    sdmx_key: str | None = None
    fallback_handler: str | None = None


ONS_SERIES_MANIFEST: dict[str, ONSSeriesManifestEntry] = {
    "ABMI": ONSSeriesManifestEntry(
        source_series_id="ABMI",
        concept="gdp",
        name="UK GDP at market prices",
        frequency="Q",
        units="GBP_M",
        seasonal_adjustment="SA",
        dataset_id="ukea",
        sdmx_key="ABMI",
    ),
    "RPHQ": ONSSeriesManifestEntry(
        source_series_id="RPHQ",
        concept="household_income",
        name="UK household disposable income",
        frequency="Q",
        units="GBP_M",
        seasonal_adjustment="SA",
        dataset_id="ukea",
        sdmx_key="RPHQ",
    ),
    "NRJS": ONSSeriesManifestEntry(
        source_series_id="NRJS",
        concept="savings_ratio",
        name="UK household savings ratio",
        frequency="Q",
        units="%",
        seasonal_adjustment="SA",
        dataset_id="ukea",
        sdmx_key="NRJS",
    ),
    "MGSX": ONSSeriesManifestEntry(
        source_series_id="MGSX",
        concept="unemployment",
        name="UK unemployment rate",
        frequency="M",
        units="%",
        seasonal_adjustment="SA",
        dataset_id="lms",
        sdmx_key="MGSX",
    ),
    "KAB9": ONSSeriesManifestEntry(
        source_series_id="KAB9",
        concept="average_earnings",
        name="Average weekly earnings",
        frequency="M",
        units="GBP",
        seasonal_adjustment="SA",
        dataset_id="lms",
        sdmx_key="KAB9",
    ),
    "HP7A": ONSSeriesManifestEntry(
        source_series_id="HP7A",
        concept="affordability",
        name="House price affordability ratio",
        frequency="A",
        units="ratio",
        seasonal_adjustment="NSA",
        transport="fallback",
        fallback_handler="affordability_ratio",
    ),
    "D7RA": ONSSeriesManifestEntry(
        source_series_id="D7RA",
        concept="rental_growth",
        name="Private rental growth",
        frequency="M",
        units="fraction",
        seasonal_adjustment="NSA",
        transport="fallback",
        fallback_handler="rental_growth",
    ),
}

ONS_SERIES_IDS = list(ONS_SERIES_MANIFEST)

ONS_CONCEPT_MAP = {
    entry.concept: entry.source_series_id for entry in ONS_SERIES_MANIFEST.values()
}
