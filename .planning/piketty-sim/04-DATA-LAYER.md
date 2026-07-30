# Stage 04 — Data layer

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S01 |
| **Blocks** | S06 (and S07, S09, S11 extend it) |
| **Requirements** | DAT-01 … DAT-08 |
| **Commit** | `feat(piketty-sim): add WID, JST, Maddison and WIID loaders` |

## 1. Purpose

Build the empirical backbone: pinned, cached, offline-capable loaders for the four
sources the Arc A notebooks need, plus the shared machinery (registry, snapshot
fallback, schema contract) that later stages reuse when they add the Piketty book
appendices (S07), OECD fiscal data (S09) and WPID political data (S11).

The design constraint that shapes everything here is that **the default test run
and every notebook must work with no network access**. A notebook that only runs
when wid.world is reachable is not a teaching artefact, it is a demo. So every
loader has a committed offline snapshot sufficient to render every chart, and the
live path is an enhancement rather than a requirement.

The second constraint is provenance. WID series are revised continuously, so a
figure reproduced today will not match one reproduced next year unless the
snapshot is pinned. Every frame therefore carries where its numbers came from and
when.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/data/__init__.py` | create | re-export loaders and the schema helpers |
| `src/piketty_sim/data/registry.py` | create | source descriptors, pinned URLs and snapshot dates |
| `src/piketty_sim/data/schema.py` | create | the shared frame contract and validation |
| `src/piketty_sim/data/snapshots.py` | create | bundled-JSON access via `importlib.resources` |
| `src/piketty_sim/data/wid.py` | create | World Inequality Database |
| `src/piketty_sim/data/jst.py` | create | Jordà–Schularick–Taylor macrohistory |
| `src/piketty_sim/data/maddison.py` | create | Maddison Project GDP per capita |
| `src/piketty_sim/data/wiid.py` | create | UNU-WIDER WIID, survey-based contrast |
| `src/piketty_sim/data/bundled/*.json` | create | committed offline extracts |
| `tests/conftest.py` | create/modify | `CanonicalStore` tmp fixture, offline guard |
| `tests/test_data_loaders.py` | create | offline behaviour, schema, caching |
| `tests/test_data_integration.py` | create | live fetches, `integration` + `network` |

## 3. Design

### 3.1 What we borrow from `uk-data`, and what we do not

Imported and used as-is:

- `uk_data.storage.canonical.CanonicalStore` — parquet under
  `<root>/canonical/<relative_path>` with `write_parquet`, `read_parquet`,
  `upsert` (DuckDB composite-key dedup) and `query_typed`.
- `uk_data.utils.http` — `get_json`, `get_text`, `get_bytes` and `retry(fn, ...,
  retries=3, backoff=1.0)`, plus `clear_cache` for test hygiene. Note the HTTP
  cache is a 256-entry in-process LRU, not an on-disk cache, so the parquet layer
  is what gives us persistence across runs.

Deliberately **not** used:

- `uk_data`'s canonical `TimeSeries` model. It is single-valued per timestamp with
  numpy arrays, which fits a (country × year × variable × percentile) cube badly.
  We use polars frames throughout.
- `uk_data`'s `CONCEPT_REGISTRY` and `UKDataClient`. Both are UK-scoped by design.
  Registering cross-country inequality series there would distort a deliberately
  national abstraction.

We do adopt two of its *conventions*: the `source_quality` provenance tag
(`live` / `cached` / `static`, extending uk-data's `live` / `fallback` / `static`)
and packaging offline fallbacks as JSON read through `importlib.resources`.

### 3.2 Shared frame contract

Every loader returns a long-format `polars.DataFrame` with this schema, so that
notebook code, joins and charts are uniform across sources:

| Column | Type | Meaning |
|---|---|---|
| `source` | `str` | `wid`, `jst`, `maddison`, `wiid`, … |
| `country` | `str` | ISO-3166 alpha-2, or `WORLD` for aggregates |
| `year` | `int` | Observation year |
| `variable` | `str` | Canonical short name, e.g. `wealth_share`, `return_equity`, `gdp_per_capita`, `beta` |
| `percentile` | `str \| null` | e.g. `p99p100`, `p0p50`; null for non-distributional series |
| `value` | `f64` | The observation |
| `value_low` | `f64 \| null` | Lower uncertainty bound where the source provides or warrants one |
| `value_high` | `f64 \| null` | Upper uncertainty bound |
| `source_quality` | `str` | `live` \| `cached` \| `static` |
| `snapshot_date` | `str` | ISO date the data was pinned or fetched |

`schema.py` owns this contract: the column list, the polars dtype mapping, and a
`validate_frame(frame, *, source)` function that every loader calls before
returning. Validation failure raises rather than warning — a malformed frame
reaching a notebook produces a confusing chart instead of a clear error.

`value_low` / `value_high` exist to satisfy DAT-08. Pre-1900 series carry wide
uncertainty, and the series must be rendered as shaded bands rather than
confident lines. Carrying the bounds in the schema is what makes that possible in
the notebook layer rather than something each chart improvises.

### 3.3 Loader contract

Every loader has the same signature shape:

```python
def load_wid(
    store: CanonicalStore | None = None,
    *,
    countries: Sequence[str] = ("GB", "FR", "US", "DE", "SE"),
    variables: Sequence[str] = ("wealth_share", "income_share", "beta"),
    offline: bool = False,
) -> pl.DataFrame:
    """Load WID distributional series.

    Resolution order: parquet cache, then live fetch, then bundled snapshot.
    """
```

Resolution order, identical for all four sources:

1. **Cache** — if `store` is given and the parquet for this request exists, read
   it and tag `cached`. No network.
2. **Live** — unless `offline=True`, fetch the scoped request through
   `retry(get_bytes, url)`, parse, validate, and if `store` is given write the
   parquet. Tag `live`.
3. **Snapshot** — on `offline=True`, or on any failure of step 2, load the bundled
   JSON extract and tag `static`. Failures are logged, never silent, and never
   raised: a notebook must degrade to committed data rather than break.

That fallback-on-failure behaviour is the single most important property in this
stage. It means a notebook is reproducible on a plane, in CI, and in five years
when a source URL has moved.

### 3.4 Registry and pinning

`registry.py` holds one `SourceDescriptor` per source:

```python
@dataclass(frozen=True)
class SourceDescriptor:
    name: str
    title: str
    homepage: str
    snapshot_date: str        # ISO date the bundled extract was taken
    licence: str
    citation: str
    request_urls: Mapping[str, str]   # logical series -> pinned URL template
```

**URLs and variable codes must be confirmed against each source's own documented
download interface at implementation time, then recorded here as constants.** Do
not carry them over from memory or from this document — the codes are structured
and easy to get subtly wrong. In particular, WID variable codes compose a
concept, a percentile, an age group and a population unit into a single
identifier; the exact codes for wealth shares, income shares and the private
wealth-to-national-income ratio (Piketty's `beta`) must be looked up in WID's
codes dictionary and cited in a comment next to each constant.

Sources and what we need from each:

| Source | Series needed | Role |
|---|---|---|
| **WID.world** | Top-10%, top-1% and bottom-50% shares of wealth and of pre-tax national income; private wealth to national income (`beta`); long-run series for GB, FR, US, DE, SE | The backbone. Every empirical replication notebook loads WID. |
| **Jordà–Schularick–Taylor** | Real returns on housing, equity, bonds and bills; real GDP growth, 18 countries since 1870 | Empirical grounding for `r` and its composition, and for the `r − g` gap. |
| **Maddison Project** | Real GDP per capita over the long run | Grounds `g` over centuries. |
| **UNU-WIDER WIID** | Gini and percentile shares, harmonised survey panel | The survey-based contrast to WID's fiscal/DINA method — the disagreement is the point, not noise. |

DAT-06 forbids bulk-archive downloads. We fetch scoped per-country or per-series
requests only. This keeps the live path fast, keeps CI honest, and avoids
depending on multi-hundred-megabyte zips whose structure changes between releases.

### 3.5 Bundled snapshots

One JSON file per source under `data/bundled/`, committed to git (S01 added the
`.gitignore` negation; the global `*.parquet` rule is exactly why these are JSON):

```json
{
  "metadata": {
    "source": "wid",
    "source_url": "<pinned request URL>",
    "snapshot_date": "2026-07-27",
    "licence": "<source licence>",
    "citation": "<full citation>",
    "coverage": {"countries": ["GB", "FR", "US"], "years": [1900, 2023]},
    "row_count": 612
  },
  "records": [ { "country": "GB", "year": 1900, "variable": "wealth_share", "percentile": "p90p100", "value": 0.925 } ]
}
```

Snapshots stay small — a few hundred to a few thousand rows each, enough to render
every Arc A chart. They are produced by running the live loader once locally and
serialising the result; only the JSON is committed, never a scraping script that
must be re-run to understand the data.

`snapshots.py` exposes `load_snapshot(name) -> tuple[dict, pl.DataFrame]` reading
through `importlib.resources.files("piketty_sim.data") / "bundled"`, plus
`available_snapshots()` and `snapshot_metadata(name)` so a notebook can print its
own provenance — which is how NBA-09 (each notebook records its snapshot date) is
satisfied without hand-maintained frontmatter.

## 4. Requirements

- [ ] **DAT-01** Declared, validated schema; `source_quality` on every row.
- [ ] **DAT-02** Pinned snapshot dates and URLs as constants, surfaced in output.
- [ ] **DAT-03** Optional `CanonicalStore`; write on live fetch, read on next call.
- [ ] **DAT-04** `offline=True` and automatic fallback on failure, tagged `static`.
- [ ] **DAT-05** Snapshots committed as JSON with full metadata.
- [ ] **DAT-06** No bulk-archive downloads; scoped requests only.
- [ ] **DAT-07** WID, JST, Maddison and WIID loaders cover the Arc A requirements.
- [ ] **DAT-08** Uncertainty bounds available for wide-error historical series.

## 5. Tests

`tests/test_data_loaders.py` — **all offline**, the default suite.

| ID | Test | Assertion |
|---|---|---|
| T04-1 | `test_offline_returns_snapshot` | For each of the four sources, `offline=True` returns a non-empty frame with every row tagged `static`. |
| T04-2 | `test_schema_conforms` | Returned columns and dtypes match `schema.EXPECTED` exactly, for every source. |
| T04-3 | `test_fallback_on_fetch_failure` | With `uk_data.utils.http.get_bytes` patched to raise, `offline=False` still returns the snapshot tagged `static` and does not propagate the exception. Mirrors the patching idiom at `tests/test_notebook.py:77`. |
| T04-4 | `test_cache_write_then_read` | With a tmp `CanonicalStore` and a stubbed fetch, the first call writes parquet; a second call with the fetch stub now raising returns `cached` data — proving the cache was used, not the network. |
| T04-5 | `test_snapshot_metadata_complete` | Every bundled snapshot has non-empty `source_url`, `snapshot_date`, `licence`, `citation` and a `row_count` matching its record count. |
| T04-6 | `test_snapshot_dates_are_iso` | Every `snapshot_date` parses as an ISO date and is not in the future. |
| T04-7 | `test_no_bulk_urls` | No registry URL points at a `.zip` archive, enforcing DAT-06 mechanically. |
| T04-8 | `test_uncertainty_bounds_present_pre_1900` | Where a source supplies or warrants bounds, pre-1900 rows have non-null `value_low`/`value_high`; where not supplied, the loader documents it and the test asserts the documented behaviour. |
| T04-9 | `test_validate_frame_rejects_malformed` | A frame missing a column or with a wrong dtype raises from `validate_frame`. |
| T04-10 | `test_arc_a_coverage` | The snapshots jointly contain everything Arc A needs: WID wealth and income shares plus `beta` for GB/FR/US, JST returns, Maddison GDP per capita, WIID Ginis — asserted as concrete non-empty selections. This is the test that stops S06 starting on incomplete data. |

`tests/test_data_integration.py` — `@pytest.mark.integration` **and**
`@pytest.mark.network`, excluded from `make test`.

| ID | Test | Assertion |
|---|---|---|
| T04-11 | `test_live_fetch_each_source` | A live scoped fetch per source returns a schema-conforming, non-empty frame tagged `live`. |
| T04-12 | `test_live_matches_snapshot_shape` | Live and snapshot frames agree on schema and on the set of `(country, variable)` pairs — catching an upstream restructuring without asserting unchanged values, which legitimately change on revision. |

`tests/conftest.py` provides: a `canonical_store` fixture on `tmp_path`; an
autouse fixture calling `uk_data.utils.http.clear_cache()` before and after each
test, mirroring `packages/uk-data/tests/conftest.py`; and an autouse guard that
fails any unmarked test attempting a socket connection, so INV-02 is enforced
mechanically rather than by reviewer vigilance.

## 6. Verification gate

```bash
make fix && make verify
make test-piketty                    # offline suite green
make test                           # whole repo green
uv run pytest packages/piketty-sim/tests/test_data_loaders.py -v
make test-piketty-integration       # run manually, with network
```

Pass criteria:

1. Offline suite passes with networking disabled at the OS level, not merely
   unused. Verify explicitly — for example run the offline test file with
   `HTTPS_PROXY` and `HTTP_PROXY` set to an unroutable value — and confirm it
   still passes.
2. Every source loads offline and prints its provenance:
   ```bash
   uv run python -c "
   from piketty_sim.data import load_wid, load_jst, load_maddison, load_wiid
   for fn in (load_wid, load_jst, load_maddison, load_wiid):
       df = fn(offline=True)
       q = set(df['source_quality'].unique())
       print(f'{fn.__name__:14s} rows={df.height:6d} quality={q} snapshot={df[\"snapshot_date\"][0]}')"
   ```
3. T04-10 passes — Arc A's data needs are demonstrably met.
4. Integration tests pass when run manually with network access. If a source is
   unreachable, that is recorded in the stage log and does **not** block the gate,
   because the offline path is the contract; but a *schema* mismatch in T04-12
   does block, since it means our parser is wrong.
5. Total bundled snapshot size under 2 MB, checked with
   `du -sh packages/piketty-sim/src/piketty_sim/data/bundled/`.
6. Snapshots are tracked: `git check-ignore` on each returns non-zero.

## 7. Risks

- **Source URLs and variable codes change.** This is the main fragility, and the
  reason the fallback is automatic rather than opt-in. The registry centralises
  every URL so a break is a one-file fix, and T04-12 detects upstream
  restructuring on demand rather than at notebook runtime.
- **Snapshot staleness.** Committed extracts drift from the live sources. Accepted
  deliberately: reproducibility beats freshness for a teaching artefact. The
  snapshot date is displayed in every notebook so a reader always knows the
  vintage, and refreshing is a normal, reviewable commit.
- **Licensing.** Each source has its own terms for redistribution. Confirm at
  implementation that committing a small derived extract is permitted for each of
  the four, record the licence and citation in the snapshot metadata, and if any
  source disallows redistribution, fall back to fetch-only with a clearly
  documented degraded offline mode for that source rather than committing data we
  may not ship.
- **WID versus WIID divergence looking like a bug.** It is not; it is Piketty's
  methodological argument that surveys miss the top tail. NB01 addresses it
  head-on (NBA-02), and no test asserts agreement between the two.

## 8. Out of scope

Piketty's book appendix spreadsheets (S07), OECD SOCX and IDD (S09), WPID (S11)
and World Bank PIP (unscheduled) all extend this layer later using the same
descriptor, schema and snapshot machinery. Adding a source is intentionally a
small, patterned change; that pattern is this stage's real deliverable.
