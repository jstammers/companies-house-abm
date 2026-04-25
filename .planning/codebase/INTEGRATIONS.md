# External Integrations

**Analysis Date:** Sat Apr 25 2026

## APIs & External Services

**Companies/Regulatory Data:**
- UK Companies House REST API - Company search, filing history, and document retrieval
  - SDK/Client: internal urllib-based client in `packages/companies-house/src/companies_house/api/client.py`
  - Auth: `COMPANIES_HOUSE_API_KEY`

**Public UK Macroeconomic Data:**
- ONS API (`api.ons.gov.uk` / beta endpoints) - GDP, labour market, IO and housing series for calibration
  - SDK/Client: shared HTTP helpers in `packages/companies-house-abm/src/companies_house_abm/data_sources/_http.py`
  - Auth: None detected
- Bank of England IADB endpoint - Monetary/credit indicators for calibration
  - SDK/Client: `packages/companies-house-abm/src/companies_house_abm/data_sources/boe.py` via `_http.py`
  - Auth: None detected
- HMRC/GOV.UK published pages - Tax and NI reference rates used by calibration logic
  - SDK/Client: `packages/companies-house-abm/src/companies_house_abm/data_sources/hmrc.py` via `_http.py`
  - Auth: None detected
- UK Land Registry endpoints - Housing index and SPARQL data pull
  - SDK/Client: `packages/companies-house-abm/src/companies_house_abm/data_sources/land_registry.py` via `_http.py`
  - Auth: None detected

**LLM/OCR Extraction:**
- litellm provider bridge - Structured extraction from filing PDFs
  - SDK/Client: dynamic `litellm` import in `packages/companies-house/src/companies_house/ingest/pdf.py`
  - Auth: Provider-specific keys expected externally; env var names not hardcoded in repo
- kreuzberg - PDF text extraction backend before LLM parsing
  - SDK/Client: `kreuzberg` in `packages/companies-house/src/companies_house/ingest/pdf.py`
  - Auth: Not applicable

## Data Storage

**Databases:**
- DuckDB (local embedded)
  - Connection: filesystem path or `:memory:` (`packages/companies-house/src/companies_house/storage/db.py`)
  - Client: `duckdb` + `polars` (`packages/companies-house/src/companies_house/storage/db.py`)

**File Storage:**
- Local filesystem only (Parquet, fixtures, generated outputs in repository and user paths)

**Caching:**
- In-process HTTP response cache for data fetchers (`_CACHE` in `packages/companies-house-abm/src/companies_house_abm/data_sources/_http.py`)
- No distributed cache detected

## Authentication & Identity

**Auth Provider:**
- Companies House Basic Auth using API key-as-username
  - Implementation: header construction + request wrapper in `packages/companies-house/src/companies_house/api/client.py`

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry/App Insights-style SDK in runtime code)

**Logs:**
- Standard-library logging (`logging.getLogger`) across API/storage/ingest modules, e.g. `packages/companies-house/src/companies_house/api/client.py` and `packages/companies-house/src/companies_house/storage/db.py`

## CI/CD & Deployment

**Hosting:**
- GitHub Pages for documentation (`.github/workflows/docs.yml`)
- Containerized runtime available via `Dockerfile` (CLI entrypoint `companies_house_abm`)

**CI Pipeline:**
- GitHub Actions (`.github/workflows/ci.yml`) for lint, type-check, tests, coverage upload, secret scan, dependency scan, Semgrep SAST

## Environment Configuration

**Required env vars:**
- `COMPANIES_HOUSE_API_KEY` (required for Companies House API-backed commands)
- `CODECOV_TOKEN` (CI-only for coverage upload in `.github/workflows/ci.yml`)

**Secrets location:**
- Local development: `.env` file present (contents intentionally not inspected)
- CI: GitHub Actions Secrets (`.github/workflows/ci.yml`)

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected (repo performs outbound pull/HTTP fetches; no configured webhook emitters)

---

*Integration audit: Sat Apr 25 2026*
