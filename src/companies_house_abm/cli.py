"""Command-line interface for companies_house_abm."""

import datetime
from pathlib import Path
from typing import Annotated

import typer

from companies_house_abm import __version__

app = typer.Typer(
    name="companies_house_abm",
    help="Agent-Based Modelling using Companies House Account Data",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"companies_house_abm version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Agent-Based Modelling using Companies House Account Data."""


@app.command()
def hello(
    name: str = typer.Argument("World", help="Name to greet"),
) -> None:
    """Say hello to someone."""
    typer.echo(f"Hello, {name}!")


@app.command()
def ingest(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output parquet file path.",
        ),
    ] = Path("companies_house_accounts.parquet"),
    zip_dir: Annotated[
        Path | None,
        typer.Option(
            "--zip-dir",
            "-z",
            help="Directory of local ZIPs (omit for streaming mode).",
        ),
    ] = None,
    start_date: Annotated[
        str | None,
        typer.Option(
            "--start-date",
            "-s",
            help="Start date (YYYY-MM-DD). Omit to infer from existing parquet.",
        ),
    ] = None,
) -> None:
    """Ingest Companies House XBRL data into a parquet file."""
    from companies_house_abm.ingest import (
        infer_start_date,
        ingest_from_stream,
        ingest_from_zips,
        merge_and_write,
    )

    parsed_start_date: datetime.date | None = None
    if start_date is not None:
        parsed_start_date = datetime.date.fromisoformat(start_date)

    if zip_dir is not None:
        if not zip_dir.is_dir():
            typer.echo(f"Error: {zip_dir} is not a directory.", err=True)
            raise typer.Exit(code=1)
        zip_paths = sorted(zip_dir.glob("*.zip"))
        if not zip_paths:
            typer.echo(f"No ZIP files found in {zip_dir}.", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"Ingesting from {len(zip_paths)} local ZIP file(s)...")
        new_data = ingest_from_zips(zip_paths)
    else:
        effective_date = parsed_start_date or infer_start_date(output)
        if effective_date is not None:
            typer.echo(f"Streaming data after {effective_date}...")
        else:
            typer.echo("Streaming all available data...")
        new_data = ingest_from_stream(start_date=effective_date)

    if new_data.is_empty():
        typer.echo("No new data ingested.")
        raise typer.Exit()

    existing_path = output if output.exists() else None
    result = merge_and_write(new_data, output, existing_path=existing_path)
    typer.echo(f"Done. {len(result)} total rows in {output}.")


@app.command()
def serve(
    host: str = typer.Option(
        "127.0.0.1", "--host", "-H", help="Host to bind the server to."
    ),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for development."
    ),
) -> None:
    """Launch the economy simulator web application."""
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "uvicorn is not installed. Install the ABM extras:\n  uv sync --all-groups",
            err=True,
        )
        raise typer.Exit(code=1) from None

    typer.echo(f"Starting economy simulator at http://{host}:{port}")
    uvicorn.run(
        "companies_house_abm.webapp.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
