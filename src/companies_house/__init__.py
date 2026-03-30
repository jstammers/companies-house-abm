"""Companies House data ingestion, analysis, and API client."""

__version__ = "0.1.0"

from companies_house.schema import (
    COMPANIES_HOUSE_SCHEMA,
    DEDUP_COLUMNS,
    SIC_TO_SECTOR,
    CompanyFiling,
)

__all__ = [
    "COMPANIES_HOUSE_SCHEMA",
    "DEDUP_COLUMNS",
    "SIC_TO_SECTOR",
    "CompanyFiling",
    "__version__",
]
