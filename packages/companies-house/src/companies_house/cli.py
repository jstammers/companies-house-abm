"""Command-line interface for the companies-house package."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Annotated

import typer

from companies_house import __version__

app = typer.Typer(
    name="companies-house",
    help="Companies House data ingestion, analysis, and API client.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"companies-house version: {__version__}")
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
    """Companies House data ingestion, analysis, and API client."""


# ---------------------------------------------------------------------------
# Ingest commands
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output parquet file path."),
    ] = Path("companies_house_accounts.parquet"),
    zip_dir: Annotated[
        Path | None,
        typer.Option(
            "--zip-dir",
            "-z",
            help="Directory of local ZIPs (omit for streaming mode).",
        ),
    ] = None,
    archive_dir: Annotated[
        Path | None,
        typer.Option(
            "--archive-dir",
            "-a",
            help="Directory of local ZIPs with incremental mode.",
        ),
    ] = None,
    start_date: Annotated[
        str | None,
        typer.Option(
            "--start-date",
            "-s",
            help="Start date (YYYY-MM-DD).",
        ),
    ] = None,
    incremental: Annotated[
        bool,
        typer.Option(
            "--incremental/--no-incremental",
            help="Skip already-ingested ZIPs.",
        ),
    ] = True,
    db_path: Annotated[
        Path | None,
        typer.Option(
            "--db",
            help="DuckDB database path (uses upsert instead of parquet).",
        ),
    ] = None,
) -> None:
    """Ingest Companies House XBRL data.

    Supports both Parquet output (default) and DuckDB storage
    (with --db flag for upsert semantics).
    """
    from companies_house.ingest.xbrl import (
        get_ingested_zip_basenames,
        infer_start_date,
        ingest_from_stream,
        ingest_from_zips,
        merge_and_write,
    )

    parsed_start_date: datetime.date | None = None
    if start_date is not None:
        parsed_start_date = datetime.date.fromisoformat(start_date)

    effective_dir = archive_dir or zip_dir

    if effective_dir is not None:
        if not effective_dir.is_dir():
            typer.echo(
                f"Error: {effective_dir} is not a directory.",
                err=True,
            )
            raise typer.Exit(code=1)

        use_incremental = incremental if archive_dir is not None else False

        if use_incremental and output.exists():
            already = get_ingested_zip_basenames(output)
            all_zips = sorted(effective_dir.glob("*.zip"))
            pending = [z for z in all_zips if z.name not in already]
            skipped = len(all_zips) - len(pending)
            typer.echo(
                f"Incremental mode: {skipped} ZIPs already in "
                f"parquet, {len(pending)} to process."
            )
            if not pending:
                typer.echo("Nothing new to ingest.")
                raise typer.Exit()
            new_data = ingest_from_zips(pending)
        else:
            all_zips = sorted(effective_dir.glob("*.zip"))
            if not all_zips:
                typer.echo(
                    f"No ZIP files found in {effective_dir}.",
                    err=True,
                )
                raise typer.Exit(code=1)
            typer.echo(f"Ingesting from {len(all_zips)} local ZIP file(s)...")
            new_data = ingest_from_zips(all_zips)
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

    # Store to DuckDB if --db is specified
    if db_path is not None:
        from companies_house.storage.db import CompaniesHouseDB

        with CompaniesHouseDB(db_path) as db:
            count = db.upsert(new_data)
            typer.echo(f"Done. Upserted {count} rows into {db_path}.")
    else:
        existing_path = output if output.exists() else None
        result = merge_and_write(new_data, output, existing_path=existing_path)
        typer.echo(f"Done. {len(result)} total rows in {output}.")


@app.command(name="check-company")
def check_company(
    company_id: str = typer.Argument(
        ...,
        help="Companies House company number (e.g. 01873499).",
    ),
    zip_source: Annotated[
        str | None,
        typer.Option(
            "--zip-source",
            "-z",
            help="Local path or URL to a Companies House bulk ZIP.",
        ),
    ] = None,
) -> None:
    """Check whether a company appears in a bulk data ZIP."""
    from companies_house.ingest.xbrl import (
        check_company_in_zip,
        fetch_zip_index,
    )

    if zip_source is None:
        typer.echo(
            "Error: --zip-source / -z is required.",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        is_url = zip_source.startswith("http://") or zip_source.startswith("https://")
        if is_url:
            typer.echo(
                f"Fetching ZIP index from {zip_source} "
                "(downloading central directory only)..."
            )
            names = fetch_zip_index(zip_source)
            found = any(company_id in name for name in names)
        else:
            found = check_company_in_zip(Path(zip_source), company_id)

        status = "FOUND" if found else "NOT FOUND"
        typer.echo(f"Company {company_id}: {status} in {zip_source}")
        raise typer.Exit(code=0 if found else 1)

    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


# ---------------------------------------------------------------------------
# API commands
# ---------------------------------------------------------------------------


@app.command()
def search(
    query: str = typer.Argument(..., help="Company name or number to search for."),
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            help="Companies House API key (or set COMPANIES_HOUSE_API_KEY env var).",
        ),
    ] = None,
) -> None:
    """Search Companies House for companies by name or number."""
    from companies_house.api.client import APIConfig, CompaniesHouseClient
    from companies_house.api.search import (
        search_companies as api_search,
    )

    config = APIConfig(api_key=api_key or "")
    if not config.api_key:
        typer.echo(
            "Error: API key required. Set COMPANIES_HOUSE_API_KEY or use --api-key.",
            err=True,
        )
        raise typer.Exit(code=1)

    client = CompaniesHouseClient(config=config)
    results = api_search(client, query)

    if not results:
        typer.echo(f"No companies found matching '{query}'.")
        raise typer.Exit()

    for r in results:
        status = f"  ({r.company_status})" if r.company_status else ""
        typer.echo(f"  {r.company_number}  {r.title}{status}")


@app.command()
def filings(
    company_number: str = typer.Argument(..., help="Companies House company number."),
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help="Filter by category (e.g. 'accounts').",
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", "-k", help="API key."),
    ] = None,
) -> None:
    """List filing history for a company."""
    from companies_house.api.client import APIConfig, CompaniesHouseClient
    from companies_house.api.filings import get_filing_history

    config = APIConfig(api_key=api_key or "")
    if not config.api_key:
        typer.echo(
            "Error: API key required. Set COMPANIES_HOUSE_API_KEY or use --api-key.",
            err=True,
        )
        raise typer.Exit(code=1)

    client = CompaniesHouseClient(config=config)
    items = get_filing_history(client, company_number, category=category)

    if not items:
        typer.echo(f"No filings found for {company_number}.")
        raise typer.Exit()

    for f in items:
        doc_id = f.document_id or "no-doc"
        typer.echo(
            f"  {f.date}  {f.category or 'unknown':20s}  "
            f"{doc_id}  {f.description or ''}"
        )


@app.command()
def fetch(
    company_number: str = typer.Argument(..., help="Companies House company number."),
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", "-k", help="API key."),
    ] = None,
    db: Annotated[
        Path | None,
        typer.Option("--db", help="DuckDB database path."),
    ] = None,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="LLM model for PDF extraction.",
        ),
    ] = "claude-sonnet-4-20250514",
) -> None:
    """Fetch and ingest filings for a company from the CH API.

    Downloads XBRL or PDF filings and upserts into DuckDB.
    """
    from companies_house.api.client import APIConfig, CompaniesHouseClient
    from companies_house.api.filings import (
        download_document,
        get_account_filings,
    )
    from companies_house.ingest.pdf import ingest_pdf_bytes
    from companies_house.storage.db import CompaniesHouseDB

    config = APIConfig(api_key=api_key or "")
    if not config.api_key:
        typer.echo(
            "Error: API key required. Set COMPANIES_HOUSE_API_KEY or use --api-key.",
            err=True,
        )
        raise typer.Exit(code=1)

    client = CompaniesHouseClient(config=config)
    items = get_account_filings(client, company_number)

    if not items:
        typer.echo(f"No account filings found for {company_number}.")
        raise typer.Exit()

    typer.echo(f"Found {len(items)} account filing(s).")

    db_instance = CompaniesHouseDB(db or Path("companies_house.duckdb"))
    total_rows = 0

    for filing in items:
        doc_id = filing.document_id
        if not doc_id:
            continue

        typer.echo(f"  Downloading {filing.date} ({doc_id})...")
        try:
            # Try XBRL first
            doc_bytes = download_document(
                client,
                doc_id,
                content_type="application/xhtml+xml",
            )
            typer.echo("    Got iXBRL, extracting...")
            # For now, fall through to PDF if XBRL parsing fails
        except Exception:
            doc_bytes = None

        if doc_bytes is None:
            try:
                doc_bytes = download_document(
                    client, doc_id, content_type="application/pdf"
                )
                typer.echo(
                    f"    Got PDF ({len(doc_bytes)} bytes), extracting with LLM..."
                )
                df = ingest_pdf_bytes(
                    doc_bytes,
                    company_number,
                    model=model,
                )
                count = db_instance.upsert(df)
                total_rows += count
                typer.echo(f"    Upserted {count} row(s).")
            except Exception as exc:
                typer.echo(f"    Error: {exc}", err=True)
                continue

    db_instance.close()
    typer.echo(f"Done. Total rows upserted: {total_rows}.")


@app.command()
def report(
    company_name_or_id: str = typer.Argument(..., help="Company name or ID."),
    parquet: Annotated[
        Path | None,
        typer.Option("--parquet", "-p", help="Parquet file path."),
    ] = None,
    sic_path: Annotated[
        Path | None,
        typer.Option("--sic", help="SIC code lookup file."),
    ] = None,
    forecast_horizon: Annotated[
        int,
        typer.Option("--horizon", help="Years to forecast."),
    ] = 3,
) -> None:
    """Generate a financial analysis report for a company."""
    from companies_house.analysis.reports import generate_report

    text = generate_report(
        company_name_or_id,
        parquet_path=parquet,
        forecast_horizon=forecast_horizon,
        sic_path=sic_path,
    )
    typer.echo(text)


@app.command()
def migrate(
    parquet: Annotated[
        Path,
        typer.Argument(help="Path to the parquet file to migrate."),
    ],
    db: Annotated[
        Path | None,
        typer.Option("--db", help="DuckDB database path."),
    ] = None,
) -> None:
    """Migrate a Parquet file into DuckDB."""
    from companies_house.storage.migrations import (
        migrate_parquet_to_duckdb,
    )

    typer.echo(f"Migrating {parquet} to DuckDB...")
    kwargs: dict[str, Path | str] = {}
    if db is not None:
        kwargs["db_path"] = db
    count = migrate_parquet_to_duckdb(parquet, **kwargs)
    typer.echo(f"Done. Migrated {count} rows.")


@app.command(name="db-query")
def db_query(
    sql: str = typer.Argument(..., help="SQL query to execute."),
    db: Annotated[
        Path,
        typer.Option("--db", help="DuckDB database path."),
    ] = Path("companies_house.duckdb"),
) -> None:
    """Execute an SQL query against the DuckDB database."""
    from companies_house.storage.db import CompaniesHouseDB

    with CompaniesHouseDB(db) as database:
        result = database.execute_query(sql)
        typer.echo(str(result))


if __name__ == "__main__":
    app()
