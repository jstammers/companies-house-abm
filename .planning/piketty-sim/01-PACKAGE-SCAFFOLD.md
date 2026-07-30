# Stage 01 — Package scaffold and root wiring

| | |
|---|---|
| **Status** | todo |
| **Depends on** | — |
| **Blocks** | S02, S03, S04 |
| **Requirements** | PKG-01 … PKG-08, INV-01, INV-04, INV-05 |
| **Commit** | `chore(piketty-sim): scaffold workspace package and root wiring` |

## 1. Purpose

Create `packages/piketty-sim/` as a fifth workspace member and make the entire
root toolchain aware of it, so that every subsequent stage lands inside a tree
that is already linted, type-checked, tested and covered. Wiring comes first
deliberately: if it comes last, every intermediate commit is invisible to CI and
the accumulated lint debt surfaces all at once.

This stage writes no simulation logic. Its deliverable is a package that imports,
a test that proves it imports, and green tooling.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `packages/piketty-sim/pyproject.toml` | create | hatchling, src layout; template is `packages/uk-data/pyproject.toml` |
| `packages/piketty-sim/README.md` | create | short pointer to the docs page and the notebook index |
| `packages/piketty-sim/src/piketty_sim/__init__.py` | create | version string and a deliberately empty public surface |
| `packages/piketty-sim/src/piketty_sim/py.typed` | create | empty marker |
| `packages/piketty-sim/src/piketty_sim/data/bundled/.gitkeep` | create | keeps the tracked-data path alive before S04 |
| `packages/piketty-sim/tests/test_package.py` | create | import and metadata smoke tests |
| `pyproject.toml` | modify | seven hardcoded per-package keys (§3.2) |
| `Makefile` | modify | `.PHONY`, `test`, `test-integration`, two new targets |
| `.gitignore` | modify | negate the bundled-data path |
| `docs/piketty-sim-package.md` | create | package documentation page |
| `mkdocs.yml` | modify | add the page to the explicit `nav` |
| `docs/architecture.md` | modify | package list, repo tree, layering-exception note |
| `CLAUDE.md` | modify | four packages → five; coupling rule |
| `uv.lock` | regenerate | via `make install` |

## 3. Design

### 3.1 Package manifest

Mirrors the conventions shared by all three existing Python members: hatchling
backend, `readme = "../../README.md"`, MIT licence, `requires-python = ">=3.10"`,
and `[tool.hatch.build.targets.wheel] packages = ["src/piketty_sim"]`.

```toml
[project]
name = "piketty-sim"
version = "0.1.0"
description = "Simulating Piketty: interactive notebooks on wealth dynamics"
readme = "../../README.md"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "altair>=5.4.0",
    "marimo>=0.10.0",
    "numpy>=1.26.0",
    "polars>=1.38.1",
    "pyyaml>=6.0",
    "scipy>=1.11.0",
    "uk-data",
]

[project.optional-dependencies]
politics = ["mesa>=3.0.0"]          # S11 only

[tool.uv.sources]
uk-data = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/piketty_sim"]

[tool.hatch.build.targets.wheel.force-include]
"src/piketty_sim/data/bundled" = "piketty_sim/data/bundled"
```

**Dependency decisions.** `numpy`, `scipy`, `polars` and `marimo` are already
workspace-wide, so they add no new resolution surface. `altair` is new and scoped
to this package: it binds declaratively to marimo's reactivity, which matters for
sliders driving live Lorenz curves. `pyyaml` supports the config round-trip and
the regime preset files of S10.

Three libraries from the source proposal are deliberately **not** taken:

- `quantecon` — wanted only for Gini and Lorenz helpers, which are about thirty
  lines of numpy. Avoids pulling a numba toolchain into the workspace.
- `powerlaw` — the Hill/MLE estimator in S03 is sufficient and more transparent
  pedagogically. Revisit as an optional extra only if S07's historical tail
  fitting needs Clauset-style automatic threshold selection.
- `matplotlib` — the series standardises on altair. The existing root notebooks
  use matplotlib; that divergence is recorded as policy in the docs page so it
  reads as a decision rather than drift.

`mesa` is an optional extra because only S11's voting model needs it, and it must
not become a hard dependency of a package whose core is pure numpy.

### 3.2 Root `pyproject.toml` edits

**Seven** keys are hardcoded per package. A new member is invisible to tooling
unless all seven are updated; only the workspace `members` glob picks it up
automatically. Locate them by key name, not by line number — the line numbers below
were accurate when this document was written and will drift.

| Key | Edit |
|---|---|
| `[tool.ruff] src` | add `"packages/piketty-sim/src"` |
| `[tool.ruff.lint.isort] known-first-party` | add `"piketty_sim"` |
| `[tool.ruff.lint.per-file-ignores]` | add `"packages/piketty-sim/notebooks/**/*.py" = ["B018", "E501", "PLC0206", "PLC0415"]` |
| `[tool.ty.src] exclude` | add `"packages/piketty-sim/tests"` |
| `[tool.pytest.ini_options] testpaths` | add `"packages/piketty-sim/tests"` |
| `[tool.pytest.ini_options] pythonpath` | add `"packages/piketty-sim/src"` |
| `[tool.coverage.run] source` | add `"piketty_sim"` |

Count them off against this table when done. An off-by-one here is exactly the
failure mode §7 warns about, and an earlier draft of this document said "six" while
listing seven.

The `slow`, `network` and `integration` pytest markers are **already registered**
in the root `markers` list, so no marker registration is needed — but `--strict-markers`
is on, so any *new* marker a later stage invents must be added there.

Two traps to respect:

- The existing per-file-ignores entry `"notebooks/**/*.py"` is **root-relative
  and will not match** `packages/piketty-sim/notebooks/`. Without the new entry,
  ruff's `B018` (useless expression) fails on every marimo display cell, because
  a bare `mo.md(...)` as the last expression of a cell is the idiom.
- If any `[[tool.ty.overrides]]` block is added, it must come **after**
  `[tool.ty.rules]`. uv's strict TOML parser fails in CI otherwise, and the
  `check-toml` hook does not catch it.

### 3.3 Makefile

Add the package to the two aggregate test targets, which hardcode directories
(`make test-cov`, the CI path, uses `testpaths` instead — update both or they
silently diverge), and add per-package targets following the `test-uk-data`
precedent:

```make
test-piketty:
	uv run pytest packages/piketty-sim/tests/ -m "not integration" -v

test-piketty-integration:
	uv run pytest packages/piketty-sim/tests/ -m integration -v
```

Update the `.PHONY` line to include both.

### 3.4 `.gitignore`

The repository ignores `data/` and `*.parquet` globally, with an existing
negation for uk-data's packaged data. Add the parallel negation immediately after
it:

```gitignore
!packages/piketty-sim/src/piketty_sim/data/
```

Bundled snapshots are committed as **JSON**, not parquet. This is a deliberate
consequence of the global `*.parquet` rule — a directory negation alone does not
rescue files matched by a filename pattern — and JSON has the side benefit of
being diffable in review. If a future stage must bundle parquet, it needs an
explicit `!.../bundled/*.parquet` negation placed after the `*.parquet` line.

### 3.5 Documentation

`docs/piketty-sim-package.md` covers: what the package is; the module map; the
twelve-notebook roadmap in three arcs plus capstone; how to run a notebook
(`uv run marimo edit packages/piketty-sim/notebooks/nb01_measuring_inequality.py`
from the repo root); the altair-not-matplotlib policy; and the coupling rules.

`docs/architecture.md` gains the package in its numbered list and repo tree, plus
a short subsection recording the **documented exception** to the layering rule:
raw data retrieval normally lives in `uk-data`, but this series' sources are
cross-country and cube-shaped, and `uk-data` is UK-scoped by name and by its
concept registry, so `piketty_sim.data` owns them while borrowing `uk-data`'s
storage and HTTP infrastructure.

`CLAUDE.md` changes "four packages" to five, adds the one-line package
description, and states the rule: *`piketty-sim` depends on `uk-data` only;
never on `companies_house_abm`.*

The two counts in this document are both correct and easy to confuse: `CLAUDE.md`
counts **four packages under `packages/`** because it includes the out-of-workspace
`rust-abm` crate, so it becomes five. §3.1 refers to **three existing Python
workspace members** — `companies-house`, `uk-data`, `companies_house_abm` — because
`rust-abm` is excluded from the uv workspace and is not a Python member. Four
directories, three Python members; both go up by one.

### 3.6 Notebook execution model — no PEP 723

The source proposal suggested PEP 723 inline dependency metadata so
`uvx marimo run notebook.py` would be self-contained. **We do not do this.** The
notebooks import `piketty_sim`, which exists only in this workspace; marimo's
sandbox mode would try to resolve it from an index and fail. The documented path
is `uv run marimo edit <notebook>` from the repo root, where the synced workspace
environment already provides everything. Each notebook states this in its header
cell.

## 4. Requirements

- [ ] **PKG-01** `uv sync` resolves the member; `import piketty_sim` works; `py.typed` present.
- [ ] **PKG-02** Ruff covers src, tests and notebooks, with marimo ignores on the package's notebook glob.
- [ ] **PKG-03** `ty` checks the src tree; package tests excluded.
- [ ] **PKG-04** Root pytest collects the package's tests; `piketty_sim` in coverage source.
- [ ] **PKG-05** Both new make targets work; both aggregate targets include the package.
- [ ] **PKG-06** Bundled data path is git-tracked and ships in the wheel.
- [ ] **PKG-07** No `companies_house_abm` dependency; `uk-data` pinned to the workspace.
- [ ] **PKG-08** Docs page exists and builds via nav; architecture and CLAUDE.md updated.

## 5. Tests

`packages/piketty-sim/tests/test_package.py`, class `TestPackageScaffold`.

| ID | Test | Assertion |
|---|---|---|
| T01-1 | `test_package_imports` | `import piketty_sim` succeeds and exposes `__version__`. |
| T01-2 | `test_package_is_typed` | `py.typed` exists inside the installed package directory. |
| T01-3 | `test_bundled_data_dir_exists` | The `data/bundled` directory resolves via `importlib.resources`. |
| T01-4 | `test_no_abm_dependency` | The package's declared dependencies contain neither `companies-house-abm` nor `companies-house`. |
| T01-5 | `test_no_abm_imports` | Recursively scanning every `.py` file under the package finds no *import* of `companies_house` — matching `^\s*(from\|import)\s+companies_house` per line, or better, walking the `ast` for `Import`/`ImportFrom` nodes. Implements INV-01 as an executable test, enforced automatically at every later gate rather than by manual grep. |

T01-5 is the load-bearing test of this stage: it converts the programme's central
architectural constraint into something CI fails on.

**It must match imports, not the bare string.** S02 requires copy-adapted modules
to name their origin in a docstring for the benefit of future readers, and that
attribution necessarily contains the text `companies_house`. A test scanning for
the bare substring would make honest attribution fail, pressuring the implementer
to drop the attribution — the opposite of what we want. Parsing the AST is the
robust form and is worth the extra few lines here, since this single test guards the
whole programme's central constraint.

## 6. Verification gate

```bash
make install                       # resolves the new member, updates uv.lock
make fix && make verify            # ruff + format + ty clean
make test                          # full suite, includes the new package
make test-piketty                  # new target works in isolation
make test-cov                      # coverage path sees piketty_sim
make docs                          # mkdocs builds with the new nav entry
uv build --package piketty-sim     # wheel builds; bundled data included
git status --porcelain             # bundled .gitkeep is tracked, not ignored
```

Pass criteria:

1. All commands above exit zero.
2. `uv run python -c "import piketty_sim; print(piketty_sim.__version__)"` prints a version.
3. `git check-ignore packages/piketty-sim/src/piketty_sim/data/bundled/.gitkeep` exits **non-zero** — the file is not ignored.
4. `rg -e 'from companies_house' -e 'import companies_house' packages/piketty-sim/` returns nothing.
5. The coverage report lists `piketty_sim`.
6. Unzipping the built wheel shows `piketty_sim/data/bundled/` present.

## 7. Risks

- **Silent tooling invisibility.** Forgetting any one of the seven root keys
  produces a package that appears fine but is unlinted or untested. Gate item 5
  and the `make test-cov` run are the specific checks for this.
- **Marimo lint failure surfacing only at S06.** The per-file-ignores glob is
  added now, before any notebook exists, precisely so the failure cannot be
  discovered late.
- **uv.lock churn.** Adding `altair` pulls a small transitive set. Review the
  lock diff for anything unexpected before committing.

## 8. Out of scope

No simulation code, no data loaders, no notebooks. The public surface of
`piketty_sim` is intentionally empty at the end of this stage; S02 and S03 fill
it. Existing root-level notebooks are left untouched.
