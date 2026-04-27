"""Concept registry and resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime

    from uk_data.adapters.base import AdapterProtocol
    from uk_data.models import TimeSeries

ONS_CONCEPT_MAP: dict[str, str] = {
    "gdp": "ABMI",
    "household_income": "RPHQ",
    "savings_ratio": "NRJS",
    "unemployment": "MGSX",
    "average_earnings": "KAB9",
    "affordability": "HP7A",
    "rental_growth": "D7RA",
}

CONCEPT_REGISTRY: dict[str, dict[str, str | None]] = {
    **{
        concept: {"ons": series_id, "boe": None}
        for concept, series_id in ONS_CONCEPT_MAP.items()
    },
    "bank_rate": {"boe": "IUMABEDR", "ons": None},
    "mortgage_rate": {"boe": "IUMTLMV", "ons": None},
    "business_rate": {"boe": "IUMZICQ", "ons": None},
    "house_price_uk": {"land_registry": "uk_hpi_average", "ons": None},
    "corp_tax_rate": {"hmrc": "corporation_tax_2024", "ons": None},
    "income_tax_basic": {"hmrc": "income_tax_basic_2024", "ons": None},
    "vat_standard": {"hmrc": "vat_standard_2024", "ons": None},
}


@dataclass
class ConceptResolver:
    """Resolve canonical concepts to source-specific series identifiers."""

    adapters: dict[str, AdapterProtocol]
    registry: dict[str, dict[str, str | None]] = field(
        default_factory=lambda: CONCEPT_REGISTRY.copy()
    )

    def resolve_series(
        self,
        concept: str,
        *,
        source: str | None = None,
        start_date: str | date | datetime | None = None,
        end_date: str | date | datetime | None = None,
        **kwargs: object,
    ) -> TimeSeries:
        """Resolve and fetch a series for a canonical concept."""
        if concept not in self.registry:
            msg = f"Unknown concept: {concept}"
            raise ValueError(msg)

        candidates = self.registry[concept]
        fetch_kwargs = dict(kwargs)
        if start_date is not None:
            fetch_kwargs["start_date"] = start_date
        if end_date is not None:
            fetch_kwargs["end_date"] = end_date

        if source is not None:
            series_id = candidates.get(source)
            if series_id is None:
                msg = f"Concept {concept!r} is not available from source {source!r}"
                raise ValueError(msg)
            return self.adapters[source].fetch_series(
                series_id,
                concept=concept,
                **fetch_kwargs,
            )

        for adapter_name, series_id in candidates.items():
            if series_id is None or adapter_name not in self.adapters:
                continue
            return self.adapters[adapter_name].fetch_series(
                series_id,
                concept=concept,
                **fetch_kwargs,
            )

        msg = f"No adapter available for concept {concept!r}"
        raise ValueError(msg)
