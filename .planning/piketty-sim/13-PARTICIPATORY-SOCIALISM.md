# Stage 13 — Participatory socialism (NB11)

| | |
|---|---|
| **Status** | todo |
| **Depends on** | S09, S12 |
| **Blocks** | S15 |
| **Requirements** | PSO-01 … PSO-03 |
| **Commit** | `feat(piketty-sim): add universal endowment and funding mix` |

> Specified to design depth. Bands pinned at implementation start.

## 1. Purpose

Simulate the central constructive proposal of *Capital and Ideology* and *A Brief
History of Equality*: a universal capital endowment paid to every young adult —
"inheritance for all" — funded by steeply progressive wealth and inheritance
taxation, with the aim of circulating property rather than merely taxing its
returns.

This is the natural counterpart to NB06. That notebook asks what a wealth tax does
to the distribution; this one asks what the *revenue* does when it is returned as
capital rather than spent as transfers. The distinction is the substance of the
proposal: a transfer raises consumption, an endowment creates owners, and only the
second changes who holds wealth a generation later.

Because the mechanism operates across generations, this stage needs both the OLG
layer from S08 and the transmission channel from S12 to say anything meaningful.

## 2. Scope

| File | Action | Notes |
|---|---|---|
| `src/piketty_sim/engine/endowments.py` | create | endowment payment and funding |
| `src/piketty_sim/engine/kesten.py` | modify | apply endowments at the demography seam |
| `src/piketty_sim/engine/results.py` | modify | record endowment flows and funding balance |
| `notebooks/nb11_participatory_socialism.py` | create | the proposal, simulated |
| `tests/test_engine_endowments.py` | create | budget identity, dynamics |

## 3. Design

### 3.1 The endowment

`EndowmentConfig`, declared in S02, becomes live:

```python
amount_fraction_of_mean: float = 0.0    # endowment as a fraction of mean adult wealth
age_at_receipt: int = 25
```

Piketty's illustrative figure is on the order of 60% of average adult wealth, paid
at 25. The fraction-of-mean parameterisation matters: an endowment fixed in absolute
terms erodes as the economy grows, whereas one indexed to mean wealth is a standing
claim on the capital stock, which is what the proposal intends.

The payment is applied at the demography seam, when an agent reaches the receipt
age. Wealth circulation is the outcome to measure, not an input.

### 3.2 Funding and the budget identity

Funding comes from a configurable mix of the S09 instruments — annual progressive
wealth taxation and progressive inheritance taxation. The requirement (PSO-01) is
that the **budget identity is enforced and reported**: total endowments paid in a
period must equal revenue raised for that purpose, up to an explicitly recorded
surplus or deficit.

This is the honest core of the notebook. It is easy to make a universal endowment
look wonderful by paying it from nowhere. The model must show what schedule is
required to fund a given endowment, and if the answer is a schedule far outside
anything historically observed, the notebook should say so rather than quietly run
a deficit. Two modes:

- `"balanced"` — the endowment is scaled down to what revenue supports, and the
  shortfall is reported.
- `"fixed"` — the endowment is paid as specified and the resulting deficit is
  recorded and displayed.

Both are legitimate analytically; silently doing the second while presenting it as
the first is not.

### 3.3 Wealth circulation

The proposal's distinctive claim is about *temporary* ownership — property
circulating rather than accumulating permanently. The metric is a circulation rate:
the fraction of the capital stock changing hands per period through taxation and
endowment, as distinct from through bequest. Reporting it lets the notebook
distinguish the proposal's mechanism from a conventional redistributive tax with
the same revenue.

### 3.4 NB11

Cells: the proposal stated; a panel for endowment size, receipt age, funding mix
and funding mode; distributional dynamics over two to three generations; the
circulation rate; mobility outcomes reusing S12's metrics; and a three-way
comparison against the status quo and against NB06's pure wealth-tax world at
matched revenue.

That matched-revenue comparison is the analytically decisive chart: same revenue,
two uses, and the question is whether returning it as capital produces different
distributional dynamics than returning it as income. If it does not, the proposal's
distinctive claim is not supported by this model, and the notebook must report that
outcome as readily as the favourable one.

## 4. Requirements

- [ ] **PSO-01** Endowment at a configurable age, funded from a configurable mix, with the budget identity enforced and reported.
- [ ] **PSO-02** NB11 shows multi-generation dynamics and compares against the status quo and NB06's wealth-tax world.
- [ ] **PSO-03** Endowment and funding parameters zero by default.

## 5. Tests

`tests/test_engine_endowments.py`

| ID | Test | Assertion |
|---|---|---|
| T13-1 | `test_defaults_reproduce_baseline_bitwise` | Zero endowment reproduces S09/S12 baselines bitwise at the same seed. PSO-03. |
| T13-2 | `test_budget_balances_in_balanced_mode` | Endowments paid equal revenue raised, to floating-point tolerance, every period. |
| T13-3 | `test_deficit_reported_in_fixed_mode` | With an underfunded schedule, the deficit is non-zero, recorded, and equal to payments minus revenue. |
| T13-4 | `test_endowment_paid_once_per_agent` | Across a long run, each agent receives exactly one endowment, at the configured age. |
| T13-5 | `test_endowment_raises_bottom_share` | The bottom-50% wealth share rises relative to the no-endowment baseline at matched revenue. |
| T13-6 | `test_endowment_raises_mobility` | Rank-rank slope falls relative to baseline — reusing S12's metrics. `slow`. |
| T13-7 | `test_circulation_rate_positive` | The circulation rate is positive when the endowment is active and zero when it is not. |
| T13-8 | `test_matched_revenue_comparison_runs` | Endowment and pure-transfer configurations at matched revenue both run and produce comparable metric sets — the comparison NB11 depends on is computable. |
| T13-9 | `test_indexed_endowment_keeps_pace` | With growth, an endowment indexed to mean wealth stays a constant fraction of mean wealth, while a fixed nominal amount erodes. |

## 6. Verification gate

```bash
make fix && make verify
uv run pytest packages/piketty-sim/tests/test_engine_endowments.py -v
uv run pytest packages/piketty-sim/tests/test_notebooks.py -v
make test-piketty && make test
```

Pass criteria:

1. All commands exit zero; T13-1, T13-2 and T13-8 pass specifically.
2. All earlier pinned observations reproduce unchanged.
3. The funding schedule required for an endowment of roughly 60% of mean adult
   wealth is computed and recorded in §9, and compared against historically observed
   top tax rates. If the required schedule is outside historical experience, the
   notebook states that plainly.
4. The matched-revenue comparison is run and its result recorded — including if the
   result is that the endowment and the transfer are distributionally similar.
5. NB11 opened interactively; funding mode switch behaves as documented.

## 7. Risks

- **Free-lunch presentation.** The dominant risk. Mitigated by the enforced budget
  identity, the explicit deficit reporting, and gate item 3's comparison against
  historical tax rates.
- **No behavioural response.** The model has no labour-supply or saving response to
  either the endowment or the taxes funding it. This is a real limitation and belongs
  in the limitations callout, not buried. The `avoidance_elasticity` from S09 is the
  only behavioural channel present, and it is crude.
- **Generational horizon.** Two to three generations of simulation is a long run
  with compounding parameter uncertainty. Report seed variability across runs rather
  than a single trajectory, using S14's harness if it is available by then.
- **Confirmation pressure.** This is a proposal the source material advocates, which
  makes it the notebook most at risk of being written to produce the desired answer.
  The matched-revenue comparison is the guard, and reporting an unfavourable result
  is an acceptable and expected outcome of the stage.

## 8. Out of scope

Temporary-ownership mechanisms beyond the endowment — co-management, voting-rights
schemes, and the corporate-governance side of the proposal — which are governance
questions this wealth-accumulation engine cannot represent. The notebook says so
rather than approximating them.

## 9. Pinned results

*To be completed at implementation.*

| Quantity | Expected | Observed |
|---|---|---|
| Funding schedule required for 60%-of-mean endowment | — | — |
| Bottom-50% share, baseline / with endowment | rises | — |
| Rank-rank slope, baseline / with endowment | falls | — |
| Circulation rate | — | — |
| Endowment vs matched-revenue transfer, top-1% share | — | — |
