# External Integrations

**Analysis Date:** 2026-04-26

## APIs & External Services

**Companies House:**
- UK Companies House REST API — company search, filing history, document download
  - SDK/Client: `packages/uk-data/src/uk_data/adapters/companies_house.py` (bulk free data); `packages/companies-house/` (REST API client)
  - Auth: `COMPANIES_HOUSE_API_KEY` (HTTP Basic, key as username, empty password)
  - Bulk dataset URL: `https://download.companieshouse.gov.uk/en_output.html`

**ONS (Office for National Statistics):**
- ONS API v1 — GDP, household income, savings ratio, unemployment, average earnings, house prices, rental index, IO tables
  - SDK/Client: `packages/uk-data/src/uk_data/adapters/ons.py`, `packages/uk-data/src/uk_data/adapters/ons_provider.py`
  - Base URL: `https://api.ons.gov.uk/v1`
  - Auth: None (open data)
  - Optional SDMX protocol via `pandasdmx` (`uk-data[sdmx]`)

**Bank of England:**
- BoE Statistical Interactive Database (IADB) — Bank Rate, lending rates, CET1 capital ratio
  - SDK/Client: `packages/uk-data/src/uk_data/adapters/boe.py`
  - Base URL: `https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp`
  - Auth: None (open data)
  - Note: IADB endpoint returns HTTP 403 for non-browser clients; adapter falls back to hardcoded published values

**HMRC:**
- Published UK tax parameters — income tax bands, NI, corporation tax, VAT
  - SDK/Client: `packages/uk-data/src/uk_data/adapters/hmrc.py` (data loaded from bundled JSON at `packages/uk-data/src/uk_data/data/hmrc_tax_years.json`)
  - Auth: None (Open Government Licence)

**HM Land Registry:**
- Linked data SPARQL endpoint + bulk download — house price index, price paid data
  - SDK/Client: `packages/uk-data/src/uk_data/adapters/land_registry.py`
  - SPARQL endpoint: `https://landregistry.data.gov.uk/landregistry/query`
  - HPI API: `https://landregistry.data.gov.uk/app/ukhpi`
  - Auth: None (Open Government Licence)

**EPC (Energy Performance Certificates):**
- EPC Open Data Communities API — domestic certificate search and bulk file download
  - SDK/Client: `packages/uk-data/src/uk_data/adapters/epc.py`
  - Files API: `https://epc.opendatacommunities.org/api/v1/files`
  - Search API: `https://epc.opendatacommunities.org/api/v1/domestic/search`
  - Auth: `EPC_API_USER` + `EPC_API_PASS` (Base64 Basic auth)

**LLM / OCR Extraction (optional):**
- `litellm` — provider bridge for structured extraction from filing PDFs
  - SDK/Client: dynamic import in `packages/companies-house/src/companies_house/ingest/pdf.py`
  - Auth: provider-specific env vars (not hardcoded); configured externally
- `kreuzberg` — async PDF/image text extraction with OCR before LLM parsing
  - SDK/Client: `packages/companies-house/src/companies_house/ingest/pdf.py`
  - Auth: Not applicable
  - Requires optional dep: `companies-house[pdf]`

## Data Storage

**Databases:**
- DuckDB (embedded, local)
  - Connection: filesystem path (default `~/.companies_house/data.duckdb`) or `:memory:` for tests
  - Client: `duckdb` + `polars` in `packages/companies-house/src/companies_house/storage/db.py` and `packages/uk-data/src/uk_data/storage/canonical.py`

**File Storage:**
- Local filesystem only
  - Parquet files for legacy bulk storage (read/write via `polars`)
  - Raw JSON provenance store: `packages/uk-data/src/uk_data/storage/raw.py` (timestamped JSON blobs under `raw/<source>/<key>/`)
  - XBRL fixtures for testing: `tests/fixtures/`
  - Bundled reference data: `packages/uk-data/src/uk_data/data/` (HMRC JSON, SIC codes, etc.)

**Caching:**
- In-process LRU HTTP response cache (`_CACHE`, max 256 entries, thread-safe)
  - Implementation: `packages/uk-data/src/uk_data/_http.py`
  - Re-exported as compatibility shim: `packages/companies-house-abm/src/companies_house_abm/data_sources/_http.py`
- No distributed cache

## Authentication & Identity

**Companies House Basic Auth:**
- HTTP Basic auth using API key as username, empty password
- Implementation: urllib-based request wrapper (`packages/companies-house/`)
- Env var: `COMPANIES_HOUSE_API_KEY`

**EPC Basic Auth:**
- Base64-encoded `user:password` header
- Implementation: `packages/uk-data/src/uk_data/adapters/epc.py` → `_resolve_epc_credentials()`
- Env vars: `EPC_API_USER`, `EPC_API_PASS`

## HTTP Client Pattern

All external HTTP calls use **stdlib `urllib`** only (no `requests`/`httpx` at runtime):
- Retry decorator: `retry()` in `packages/uk-data/src/uk_data/_http.py`
- Browser-like User-Agent to avoid 403s from government APIs
- Helpers: `get_text()`, `get_json()`, `get_bytes()` with in-process caching

## Monitoring & Observability

**Error Tracking:** Not detected (no Sentry/Application Insights SDK in runtime code)

**Logs:** Standard-library `logging` (`logging.getLogger(__name__)`) throughout all ingest, storage, and adapter modules

## CI/CD & Deployment

**Hosting:**
- Documentation: GitHub Pages (`/.github/workflows/docs.yml`)
- Application: Docker container (`Dockerfile`), entrypoint `companies_house_abm`
- PyPI publishing: disabled (`/.github/workflows/release.yml` is a placeholder)

**CI Pipeline (GitHub Actions — `.github/workflows/ci.yml`):**
1. Lint: `ruff check` + `ruff format --check`
2. Type check: `ty check`
3. Test: pytest across Python 3.12, 3.13, 3.14 with coverage → Codecov upload
4. Secret scan: Gitleaks
5. Dependency scan: `pysentry-rs`
6. SAST: Semgrep

## Environment Configuration

**Required env vars:**
- `COMPANIES_HOUSE_API_KEY` — Companies House REST API commands
- `EPC_API_USER` + `EPC_API_PASS` — EPC data fetch
- `CODECOV_TOKEN` — CI coverage upload (GitHub Actions secret only)

**Secrets location:**
- Local development: `.env` file (not committed content)
- CI: GitHub Actions Secrets

## Webhooks & Callbacks

**Incoming:** None detected

**Outgoing:** None detected (all integrations are outbound pull/HTTP fetches; no configured webhook emitters)

---

*Integration audit: 2026-04-26*
