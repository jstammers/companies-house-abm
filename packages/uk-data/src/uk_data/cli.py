"""CLI entrypoint for the uk-data package (``ukd`` command)."""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 -- Typer inspects annotations at runtime
from typing import Annotated

import typer

from uk_data.client import UKDataClient

app = typer.Typer(
    name="ukd",
    help="Fetch UK public economic and business data.",
    no_args_is_help=True,
)


def _parse_params(params: list[str]) -> dict[str, str]:
    """Parse a list of ``KEY=VALUE`` strings into a dict."""
    result: dict[str, str] = {}
    for item in params:
        if "=" not in item:
            raise typer.BadParameter(
                f"--param must be in KEY=VALUE format, got: {item!r}"
            )
        k, _, v = item.partition("=")
        result[k.strip()] = v
    return result


@app.command()
def sources() -> None:
    """List all available data sources and their series."""
    client = UKDataClient()
    for src in client.list_sources():
        series_str = ", ".join(src.series) if src.series else "(none)"
        typer.echo(f"{src.name}: {series_str}")


@app.command(name="get-series")
def get_series_cmd(
    concept: str = typer.Argument(..., help="Concept name, e.g. 'gdp' or 'bank_rate'."),
    source: str | None = typer.Option(
        None, "--source", "-s", help="Preferred data source adapter name."
    ),
    limit: int | None = typer.Option(
        None, "--limit", "-n", help="Maximum number of observations to return."
    ),
    start_date: str | None = typer.Option(
        None,
        "--start-date",
        help=(
            "Inclusive start date (ISO). Limit-only remains supported for "
            "backward compatibility, but explicit date windows are preferred."
        ),
    ),
    end_date: str | None = typer.Option(
        None,
        "--end-date",
        help=(
            "Inclusive end date (ISO). When used with --limit, filtering occurs "
            "before limit slicing."
        ),
    ),
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data-path",
            "-d",
            help=(
                "Directory for cached/downloaded data files "
                "(required for some series, e.g. uk_hpi_full). "
                "Defaults to platform cache dir."
            ),
        ),
    ] = None,
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output format: 'json' or 'text' (default)."
    ),
) -> None:
    """Fetch a canonical time series by concept name.

    Migration semantics: limit-only calls are still supported for backward
    compatibility; explicit ``--start-date``/``--end-date`` windows are the
    preferred bounded API. When both window and limit are provided, filtering
    occurs before limit slicing.
    """
    client = UKDataClient()
    series_kwargs: dict[str, object] = {}
    # Only concepts backed by a local file require a filepath; e.g. land
    # registry's full UK HPI CSV.  Injecting the cache directory for other
    # concepts would just confuse their adapters.
    if data_path is not None:
        series_kwargs["filepath"] = str(data_path)
    if isinstance(start_date, str) and start_date.strip():
        series_kwargs["start_date"] = start_date
    if isinstance(end_date, str) and end_date.strip():
        series_kwargs["end_date"] = end_date
    ts = client.get_series(
        concept,
        source=source,
        limit=limit if limit is not None else 20,
        **series_kwargs,
    )
    if output == "json":
        data = {
            "concept": concept,
            "source": ts.source,
            "series_id": ts.series_id,
            "latest_value": ts.latest_value,
            "observations": [
                {"date": str(d), "value": float(v)}
                for d, v in zip(ts.timestamps, ts.values, strict=True)
            ],
        }
        typer.echo(json.dumps(data, indent=2))
    else:
        typer.echo(f"concept:      {concept}")
        typer.echo(f"source:       {ts.source}")
        typer.echo(f"series_id:    {ts.series_id}")
        typer.echo(f"latest_value: {ts.latest_value}")
        n = len(ts.timestamps)
        if n > 0:
            typer.echo(f"observations: {n} data points")
            typer.echo(f"  first: {ts.timestamps[0]}  {ts.values[0]}")
            typer.echo(f"  last:  {ts.timestamps[-1]}  {ts.values[-1]}")


@app.command()
def entities() -> None:
    """List sources that expose entity lookup and their entity types."""
    client = UKDataClient()
    rows = client.list_entities()
    if not rows:
        typer.echo("No sources expose entity lookup.")
        return
    for info in rows:
        types_str = ", ".join(info.entity_types)
        typer.echo(f"{info.source}: {types_str}")


@app.command()
def events() -> None:
    """List sources that expose event streams and their event types."""
    client = UKDataClient()
    rows = client.list_events()
    if not rows:
        typer.echo("No sources expose event streams.")
        return
    for info in rows:
        types_str = ", ".join(info.event_types)
        typer.echo(f"{info.source}: {types_str}")


@app.command(name="get-entity")
def get_entity(
    name: str = typer.Argument(..., help="Entity name or ID to look up."),
    source: str = typer.Option(
        "companies_house",
        "--source",
        "-s",
        help="Data source adapter to query (default: companies_house).",
    ),
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data-path",
            "-d",
            help=(
                "Directory for cached/downloaded data files. "
                "Defaults to platform cache dir."
            ),
        ),
    ] = None,
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output format: 'json' or 'text' (default)."
    ),
) -> None:
    """Fetch a single entity by name or ID from the specified source."""
    del data_path  # reserved for future file-backed entity sources
    client = UKDataClient()
    entity = client.get_entity(name, source=source)
    if entity is None:
        typer.echo(f"Entity not found: {name!r}", err=True)
        raise typer.Exit(code=1)
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "entity_id": entity.entity_id,
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "source": entity.source,
                    "source_id": entity.source_id,
                    "attributes": entity.attributes,
                },
                indent=2,
                default=str,
            )
        )
    else:
        typer.echo(f"entity_id:   {entity.entity_id}")
        typer.echo(f"name:        {entity.name}")
        typer.echo(f"entity_type: {entity.entity_type}")
        typer.echo(f"source:      {entity.source}")
        typer.echo(f"source_id:   {entity.source_id}")
        if entity.attributes:
            typer.echo("attributes:")
            for k, v in entity.attributes.items():
                typer.echo(f"  {k}: {v}")


@app.command(name="get-events")
def get_events(
    source: str = typer.Option(
        "companies_house",
        "--source",
        "-s",
        help="Data source adapter to query (default: companies_house).",
    ),
    entity_id: str | None = typer.Option(
        None, "--entity-id", "-e", help="Filter events to this entity ID."
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", "-t", help="Filter events by type."
    ),
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data-path",
            "-d",
            help=(
                "Directory for cached/downloaded data files "
                "(required for land_registry and epc sources). "
                "Defaults to platform cache dir."
            ),
        ),
    ] = None,
    limit: int | None = typer.Option(
        None, "--limit", "-n", help="Maximum number of events to return."
    ),
    param: Annotated[
        list[str],
        typer.Option(
            "--param",
            "-p",
            help="Extra adapter parameter as KEY=VALUE (repeatable).",
        ),
    ] = [],  # noqa: B006
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output format: 'json' or 'text' (default)."
    ),
) -> None:
    """Fetch events from the specified source with optional filters."""
    extra = _parse_params(param)
    kwargs: dict[str, object] = dict(extra)
    if limit is not None:
        kwargs["limit"] = limit
    if (
        source in ("land_registry", "epc")
        and "filepath" not in kwargs
        and data_path is not None
    ):
        kwargs["filepath"] = str(data_path)

    client = UKDataClient()
    event_list = client.get_events(
        entity_id=entity_id,
        event_type=event_type,
        source=source,
        **kwargs,
    )

    if output == "json":
        typer.echo(
            json.dumps(
                [
                    {
                        "event_id": ev.event_id,
                        "entity_id": ev.entity_id,
                        "event_type": ev.event_type,
                        "timestamp": str(ev.timestamp),
                        "source": ev.source,
                        "payload": ev.payload,
                    }
                    for ev in event_list
                ],
                indent=2,
                default=str,
            )
        )
    else:
        if not event_list:
            typer.echo("No events found.")
            return
        for ev in event_list:
            typer.echo(
                f"[{ev.timestamp}] {ev.event_type} | {ev.entity_id} | {ev.event_id}"
            )
            if ev.payload:
                for k, v in ev.payload.items():
                    typer.echo(f"  {k}: {v}")
