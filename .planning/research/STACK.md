# Stack Research

## Recommended Stack for This Refactor

- Python 3.10+ with existing uv workspace and hatchling package boundaries.
- Keep adapter contracts in `uk-data` with `typing.Protocol` or ABC-based interfaces (current pattern already in `adapters/base.py`).
- Use existing canonical models (`TimeSeries`, `Entity`, `Event`) for cross-layer handoff.
- Keep persistence optional and DuckDB-backed via existing storage modules.

## Library/Pattern Guidance

- Prefer composition over inheritance for high-level utilities that orchestrate multiple adapters.
- Use explicit date interval parameters (`start_date`, `end_date`) at utility entry points and pass through to adapter queries.
- Keep adapter return normalization in one place (utility layer), not spread across callers.

## Avoid

- Adding new third-party orchestration dependencies for this refactor.
- Embedding ABM-specific business logic in `uk-data` utility modules.
- Maintaining implicit default-limit-only pathways for new time-series calls.

## Confidence

- High: approach aligns with current repository architecture and package boundaries.
