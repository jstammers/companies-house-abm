# Companies House Package

The `companies-house` package (`src/companies_house/`) is a standalone data ingestion and analysis library for UK Companies House financial data. It lives as a workspace member in the monorepo and can eventually be extracted to its own repository.

## Architecture Overview

```
src/companies_house/
├── __init__.py            # Public exports (CompanyFiling, schema, etc.)
├── schema.py              # Polars schema (39 cols) + CompanyFiling Pydantic model
├── cli.py                 # Typer CLI: ingest, search, filings, fetch, report, migrate, db-query
├── api/                   # Companies House REST API client
│   ├── client.py          # HTTP client with auth, rate limiting, retry
│   ├── models.py          # Pydantic response models (Filing, CompanySearchResult)
│   ├── filings.py         # Filing history + document download
│   └── search.py          # Company search
├── ingest/                # Data ingestion pipelines
│   ├── base.py            # IngestSource protocol
│   ├── xbrl.py            # Bulk XBRL ingestion (ZIP/stream)
│   └── pdf.py             # PDF extraction (kreuzberg + litellm)
├── analysis/              # Financial analysis
│   ├── benchmarks.py      # Sector benchmarks and peer comparison
│   ├── forecasting.py     # Time-series forecasting
│   ├── formatting.py      # Report formatting utilities
│   └── reports.py         # Full company report generation
└── storage/               # Persistence layer
    ├── db.py              # DuckDB storage with upsert semantics
    └── migrations.py      # Parquet-to-DuckDB migration
```

## Dual Schema

The package uses two complementary schema representations:

### Polars Schema

`COMPANIES_HOUSE_SCHEMA` is a 39-column dictionary mapping column names to Polars types. Financial fields use `Decimal(20, 2)` for precision. This schema is the source of truth for DataFrame operations and Parquet output.

### Pydantic Model

`CompanyFiling` is a Pydantic `BaseModel` that mirrors the Polars schema. It provides:

- **Validation** for data from any source (XBRL, PDF/LLM, API)
- **`to_polars_row()`** to convert a validated filing into a schema-conformant dict
- **`polars_schema()`** class method returning `COMPANIES_HOUSE_SCHEMA`
- **`duckdb_ddl(table_name)`** class method generating a `CREATE TABLE` statement with the composite primary key

### Deduplication

Records are deduplicated on the composite key: `company_id`, `balance_sheet_date`, `period_start`, `period_end`. DuckDB uses this as the primary key for upsert operations.

## Data Ingestion

### XBRL (Bulk)

The primary ingestion path processes bulk ZIP archives from Companies House:

1. ZIP files downloaded or streamed from Companies House
2. `stream-read-xbrl` parses iXBRL into row dicts
3. Rows cast to the Polars schema
4. Deduplicated and merged with existing data
5. Written to Parquet or upserted into DuckDB

CLI: `companies-house ingest --zip-dir ./zips` or `companies-house ingest --db companies.duckdb`

### PDF (Per-Company)

For companies without machine-readable XBRL filings:

1. **kreuzberg** extracts text from PDF bytes (OCR-capable)
2. **litellm** sends the text + `CompanyFiling.model_json_schema()` to an LLM
3. The JSON response is validated against `CompanyFiling`
4. Result converted to a Polars DataFrame with `file_type = "pdf"`

litellm supports any provider (Anthropic, OpenAI, Ollama, etc.) via the `--model` flag. Default: `claude-sonnet-4-20250514`.

CLI: `companies-house fetch 01873499 --model gpt-4o`

## Companies House REST API

The `api/` module provides a typed client for the [Companies House API](https://developer.company-information.service.gov.uk/):

| Endpoint | Function | Returns |
|----------|----------|---------|
| `/search/companies` | `search_companies()` | `list[CompanySearchResult]` |
| `/company/{number}/filing-history` | `get_filing_history()` | `list[Filing]` |
| Document API | `download_document()` | `bytes` |

Authentication uses HTTP Basic (API key as username). The client implements token-bucket rate limiting (600 requests / 5 minutes) and exponential backoff retry.

CLI commands: `companies-house search "company name"`, `companies-house filings 01873499`

## Storage

### DuckDB

`CompaniesHouseDB` provides OLAP-friendly storage with:

- **Upsert semantics** via `INSERT OR REPLACE` on the composite primary key
- **SQL queries** for ad-hoc analysis (`companies-house db-query "SELECT ..."`)
- **Company search** and per-company queries
- **Parquet export/import** for interoperability

### Parquet (Legacy)

The original storage format is still supported for bulk ingestion. Data is read, merged, deduplicated, and rewritten on each ingest cycle.

## Optional Dependencies

The package uses optional dependency groups to keep the core lightweight:

| Extra | Packages | Purpose |
|-------|----------|---------|
| `xbrl` | `stream-read-xbrl` | Bulk XBRL ingestion |
| `pdf` | `kreuzberg` | PDF text extraction |
| `llm` | `litellm` | LLM-based structured extraction |
| `analysis` | `numpy`, `scipy` | Financial analysis and forecasting |
| `all` | All of the above | Everything |

Install with: `pip install companies-house[all]` or `uv add companies-house[xbrl,llm]`

## Workspace Integration

The root `pyproject.toml` declares `src/companies_house` as a uv workspace member:

```toml
[tool.uv.workspace]
members = ["src/companies_house"]

[tool.uv.sources]
companies-house = { workspace = true }
```

The parent package `companies_house_abm` depends on `companies-house[xbrl,analysis]` and provides backward-compatible re-exports through `companies_house_abm.ingest` and `companies_house_abm.company_analysis`.
