# Codebase Cleanup & API Simplification Plan

Status: proposal · Author: Claude · Date: 2026-07-17

## 1. Goal

Reshape the codebase around four clearly separated concerns, each with a single
home and a stable public API:

| Concern | One-line responsibility | Target home |
|---|---|---|
| **Data loading** | Fetch + persist raw external data, expose typed records | `uk_data` |
| **Modeling** | Run the ABM given a config (agents, markets, simulation) | `companies_house_abm.abm` (model core) |
| **Calibrating** | Turn data + firm profiles into a `ModelConfig`; tune params | `companies_house_abm.calibration` (new) |
| **Reporting** | Company financial reports + simulation evaluation + serving | `companies_house.analysis` / `companies_house_abm.reporting` (new) |

The refactor to build `uk_data` (the data-loading layer) is largely complete
per `.planning/ROADMAP.md` phases 1–4. This plan covers **finishing that
migration and then untangling calibration, modeling and reporting**, which
currently bleed into each other and into `data_sources/`.

## 2. Current state (what the review found)

### 2.1 Package layout today

```
packages/
├── companies-house/        # XBRL/PDF ingest → DuckDB → schema → analysis (company reports)
├── uk-data/                # NEW unified data layer: adapters, workflows, transformers,
│                           #   models, storage(raw/canonical), api(CH REST), registry, client
├── companies-house-abm/    # ABM: abm/(agents,markets,model), data_sources/, webapp/
└── rust-abm/               # optional maturin extension
```

### 2.2 Concrete problems

**A. `data_sources/` is a half-finished migration to `uk_data`.**
- `data_sources/{boe,ons,hmrc,companies_house,land_registry}.py` are **deprecation
  shims** re-exporting from `uk_data`.
- `data_sources/_http.py` is a **dead shim** — nothing imports it (only self-reference).
- Yet `cli.py::fetch_data` **imports those very shims** (lines ~306–470), so every
  `fetch-data` run emits `DeprecationWarning`s the project inflicted on itself.
- `data_sources/__init__.py` re-exports a flat 40+ name namespace mixing *fetching*
  (`fetch_gdp`, `get_vat_rate`) with *calibration* (`calibrate_model`) with
  *profiling* (`run_profile_pipeline`) — no separation of concern at the API surface.

**B. The `companies-house` package is a declared dependency the ABM never uses.**
- `companies-house-abm/pyproject.toml` depends on `companies-house[xbrl,analysis]`.
- **No file under `companies_house_abm/src` imports `companies_house`.**
- `firm_distributions.load_accounts()` reads a raw `*.parquet` directly with
  `pl.scan_parquet` instead of going through `companies_house.ingest`/`storage`.
- So the "proper" ingest→DuckDB→analysis pipeline runs in parallel and is
  disconnected from the model's actual data loading.

**C. "Calibration" is three unrelated things sharing a name.**
- `data_sources/calibration.py` (403 LOC) — *data → `ModelConfig`* (`calibrate_households`,
  `calibrate_banks`, `calibrate_government`, `calibrate_io_sectors`, `calibrate_model`).
- `abm/calibration.py` (300 LOC) — *parameter sweeps & sensitivity analysis*
  (`parameter_sweep`, `sensitivity_analysis`, `SweepResult`).
- `firm_distributions.py` (818 LOC) — *profile firm accounts + fit distributions →
  sector-year parameters* (also a form of calibration input).

**D. "Reporting" is spread across three surfaces with no shared contract.**
- `companies_house.analysis.*` — company-level financial reports/forecasts/benchmarks.
- `abm/evaluation.py` (500 LOC) — simulation-vs-target evaluation reports.
- `webapp/` — FastAPI serving + JSON models for the browser UI.

**E. "Historical" names three different concepts.**
- `uk_data/adapters/historical.py` — low-level quarterly fetchers.
- `data_sources/historical.py` — `HistoricalAdapter` orchestration wrapper.
- `abm/historical.py` — `HistoricalSimulation` runner (a *model*, not data).

**F. Stale config & doc drift.**
- `pyproject.toml:85` references `companies_house/api/models.py` — **that dir was
  deleted** (moved to `uk_data/api`).
- `CLAUDE.md` still documents `companies_house/api/` as the REST client and does
  not mention the `uk-data` package at all.
- `README`/docs describe the pre-`uk_data` layout.

### 2.3 Open PRs

- **#40** `refactor(uk-data): apply schema-on-read pipeline to ONSAdapter` — extends
  the extract/transform/fetch split and RawStore/CanonicalStore. **Land this first**;
  it is on the critical path (finishes the ONS adapter contract). Note its own caveat:
  `HP7A`/`D7RA` dataset IDs are best-guess and need live verification.
- **#36** `docs: add research on consumer goods market` — docs only, independent;
  merge or close on its own track, not part of this cleanup.

## 3. Target architecture

```
uk_data                         DATA LOADING (external world → typed records)
  adapters/  workflows/  transformers/  models/  storage/  api/  client

companies_house                 DATA LOADING (Companies House filings, specialised)
  ingest/  storage/  schema     — XBRL/PDF → DuckDB
  analysis/                     — REPORTING (company financial reports)   [see §5]

companies_house_abm
  abm/                          MODELING only (agents, markets, model,
                                  sector_model, scenarios, historical simulation)
  calibration/                  CALIBRATING (data→config, firm profiling, sweeps)
  reporting/                    REPORTING (evaluation + serialisation for webapp)
  webapp/                       thin HTTP layer over reporting/
  cli.py                        orchestration only — imports the four layers, no logic
```

Rule of thumb enforced by the layering: **`abm/` imports nothing from `uk_data`
or `calibration/`.** The model takes a `ModelConfig` and produces a
`SimulationResult`. Calibration produces configs; reporting consumes results.

## 4. Workstreams

### Phase A — Finish the `uk_data` migration (unblocks everything)
1. Merge PR #40 (ONS schema-on-read).
2. Repoint `cli.py::fetch_data` imports from `companies_house_abm.data_sources.*`
   shims to `uk_data.workflows.*` / `uk_data.adapters.*` directly.
3. Delete the dead/duplicated shims: `data_sources/{_http,boe,ons,hmrc,
   companies_house,land_registry}.py`.
4. Keep only genuinely ABM-owned modules in place temporarily (`calibration.py`,
   `firm_distributions.py`, `input_output.py`, `historical.py`) — relocated in Phase C.
5. Remove the DeprecationWarnings' reason for existing; no shim should be imported
   from within the repo.

*Exit:* `grep -r data_sources.\(boe\|ons\|hmrc\|_http\) packages tests` returns nothing;
`fetch-data` runs warning-free.

### Phase B — Fix stale config & docs (cheap, do alongside A)
1. `pyproject.toml`: drop the `companies_house/api/models.py` per-file-ignore; add
   `uk_data` paths already present are fine — audit `[tool.ty.overrides]` for dead paths.
2. `CLAUDE.md`: remove the `companies_house/api/` section, add a `uk-data` package
   section, and document the four-layer separation as the intended architecture.
3. Reconcile `README.md` and `docs/` (there are already `docs/uk-data-*.md`).

### Phase C — Establish the `calibration/` subpackage
1. Create `companies_house_abm/calibration/` and move in:
   - `data_sources/calibration.py`  → `calibration/from_data.py`
     (data→`ModelConfig`).
   - `data_sources/firm_distributions.py` → `calibration/firm_profiles.py`
     (profiling + distribution fitting).
   - `data_sources/input_output.py` → `calibration/input_output.py`.
   - `abm/calibration.py` → `calibration/sweep.py` (parameter sweep / sensitivity).
2. Give it one public API: `calibration/__init__.py` exports `calibrate_model`,
   `run_profile_pipeline`, `parameter_sweep`, `sensitivity_analysis` — and nothing
   about raw fetching (that's `uk_data`).
3. Decide the fate of the `companies-house` dependency:
   - If firm profiling should use the real ingest pipeline, wire
     `firm_profiles.load_accounts` to `companies_house.storage`/`ingest` and keep
     the dep.
   - If not, **drop `companies-house[xbrl,analysis]` from the ABM's deps** and let
     `load_accounts` keep reading parquet (document the contract). Removing an
     unused dependency is the honest default unless the pipeline is meant to connect.
4. `data_sources/` becomes empty → delete the package; update `__init__` re-exports
   and the ~6 test modules that import from it.

*Exit:* the words "calibrate", "profile", "sweep" all resolve to `calibration/`;
`abm/` has no calibration code.

### Phase D — Consolidate reporting
1. Create `companies_house_abm/reporting/` and move `abm/evaluation.py` →
   `reporting/evaluation.py` (simulation → report), plus the JSON/serialisation
   helpers currently living in `webapp/models.py` that describe *results* (not
   requests).
2. `webapp/app.py` becomes a thin transport shell that calls `reporting/`; no
   evaluation maths in the web layer.
3. Keep company-financial reporting in `companies_house.analysis` (it's already
   cleanly separated). Document the two reporting audiences (per-company vs
   whole-simulation) so they are not re-merged by accident.

*Exit:* `webapp/` contains only FastAPI wiring; all report computation is in
`reporting/` or `companies_house.analysis`.

### Phase E — Rename for clarity & tidy the CLI
1. Rename the three "historical" modules so the name states the layer:
   `uk_data/adapters/historical.py` → `historical_quarterly.py` (fetchers);
   keep `HistoricalAdapter` as the orchestration name; `abm/historical.py` →
   `abm/historical_simulation.py` (or keep, but ensure docstrings disambiguate).
2. Slim `cli.py` (1145 LOC): each command should import a layer and call one
   entry point (`uk_data` fetch, `calibration.calibrate_model`, `Simulation.run`,
   `reporting.evaluate_simulation`). Move `_write_*`/`_to_dict` helpers next to the
   code they serialise (likely `reporting/`).

## 5. Deduplication checklist (fast wins, mostly Phase A/B)

- [ ] Delete `data_sources/_http.py` (dead).
- [ ] Delete the 5 re-export shims once `cli.py` is repointed.
- [ ] Remove stale `pyproject.toml` per-file-ignore for the deleted `api/models.py`.
- [ ] Drop the unused `companies-house[xbrl,analysis]` dependency **or** wire it in
      (decide in Phase C.3 — do not leave it dangling).
- [ ] Collapse `data_sources/__init__`'s flat 40-name namespace; re-export from the
      four layer packages instead.
- [ ] Audit `abm/calibration.py`'s `factory`/`SweepResult` for overlap with
      `data_sources/calibration.py`'s `ModelConfig` construction (shared `replace`
      patterns can be factored into one helper).

## 6. Sequencing & risk

```
A (finish uk_data)  ──►  C (calibration/)  ──►  D (reporting/)  ──►  E (rename/CLI)
      │
      └─ B (config/docs) runs in parallel, low risk
```

- **A** is prerequisite (shims must go before moving their neighbours).
- Each phase is independently shippable behind green tests; the suite already covers
  `data_sources`, `abm`, `evaluation`, `firm_distributions`, `historical`, `webapp`,
  so moves are mechanically verifiable.
- **Test-import churn** is the main risk: ~6 test modules import `data_sources`.
  Update imports in the same commit as each move; run `make verify && make test`.
- **Public API break:** `data_sources` is imported by the CLI and tests only (not,
  as far as the review found, by external notebooks committed here). Treat the
  `data_sources` name as internal and remove it rather than maintaining shims
  indefinitely — the shims already warn.

## 7. Definition of done

1. Four packages/subpackages map 1:1 to the four concerns; no cross-layer leakage
   (`abm/` free of data/calibration/reporting imports).
2. Zero in-repo imports of any deprecation shim; `data_sources/` deleted.
3. No dead dependency: `companies-house` is either used or removed.
4. `CLAUDE.md`, `README`, `docs/` describe the `uk_data`-based four-layer layout.
5. `make verify && make test` green across Python 3.10–3.13.
