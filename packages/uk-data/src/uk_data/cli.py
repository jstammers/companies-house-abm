"""CLI entrypoint for the uk-data package (``ukd`` command)."""

from __future__ import annotations

import json

import typer

from uk_data.client import UKDataClient

app = typer.Typer(
    name="ukd",
    help="Fetch UK public economic and business data.",
    no_args_is_help=True,
)


@app.command()
def sources() -> None:
    """List all available data sources and their series."""
    client = UKDataClient()
    for src in client.list_sources():
        series_str = ", ".join(src.series) if src.series else "(none)"
        typer.echo(f"{src.name}: {series_str}")


@app.command()
def series(
    concept: str = typer.Argument(..., help="Concept name, e.g. 'gdp' or 'bank_rate'."),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output format: 'json' or 'text' (default)."
    ),
) -> None:
    """Fetch a canonical time series by concept name."""
    client = UKDataClient()
    ts = client.get_series(concept)
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
