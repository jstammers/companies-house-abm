# CLAUDE.md

This file provides guidance for AI assistants working on the Companies House ABM codebase.

## Project Overview

Companies House ABM is a Python library and CLI tool for ingesting and processing financial data from Companies House XBRL accounts. It transforms XBRL data into Parquet format using Polars for downstream agent-based modelling.

**Status**: Alpha (v0.2.0)
**License**: MIT
**Python**: >=3.10 (CI tests 3.10–3.13)

## Repository Structure

```
src/companies_house_abm/     # Production code
├── __init__.py               # Package version
├── cli.py                    # Typer CLI (ingest, fetch-data, serve, hello, --version)
├── ingest.py                 # ETL pipeline: schema, dedup, zip/stream ingest, merge
├── data_sources/             # Public data fetchers for ABM calibration
│   ├── __init__.py           # Module exports
│   ├── _http.py              # Shared HTTP utilities (urllib-based, in-memory cache)
│   ├── boe.py                # Bank of England: Bank Rate, lending rates, CET1
│   ├── calibration.py        # Translate fetched data into ModelConfig parameters
│   ├── hmrc.py               # HMRC: income tax bands, NI, corporation tax, VAT
│   └── ons.py                # ONS: GDP, household income, labour market, IO tables
├── webapp/                   # FastAPI economy simulator web application
│   ├── __init__.py
│   ├── app.py                # FastAPI app (REST API + static file serving)
│   ├── models.py             # Pydantic request/response models
│   └── static/               # Frontend assets
│       ├── index.html        # Single-page application entry point
│       ├── app.js            # Simulation UI logic
│       └── styles.css        # Application styles
└── abm/                      # Agent-based model module
    ├── __init__.py           # ABM package exports (Simulation, ModelConfig, load_config)
    ├── config.py             # Dataclass configuration and YAML loader
    ├── model.py              # Simulation orchestrator
    ├── agents/               # Agent implementations
    │   ├── __init__.py
    │   ├── base.py           # Abstract base agent class
    │   ├── firm.py           # Firm agent
    │   ├── household.py      # Household agent
    │   ├── bank.py           # Bank agent
    │   ├── central_bank.py   # Central bank agent (Taylor rule)
    │   └── government.py     # Government agent (fiscal policy)
    ├── markets/              # Market mechanisms
    │   ├── __init__.py
    │   ├── base.py           # Abstract base market class
    │   ├── goods.py          # Goods market
    │   ├── labor.py          # Labour market
    │   └── credit.py         # Credit market
    └── README.md             # ABM module documentation
tests/                        # Pytest test suite
├── conftest.py               # Shared fixtures
├── test_companies_house_abm.py  # CLI/version tests
├── test_ingest.py            # Ingest module tests (class-based, ~380 lines)
├── test_abm_agents.py        # Agent class tests (~400 lines)
├── test_abm_markets.py       # Market mechanism tests
├── test_abm_model.py         # Simulation model tests
├── test_abm_config.py        # Configuration loading tests
├── test_abm_performance.py   # Performance benchmarks for ABM simulation
└── test_data_sources.py      # Data sources and calibration tests
config/                       # Configuration files
├── README.md                 # Configuration usage guide
└── model_parameters.yml      # ABM model parameters (200+ parameters)
docs/                         # MkDocs documentation
├── abm-design.md             # ABM design document
├── modelling-approach.md     # Implemented modelling approach
├── stochastic-bounded-rationality.md  # Plan for stochastic extensions
├── api.md                    # API reference (mkdocstrings)
├── contributing.md           # Contributor guide
└── index.md                  # Documentation home page
scripts/                      # Utility scripts (download, extract, import)
notebooks/                    # Marimo interactive notebooks
├── firm_agent.py             # Firm agent explorer
├── household_agent.py        # Household agent explorer
├── bank_agent.py             # Bank agent explorer
├── policy_agents.py          # Central bank & government explorer
└── ecosystem.py              # Full ecosystem simulation
.github/workflows/            # CI, docs deployment, release
```

## Quick Reference Commands

All commands use `uv` as the package manager and are defined in the `Makefile`:

```bash
make install        # Install all dependencies (uv sync --all-groups)
make verify         # Run lint + format-check + type-check (no changes)
make fix            # Auto-fix lint and formatting issues
make test           # Run tests (pytest tests/ -v)
make test-cov       # Run tests with coverage report
make type-check     # Run ty type checker
make lint           # Run ruff check
make format-check   # Check formatting with ruff
make docs           # Build documentation (mkdocs build)
make docs-serve     # Serve documentation locally
make pysentry       # Dependency vulnerability scan
```

## Development Workflow

### 1. Initial Setup

After cloning the repository, install all dependencies and activate pre-commit hooks:

```bash
make install        # Runs: uv sync --all-groups
uv run prek install # Install pre-commit hooks (required)
```

This installs:
- Core dependencies (polars, stream-read-xbrl, typer)
- Dev dependencies (pytest, pytest-cov, ruff, ty, hatch, prek, pysentry-rs)
- Docs dependencies (mkdocs, mkdocs-material, mkdocstrings-python)
- ABM dependencies (mesa, networkx, numpy, scipy, matplotlib, pyyaml, marimo, fastapi, uvicorn, pydantic)

**Pre-commit hooks are required.** `prek install` registers a `.git/hooks/pre-commit` script that
automatically runs linting, formatting, and type-checking before every commit. Without it, hook
checks are silently skipped. Always run `uv run prek install` after cloning, even in automated /
coding-agent environments where git hooks are not installed by default.

### 2. Development Cycle

When making changes, follow this workflow:

#### Step 1: Make your changes
Edit code in `src/companies_house_abm/` or tests in `tests/`

#### Step 2: Auto-fix linting and formatting issues

```bash
make fix            # Auto-fix lint and format problems
```

This runs:
- `uv run ruff check --fix .` - Auto-fixes linting issues
- `uv run ruff format .` - Formats code according to project style

#### Step 3: Verify all quality checks pass

```bash
make verify         # Run all checks without making changes
```

This runs (in order):
1. `make lint` - Checks for linting issues (without fixing)
2. `make format-check` - Checks formatting (without changing)
3. `make type-check` - Runs type checking with ty

**All three checks must pass before committing.**

#### Step 4: Run tests

```bash
make test           # Run all tests with pytest
```

Or with coverage:

```bash
make test-cov       # Run tests with coverage report
```

### 3. Before Every Commit

**Always run these two commands before committing:**

```bash
make verify         # Ensures lint, format, and type checks pass
make test           # Ensures all tests pass
```

If `make verify` fails:
1. Run `make fix` to auto-fix issues
2. Manually fix any remaining issues
3. Run `make verify` again to confirm

If `make test` fails:
1. Review the test output
2. Fix the failing tests
3. Run `make test` again to confirm

### 4. Individual Make Commands

#### Quality Checks (No Changes)

```bash
make lint           # Check linting with ruff (no fixes)
make format-check   # Check formatting with ruff (no changes)
make type-check     # Run ty type checker
make verify         # Run all three checks above
```

#### Auto-Fix Commands

```bash
make fix            # Auto-fix linting and formatting
make format         # Format code only (same as part of make fix)
```

#### Testing Commands

```bash
make test           # Run tests with pytest
make test-cov       # Run tests with coverage report (XML + terminal)
make test-matrix    # Test across Python 3.10-3.13 (using hatch)
make test-matrix-cov # Test with coverage across all Python versions
```

#### Documentation Commands

```bash
make docs           # Build documentation (output to site/)
make docs-serve     # Serve documentation locally (http://127.0.0.1:8000)
```

#### Security & Dependencies

```bash
make pysentry       # Scan dependencies for vulnerabilities
```

### 5. Common Issues and Solutions

#### Issue: `make verify` fails with linting errors

**Solution:**
```bash
make fix            # Auto-fix what can be fixed
make verify         # Check if all issues resolved
```

#### Issue: `make verify` fails with type errors

**Solution:**
Type errors usually require manual fixes. Check the error message and:
- Add missing type annotations
- Fix type mismatches
- Update `[tool.ty]` config in `pyproject.toml` if needed (rare)

#### Issue: `make test` fails

**Solution:**
1. Read the test failure message carefully
2. Run specific test file: `uv run pytest tests/test_specific.py -v`
3. Run specific test: `uv run pytest tests/test_file.py::test_name -v`
4. Fix the code or test
5. Re-run `make test`

#### Issue: Need to skip slow tests

**Solution:**
```bash
uv run pytest tests/ -v -m "not slow"
```

### 6. Git Pre-commit Hooks (Required)

Pre-commit hooks must be installed before making any commits:

```bash
uv run prek install         # Install hooks into .git/hooks/pre-commit
uv run prek run --all-files # Run all hooks manually on every file
```

The hooks run automatically on every `git commit` and enforce:
- Trailing whitespace removal and end-of-file normalisation
- YAML and TOML validity
- No accidentally committed large files or merge conflict markers
- No debug statements (`breakpoint()`, `pdb`, etc.)
- Ruff linting (`--fix`) and formatting
- ty type checking

**Important for coding agents**: git hooks are not installed automatically when a repo is cloned;
`uv run prek install` must be run explicitly. If a commit fails due to a hook, fix the reported
issues (usually running `make fix` is sufficient), stage the changes, and commit again. Do not
bypass hooks with `--no-verify`.

### 7. CI/CD Pipeline

When you push to GitHub, the CI pipeline runs:

1. **Lint Check**: `ruff check` + `ruff format --check`
2. **Type Check**: `ty check`
3. **Tests**: pytest across Python 3.10–3.13 with coverage
4. **Security**: Gitleaks (secrets) + pysentry-rs (dependencies)
5. **SAST**: Semgrep static analysis

**All checks must pass for PR approval.**

### 8. Quick Reference Cheat Sheet

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `make install` | Install dependencies | First setup, after dependency changes |
| `uv run prek install` | Install pre-commit hooks | First setup (required, run after `make install`) |
| `uv run prek run --all-files` | Run all hooks manually | Verify hook state, fix accumulated issues |
| `make fix` | Auto-fix lint/format | Before committing |
| `make verify` | Check all quality | Before committing (required) |
| `make test` | Run tests | Before committing (required) |
| `make test-cov` | Tests + coverage | When checking coverage |
| `make lint` | Lint only (no fix) | To see issues without changing |
| `make format-check` | Check format only | To see format issues |
| `make type-check` | Type check only | To see type issues |
| `make docs-serve` | Preview docs | When editing documentation |
| `make pysentry` | Security scan | Before adding dependencies |

## Code Quality Tools

| Tool | Purpose | Config location |
|------|---------|-----------------|
| **Ruff** | Linting and formatting | `[tool.ruff]` in `pyproject.toml` |
| **ty** | Type checking (Astral) | `[tool.ty]` in `pyproject.toml` |
| **pytest** | Testing | `[tool.pytest.ini_options]` in `pyproject.toml` |
| **pytest-cov** | Coverage | `[tool.coverage]` in `pyproject.toml` |
| **prek** | Pre-commit hooks | `.pre-commit-config.yaml` |

### Ruff Rules

Line length is 88. Selected rule sets: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `ARG`, `SIM`, `TCH`, `PTH`, `ERA`, `RUF`. The `ARG001` rule (unused arguments) is ignored in test files.

### Type Checking Notes

ty has specific rule overrides due to Polars stubs and dynamic YAML loading:
- `invalid-assignment`: ignored
- `invalid-argument-type`: warn only (dynamic dict unpacking)
- `not-subscriptable`: ignored
- `unresolved-attribute`: warn only

## Testing Conventions

- Tests live in `tests/` and use pytest.
- Test classes are organized by function/module (e.g., `TestSchema`, `TestDeduplicate`, `TestIngestFromZips`).
- Helper factories `_make_row()` and `_make_df()` in `test_ingest.py` create test data with sensible defaults.
- External dependencies (`stream_read_xbrl_zip`, `stream_read_xbrl_sync`) are mocked using `unittest.mock`.
- Mark slow tests with `@pytest.mark.slow` (deselect with `-m "not slow"`).
- Coverage source is `src/companies_house_abm` with branch coverage enabled.

## Architecture Notes

### Key modules

- **`cli.py`**: Typer-based CLI. Commands: `ingest` (XBRL to Parquet, local ZIP or streaming mode), `fetch-data` (download ONS/BoE/HMRC calibration data), `serve` (launch economy simulator web app), `hello`. Lazy-imports heavy modules to keep CLI startup fast.
- **`ingest.py`**: Core ETL logic. `COMPANIES_HOUSE_SCHEMA` defines 39 columns with Polars types. Financial fields use `Decimal(20, 2)`. Deduplication uses `company_id`, `balance_sheet_date`, `period_start`, `period_end` as composite key. Data is always written as Parquet.
- **`data_sources/`**: Fetches publicly available UK economic data using the standard-library `urllib` (no extra runtime dependencies). Responses are cached in memory. Sub-modules: `ons.py` (national accounts, labour market, IO tables), `boe.py` (Bank Rate, lending rates, capital ratios), `hmrc.py` (income tax, NI, corporation tax, VAT), `calibration.py` (translates fetched data into `ModelConfig` parameters).
- **`webapp/`**: FastAPI application serving a single-page economy simulator. The `serve` CLI command launches it via uvicorn. Static frontend assets live in `webapp/static/`.

### Data flow

1. Data sourced from ZIP files or streamed from Companies House API
2. Raw XBRL parsed via `stream-read-xbrl` into row-oriented data
3. Rows cast to a strict Polars schema
4. New data merged with existing Parquet file (if present)
5. Deduplicated (keep last occurrence)
6. Written to output Parquet file

### ABM module

The agent-based model module (`src/companies_house_abm/abm/`) simulates UK macroeconomic dynamics using Companies House firm data.

**Agents** (`abm/agents/`):

- `base.py`: Abstract `BaseAgent` with `step()` and `get_state()` methods
- `firm.py`: Firm agents — pricing, production, employment, financials
- `household.py`: Household agents — consumption, saving, labour supply
- `bank.py`: Bank agents — lending, capital adequacy, risk pricing
- `central_bank.py`: Central bank — Taylor rule monetary policy
- `government.py`: Government — taxation, spending, fiscal rule

**Markets** (`abm/markets/`):

- `base.py`: Abstract `BaseMarket` with `clear()` method
- `goods.py`: Goods market — competitive allocation by price
- `labor.py`: Labour market — matching with frictions
- `credit.py`: Credit market — risk-based lending with rationing

**Orchestration**:

- `config.py`: Frozen dataclass configuration loaded from YAML
- `model.py`: `Simulation` class drives the period-by-period loop

**Configuration**: `config/model_parameters.yml` (200+ parameters)

**Documentation**: `docs/abm-design.md` (design) and `docs/modelling-approach.md` (implementation)

**Notebooks** (`notebooks/`): Marimo interactive notebooks for each agent and the full ecosystem

## CI Pipeline

GitHub Actions runs on push/PR to `main`:

1. **Lint**: `ruff check` + `ruff format --check`
2. **Type Check**: `ty check`
3. **Test**: pytest with coverage across Python 3.10–3.13, uploaded to Codecov
4. **Security**: Gitleaks (secret detection) + pysentry-rs (dependency scan)
5. **SAST**: Semgrep static analysis

## Git Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/). All commit messages **must** follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit types

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `refactor` | Code refactoring (no behavior change) |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks, dependency updates |
| `perf` | Performance improvements |
| `style` | Code style changes (formatting, no logic change) |
| `ci` | CI/CD configuration changes |

### Examples

```
feat: add export to CSV format
fix: handle empty XBRL responses gracefully
docs: update API reference for ingest module
test: add edge case coverage for deduplication
refactor: extract schema validation into helper
chore: update polars to v1.40
```

Conventional commits are required because the project uses **git-cliff** (`cliff.toml`) for automated changelog generation. Non-conventional commits are filtered out.

## Dependencies

### Core

- **polars** (>=1.38.1): DataFrame processing and Parquet I/O
- **stream-read-xbrl** (>=0.1.1): XBRL data streaming/parsing
- **typer** (>=0.12.0): CLI framework

### ABM (Agent-Based Model) Dependencies

- **mesa** (>=3.0.0): Python ABM framework
- **networkx** (>=3.2): Network analysis and graph operations
- **numpy** (>=1.26.0): Numerical computing
- **scipy** (>=1.11.0): Scientific computing and optimization
- **matplotlib** (>=3.8.0): Visualization
- **pyyaml** (>=6.0.0): YAML configuration parsing
- **marimo** (>=0.10.0): Interactive notebook framework
- **fastapi** (>=0.115.0): Web framework for the economy simulator API
- **uvicorn[standard]** (>=0.30.0): ASGI server for serving the web app
- **pydantic** (>=2.0.0): Data validation for API request/response models

### Build

- **hatchling**: Build backend
- **uv**: Package manager (with lockfile `uv.lock`)

### Dev

- **pytest** (>=9.0.0): Testing framework
- **pytest-cov** (>=7.0.0): Coverage plugin
- **ruff** (>=0.14.14): Linting and formatting
- **ty** (>=0.0.14): Type checking
- **hatch** (>=1.16.3): Environment management
- **prek** (>=0.1.0): Pre-commit hooks
- **pysentry-rs** (>=0.1.0): Dependency vulnerability scanning

### Docs

- **mkdocs** (>=1.6.0): Documentation generator
- **mkdocs-material** (>=9.7.0): Material theme for MkDocs
- **mkdocstrings-python** (>=2.0.1): Python API documentation
