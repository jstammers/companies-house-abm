# CLAUDE.md

This file provides guidance for AI assistants working on the Companies House ABM
codebase. It is deliberately short; detailed reference lives under `docs/` and
should be read on demand.

## Project Overview

A **uv workspace monorepo** ([uv workspace
layout](https://docs.astral.sh/uv/concepts/projects/workspaces/)) of four
packages under `packages/`:

1. **`companies-house`** — Ingest/store/analyse Companies House financial data
   (XBRL, PDF, DuckDB, financial analysis). Depends on `uk-data` for the REST
   API client.
2. **`uk-data`** — Unified UK data-loading layer (adapters, workflows,
   transformers, typed models, storage, `UKDataClient`). The single home for
   external data retrieval.
3. **`companies_house_abm`** — Agent-Based Model of the UK economy (agents,
   markets, simulation), calibration helpers under `data_sources/`, and a
   FastAPI webapp. Depends on `companies-house[xbrl,analysis]` and `uk-data`.
4. **`companies-house-abm-rust`** (`packages/rust-abm/`) — Optional maturin Rust
   extension; not a uv member, built via `make build-rust`.

Layering rule: raw data retrieval lives in `uk-data`; the ABM consumes it and
must not re-implement fetching.

## Documentation Map

Read the relevant file when you need detail — do not assume its contents:

| Topic | File |
|---|---|
| Package layout, repo tree, workspace/build, schema, storage, API client, Rust, deps, env vars | [`docs/architecture.md`](docs/architecture.md) |
| Setup, commands, pre-commit workflow, code-quality tools, type-checking notes, git conventions, CI | [`docs/development.md`](docs/development.md) |
| Test conventions, layout, markers | [`docs/testing.md`](docs/testing.md) |

## Essential Rules

- **Before every commit**: `make fix` → `make verify` → `make test`.
- **Never** bypass pre-commit hooks with `--no-verify`.
- Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat`,
  `fix`, `docs`, `refactor`, `test`, `chore`, …) — required for changelog
  generation.
- `[tool.ty.rules]` **must** precede `[[tool.ty.overrides]]` in `pyproject.toml`,
  or uv's strict TOML parser fails in CI (the `check-toml` hook does not catch
  this). See [`docs/development.md`](docs/development.md).
