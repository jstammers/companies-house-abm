# Development

## Quick Reference Commands

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
make format         # Auto-format in-place (ruff format .)
make test-matrix    # Run tests across Python 3.10-3.13 (hatch)
make build-rust     # Build optional Rust ABM extension (requires cargo + maturin)
make benchmark      # Run Python vs Rust ABM performance benchmark
```

## Development Workflow

### 1. Initial Setup

```bash
make install        # Runs: uv sync --all-groups
uv run prek install # Install pre-commit hooks (required)
```

### 2. Before Every Commit

```bash
make fix            # Auto-fix lint and formatting
make verify         # Check lint, format, and type checks pass
make test           # Run all tests
```

### 3. Pre-commit Hooks (Required)

```bash
uv run prek install         # Install hooks
uv run prek run --all-files # Run all hooks manually
```

Do not bypass hooks with `--no-verify`.

## Code Quality Tools

| Tool | Purpose | Config |
|------|---------|--------|
| **Ruff** | Linting + formatting (line-length 88) | `[tool.ruff]` in root `pyproject.toml` |
| **ty** | Type checking (Astral) | `[tool.ty]` in root `pyproject.toml` |
| **pytest** | Testing | `[tool.pytest.ini_options]` in root `pyproject.toml` |
| **prek** | Pre-commit hooks | `.pre-commit-config.yaml` |

### Type Checking Notes

ty rule overrides for Polars stubs, optional deps, and dynamic patterns:

- `invalid-assignment`: ignored
- `invalid-argument-type`: warn
- `not-subscriptable`: ignored
- `unresolved-attribute`: warn
- `invalid-return-type`: warn
- `invalid-method-override`: warn (io.RawIOBase stub mismatch for `_TailBuffer`)
- `unresolved-import`: warn (Rust extension not built in dev by default)
- `unresolved-import` fully ignored for
  `packages/companies-house/src/companies_house/ingest/pdf.py` (optional deps)

### pyproject.toml TOML Structure Gotcha

`[tool.ty.rules]` **must** appear before `[[tool.ty.overrides]]`. Defining the
`[[...]]` array-of-tables first and then re-opening the parent table with
`[tool.ty.rules]` triggers a "duplicate key" TOML parse error in strict parsers
(uv in CI, for example). The pre-commit `check-toml` hook does **not** catch
this.

## Git Conventions

Uses [Conventional Commits](https://www.conventionalcommits.org/): `feat`,
`fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`, `ci`. Required for
git-cliff changelog generation.

## CI Pipeline

GitHub Actions on push/PR to `main`:

1. Lint: `ruff check` + `ruff format --check`
2. Type Check: `ty check`
3. Test: pytest across Python 3.10-3.13 with coverage
4. Security: Gitleaks + pysentry-rs
5. SAST: Semgrep
