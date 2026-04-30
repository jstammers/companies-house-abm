"""Command-line interface for companies_house_abm."""

import datetime
import warnings
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
    archive_dir: Annotated[
        Path | None,
        typer.Option(
            "--archive-dir",
            "-a",
            help=(
                "Directory of local ZIPs — like --zip-dir but defaults to "
                "incremental mode (skip ZIPs already in the output parquet)."
            ),
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
    incremental: Annotated[
        bool,
        typer.Option(
            "--incremental/--no-incremental",
            help=(
                "Skip ZIPs whose basenames are already recorded in the output "
                "parquet. Applies when --archive-dir or --zip-dir is used. "
                "Default: True for --archive-dir, False for --zip-dir."
            ),
        ),
    ] = True,
) -> None:
    """Ingest Companies House XBRL data into a parquet file.

    Both old-style XML XBRL archives (pre-2014) and modern iXBRL HTML archives
    are handled automatically by the underlying parser.

    Examples:

    \\b
        # Incremental ingest from local archive (skips already-processed ZIPs)
        companies_house_abm ingest --archive-dir data/archive -o data/ch.parquet

    \\b
        # Force re-process every ZIP in a directory
        companies_house_abm ingest --archive-dir data/archive --no-incremental

    \\b
        # Stream new data from Companies House API
        companies_house_abm ingest -o data/ch.parquet
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
            typer.echo(f"Error: {effective_dir} is not a directory.", err=True)
            raise typer.Exit(code=1)

        # --archive-dir defaults to incremental; --zip-dir defaults to non-incremental
        use_incremental = incremental if archive_dir is not None else False

        if use_incremental and output.exists():
            already = get_ingested_zip_basenames(output)
            all_zips = sorted(effective_dir.glob("*.zip"))
            pending = [z for z in all_zips if z.name not in already]
            skipped = len(all_zips) - len(pending)
            typer.echo(
                f"Incremental mode: {skipped} ZIPs already in parquet, "
                f"{len(pending)} to process."
            )
            if not pending:
                typer.echo("Nothing new to ingest.")
                raise typer.Exit()
            new_data = ingest_from_zips(pending)
        else:
            all_zips = sorted(effective_dir.glob("*.zip"))
            if not all_zips:
                typer.echo(f"No ZIP files found in {effective_dir}.", err=True)
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

    existing_path = output if output.exists() else None
    result = merge_and_write(new_data, output, existing_path=existing_path)
    typer.echo(f"Done. {len(result)} total rows in {output}.")


@app.command(name="check-company")
def check_company(
    company_id: str = typer.Argument(
        ...,
        help=(
            "Companies House company number to search for "
            "(e.g. 01873499 for Exel Computer Systems PLC)."
        ),
    ),
    zip_source: Annotated[
        str | None,
        typer.Option(
            "--zip-source",
            "-z",
            help=(
                "Local path or HTTP/HTTPS URL to a Companies House bulk data ZIP. "
                "For remote URLs only the central directory is downloaded "
                "(at most 64 MB), not the full archive."
            ),
        ),
    ] = None,
) -> None:
    """Check whether a company appears in a Companies House bulk data ZIP.

    Works with both local archive files and remote URLs.  For remote ZIPs the
    full archive is NOT downloaded — only the central directory (the file index
    at the end of the ZIP) is fetched via an HTTP Range request.

    Examples:

    \\b
        # Check a local archive file
        companies_house_abm check-company 01873499 \\
            --zip-source data/archive/Accounts_Monthly_Data-April2025.zip

    \\b
        # Check a remote file without downloading it
        companies_house_abm check-company 01873499 \\
            --zip-source https://download.companieshouse.gov.uk/Accounts_Monthly_Data-April2025.zip

    Exit codes: 0 = found, 1 = not found, 2 = error.
    """
    from companies_house.ingest.xbrl import check_company_in_zip, fetch_zip_index

    if zip_source is None:
        typer.echo(
            "Error: --zip-source / -z is required. Provide a local path or URL.",
            err=True,
        )
        raise typer.Exit(code=2)

    def _segment_match(name: str, cid: str) -> bool:
        """Match company ID against the 3rd underscore-separated segment."""
        parts = name.rsplit("/", 1)[-1].split("_")
        return len(parts) >= 3 and parts[2] == cid

    try:
        if zip_source.startswith("http://") or zip_source.startswith("https://"):
            typer.echo(
                f"Fetching ZIP index from {zip_source} "
                "(downloading central directory only)..."
            )
            names = fetch_zip_index(zip_source)
            found = any(_segment_match(n, company_id) for n in names)
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


@app.command(name="fetch-data")
def fetch_data(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory to write cached data files.",
        ),
    ] = Path("data"),
    sources: Annotated[
        list[str] | None,
        typer.Option(
            "--source",
            "-s",
            help=(
                "Data source to fetch: ons, boe, hmrc, io-tables, sic, "
                "historical, land-registry, all. "
                "May be repeated. Defaults to all."
            ),
        ),
    ] = None,
    calibrate: Annotated[
        bool,
        typer.Option(
            "--calibrate/--no-calibrate",
            help="Write a calibrated model_parameters.yml to the output directory.",
        ),
    ] = False,
) -> None:
    """Fetch publicly available UK economic data for ABM calibration.

    Downloads data from ONS, Bank of England, HMRC, HM Land Registry, and
    Companies House to calibrate household income, government tax rates,
    bank interest rates, firm input-output production relations, and
    housing market parameters.

    Examples:

    \\b
        # Fetch all sources and save to ./data/
        companies_house_abm fetch-data

    \\b
        # Fetch only ONS and BoE data
        companies_house_abm fetch-data --source ons --source boe

    \\b
        # Fetch all data and write a calibrated config
        companies_house_abm fetch-data --calibrate --output ./calibrated/
    """

    from companies_house_abm.data_sources.boe import (
        fetch_bank_rate_current,
        fetch_lending_rates,
        get_aggregate_capital_ratio,
    )
    from companies_house_abm.data_sources.hmrc import (
        effective_tax_wedge,
        get_corporation_tax_rate,
        get_income_tax_bands,
        get_national_insurance_rates,
        get_vat_rate,
    )
    from companies_house_abm.data_sources.ons import (
        fetch_affordability_ratio,
        fetch_gdp,
        fetch_household_income,
        fetch_input_output_table,
        fetch_labour_market,
        fetch_rental_growth,
        fetch_savings_ratio,
        fetch_tenure_distribution,
    )

    requested = set(sources) if sources else {"all"}
    fetch_all = "all" in requested

    output.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Writing data to {output}/")

    # ------------------------------------------------------------------ ONS
    if fetch_all or "ons" in requested:
        typer.echo("Fetching ONS data...")

        gdp = fetch_gdp(limit=20)
        _write_json(output / "ons_gdp.json", gdp)
        typer.echo(f"  GDP: {len(gdp)} observations → ons_gdp.json")

        hh_income = fetch_household_income(limit=20)
        _write_json(output / "ons_household_income.json", hh_income)
        typer.echo(
            f"  Household income: {len(hh_income)} observations"
            " -> ons_household_income.json"
        )

        savings = fetch_savings_ratio(limit=20)
        _write_json(output / "ons_savings_ratio.json", savings)
        typer.echo(
            f"  Savings ratio: {len(savings)} observations -> ons_savings_ratio.json"
        )

        labour = fetch_labour_market()
        _write_json(output / "ons_labour_market.json", labour)
        typer.echo(
            f"  Labour market: unemployment={labour.get('unemployment_rate')}%"
            " -> ons_labour_market.json"
        )

        tenure = fetch_tenure_distribution()
        affordability = fetch_affordability_ratio()
        rental_growth = fetch_rental_growth()
        ons_housing_data = {
            "tenure_distribution": tenure,
            "affordability_ratio": affordability,
            "rental_growth": rental_growth,
        }
        _write_json(output / "ons_housing.json", ons_housing_data)
        typer.echo(
            f"  Housing: affordability={affordability:.1f}x,"
            f" rental growth={rental_growth:.1%} -> ons_housing.json"
        )

    # ------------------------------------------------------------ IO tables
    if fetch_all or "io-tables" in requested:
        typer.echo("Fetching ONS Input-Output tables...")
        io = fetch_input_output_table()
        _write_json(output / "ons_io_tables.json", io)
        typer.echo(f"  IO table: {len(io['sectors'])} sectors -> ons_io_tables.json")

    # ------------------------------------------------------------------ BoE
    if fetch_all or "boe" in requested:
        typer.echo("Fetching Bank of England data...")

        bank_rate = fetch_bank_rate_current()
        lending = fetch_lending_rates()
        cet1 = get_aggregate_capital_ratio()
        boe_data = {
            "bank_rate": bank_rate,
            "lending_rates": lending,
            "aggregate_cet1_ratio": cet1,
        }
        _write_json(output / "boe_rates.json", boe_data)
        typer.echo(f"  Bank Rate: {bank_rate:.2%}, CET1: {cet1:.1%} -> boe_rates.json")

    # ----------------------------------------------------------------- HMRC
    if fetch_all or "hmrc" in requested:
        typer.echo("Fetching HMRC tax data...")

        bands = get_income_tax_bands()
        ni = get_national_insurance_rates()
        corp_tax = get_corporation_tax_rate()
        vat = get_vat_rate()
        # Illustrative tax wedge at mean income
        wedge = effective_tax_wedge(35_000.0)

        hmrc_data = {
            "income_tax_bands": [
                {
                    "name": b.name,
                    "lower": b.lower,
                    "upper": b.upper,
                    "rate": b.rate,
                }
                for b in bands
            ],
            "national_insurance": {
                "employee_main_rate": ni.employee_main_rate,
                "employee_upper_rate": ni.employee_upper_rate,
                "employer_rate": ni.employer_rate,
                "primary_threshold": ni.primary_threshold,
                "upper_earnings_limit": ni.upper_earnings_limit,
            },
            "corporation_tax_main_rate": corp_tax,
            "vat_standard_rate": vat,
            "tax_wedge_at_35k": wedge,
        }
        _write_json(output / "hmrc_tax.json", hmrc_data)
        typer.echo(
            f"  Corp tax: {corp_tax:.0%}, VAT: {vat:.0%}"
            f", effective wedge at 35k: {wedge['effective_rate']:.1%}"
            " -> hmrc_tax.json"
        )

    # -------------------------------------------------- SIC codes (Companies House)
    if fetch_all or "sic" in requested:
        typer.echo("Fetching Companies House SIC codes (bulk download ~400 MB)...")
        from companies_house_abm.data_sources.companies_house import fetch_sic_codes

        sic_output = output / "sic_codes.parquet"
        try:
            df = fetch_sic_codes(output_path=sic_output)
            typer.echo(f"  SIC codes: {len(df):,} companies -> {sic_output.name}")
        except RuntimeError as exc:
            typer.echo(f"  Warning: could not fetch SIC codes: {exc}", err=True)

    # ----------------------------------------------- Historical time-series
    if fetch_all or "historical" in requested:
        typer.echo("Fetching historical quarterly time-series data...")
        from uk_data.adapters.historical import (
            fetch_all_historical,
        )

        historical = fetch_all_historical()
        _write_json(output / "historical_quarterly.json", historical)
        n_quarters = len(next(iter(historical.values()), []))
        typer.echo(
            f"  Historical data: {len(historical)} series,"
            f" {n_quarters} quarters -> historical_quarterly.json"
        )

    # ---------------------------------------------------- HM Land Registry
    if fetch_all or "land-registry" in requested:
        typer.echo("Fetching HM Land Registry house price data...")
        from companies_house_abm.data_sources.land_registry import (
            fetch_regional_prices,
            fetch_uk_average_price,
        )

        regional = fetch_regional_prices()
        uk_avg = fetch_uk_average_price()
        lr_data = {
            "uk_average_price": uk_avg,
            "regional_prices": regional,
        }
        _write_json(output / "land_registry_prices.json", lr_data)
        typer.echo(
            f"  Land Registry: UK avg £{uk_avg:,.0f},"
            f" {len(regional)} regions -> land_registry_prices.json"
        )

    # ----------------------------------------------------------- Calibration
    if calibrate:
        typer.echo("Generating calibrated model parameters...")
        from companies_house_abm.data_sources.calibration import calibrate_model

        calibrated = calibrate_model()
        cfg_path = output / "model_parameters_calibrated.yml"
        _write_calibrated_yaml(calibrated, cfg_path)
        typer.echo(f"  Calibrated config written -> {cfg_path}")

    typer.echo("Done.")


def _write_json(path: Path, data: object) -> None:
    """Write *data* as pretty-printed JSON to *path*."""
    import json as _json

    path.write_text(_json.dumps(data, indent=2, default=str), encoding="utf-8")


def _write_calibrated_yaml(config: object, path: Path) -> None:
    """Write a calibrated ModelConfig as a YAML file."""
    import dataclasses

    import yaml

    def _to_dict(obj: object) -> object:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {
                f.name: _to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)
            }
        if isinstance(obj, tuple):
            return list(obj)
        return obj

    path.write_text(
        yaml.dump(_to_dict(config), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


@app.command(name="profile-firms")
def profile_firms(
    parquet: Annotated[
        Path,
        typer.Option(
            "--parquet",
            "-p",
            help="Path to Companies House accounts parquet file.",
        ),
    ] = Path("data/companies_house_accounts.parquet"),
    sic_file: Annotated[
        Path | None,
        typer.Option(
            "--sic-file",
            "-s",
            help=(
                "Path to SIC code lookup (parquet or CSV) with columns "
                "'companies_house_registered_number' and 'sic_code'."
            ),
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output file for fitted distribution parameters.",
        ),
    ] = Path("data/firm_distribution_parameters.yml"),
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: yaml or json.",
        ),
    ] = "yaml",
    sample: Annotated[
        float | None,
        typer.Option(
            "--sample",
            help=(
                "Fraction of data to sample (e.g. 0.01 for 1%%)."
                " Useful for large datasets."
            ),
        ),
    ] = None,
) -> None:
    """Profile firm financial data and fit statistical distributions.

    Analyses Companies House accounts data to generate per-sector,
    per-financial-year distribution parameters suitable for initialising
    firm agents in the ABM simulation.

    Examples:

    \\b
        # Profile all data (may be slow for large datasets)
        companies_house_abm profile-firms

    \\b
        # Profile a 1%% sample with SIC code lookup
        companies_house_abm profile-firms --sample 0.01 --sic-file data/sic_codes.csv

    \\b
        # Output as JSON
        companies_house_abm profile-firms --format json -o data/params.json
    """
    from companies_house_abm.data_sources.firm_distributions import (
        run_profile_pipeline,
    )

    if not parquet.exists():
        typer.echo(f"Error: parquet file not found: {parquet}", err=True)
        raise typer.Exit(code=1)

    if output_format not in ("yaml", "json"):
        typer.echo(f"Error: unsupported format '{output_format}'", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Profiling firm data from {parquet}...")
    if sample is not None:
        typer.echo(f"  Sampling {sample:.1%} of data")
    if sic_file is not None:
        typer.echo(f"  Using SIC codes from {sic_file}")

    summary = run_profile_pipeline(
        parquet_path=parquet,
        sic_path=sic_file,
        output_path=output,
        output_format=output_format,
        sample_fraction=sample,
    )

    typer.echo(
        f"Done. Fitted {len(summary.parameters)} sector-year parameter sets"
        f" across {len(summary.sectors)} sectors"
        f" and {len(summary.financial_years)} financial years."
    )
    typer.echo(f"Parameters written to {output}")


@app.command(name="run-simulation")
def run_simulation(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help=(
                "Path to model YAML config file. "
                "Defaults to config/model_parameters.yml."
            ),
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory to write results.",
        ),
    ] = Path("results"),
    periods: Annotated[
        int | None,
        typer.Option(
            "--periods",
            "-n",
            help="Number of periods to simulate. Overrides config value.",
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format for time-series data: csv, json, or parquet.",
        ),
    ] = "csv",
    evaluate: Annotated[
        bool,
        typer.Option(
            "--evaluate/--no-evaluate",
            help=(
                "Compare output to UK calibration targets "
                "and print an evaluation report."
            ),
        ),
    ] = False,
    warm_up: Annotated[
        int,
        typer.Option(
            "--warm-up",
            "-w",
            help=(
                "Number of leading periods to skip when computing "
                "evaluation statistics."
            ),
        ),
    ] = 0,
) -> None:
    """Run the ABM simulation and save results.

    Loads configuration from a YAML file (or built-in defaults), runs the
    simulation, and writes time-series results and optional evaluation reports
    to the output directory.

    Examples:

    \\b
        # Run with defaults and save CSV results
        companies_house_abm run-simulation

    \\b
        # Run for 40 quarters using a custom config
        companies_house_abm run-simulation --config calibrated.yml --periods 40

    \\b
        # Run and evaluate against calibration targets
        companies_house_abm run-simulation --periods 80 --evaluate --warm-up 20
    """
    from companies_house_abm.abm.config import load_config
    from companies_house_abm.abm.model import Simulation

    if output_format not in ("csv", "json", "parquet"):
        typer.echo(f"Error: unsupported format '{output_format}'", err=True)
        raise typer.Exit(code=1)

    typer.echo("Loading configuration...")
    cfg = load_config(config)
    n_periods = periods or cfg.simulation.periods
    typer.echo(
        f"Running simulation: {n_periods} periods, "
        f"{cfg.firms.sample_size} firms, "
        f"{cfg.households.count} households, "
        f"{cfg.banks.count} banks"
    )

    sim = Simulation(cfg)
    sim.initialize_agents()
    typer.echo(
        f"Agents initialised: {len(sim.firms)} firms, "
        f"{len(sim.households)} households, "
        f"{len(sim.banks)} banks"
    )

    result = sim.run(periods=n_periods)
    typer.echo(f"Simulation complete: {len(result.records)} periods recorded.")

    output.mkdir(parents=True, exist_ok=True)

    # ── Write time-series results ─────────────────────────────────────────
    import dataclasses

    records_data = [dataclasses.asdict(r) for r in result.records]

    if output_format == "json":
        _write_json(output / "simulation_results.json", records_data)
        typer.echo(f"  Results -> {output / 'simulation_results.json'}")
    elif output_format == "parquet":
        try:
            import polars as pl

            df = pl.DataFrame(records_data)
            df.write_parquet(output / "simulation_results.parquet")
            typer.echo(f"  Results -> {output / 'simulation_results.parquet'}")
        except ImportError:
            typer.echo(
                "polars is required for parquet output. Falling back to CSV.", err=True
            )
            output_format = "csv"

    if output_format == "csv":
        import csv

        csv_path = output / "simulation_results.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            if records_data:
                writer = csv.DictWriter(fh, fieldnames=records_data[0].keys())
                writer.writeheader()
                writer.writerows(records_data)
        typer.echo(f"  Results -> {csv_path}")

    # ── Evaluation ────────────────────────────────────────────────────────
    if evaluate:
        from companies_house_abm.abm.evaluation import evaluate_simulation

        typer.echo("\nEvaluating against UK calibration targets...")
        report = evaluate_simulation(result, warm_up=warm_up)
        typer.echo(report.summary())

        _write_json(output / "evaluation_report.json", report.as_dict())
        typer.echo(f"\n  Evaluation report -> {output / 'evaluation_report.json'}")

    typer.echo("Done.")


@app.command(name="run-sector-model")
def run_sector_model(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory to write results.",
        ),
    ] = Path("results/sector"),
    periods: Annotated[
        int,
        typer.Option(
            "--periods",
            "-n",
            help="Number of periods to simulate.",
        ),
    ] = 80,
    n_households: Annotated[
        int,
        typer.Option(
            "--households",
            help="Number of household agents.",
        ),
    ] = 1000,
    n_banks: Annotated[
        int,
        typer.Option(
            "--banks",
            help="Number of bank agents.",
        ),
    ] = 5,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Random seed.",
        ),
    ] = 42,
    evaluate: Annotated[
        bool,
        typer.Option(
            "--evaluate/--no-evaluate",
            help="Print evaluation report against UK calibration targets.",
        ),
    ] = True,
    warm_up: Annotated[
        int,
        typer.Option(
            "--warm-up",
            help="Periods to skip when computing evaluation statistics.",
        ),
    ] = 20,
) -> None:
    """Run the sector-representative ABM (one firm per sector).

    Creates a simplified simulation with exactly one representative firm per
    UK industry sector, calibrated to ONS Blue Book 2023 macroeconomic data.
    The aggregate of firm outputs approximates real UK GDP, employment and
    wage shares.

    Examples:

    \\b
        # Run 80 quarters and evaluate against UK targets
        companies_house_abm run-sector-model

    \\b
        # Run with a larger household population
        companies_house_abm run-sector-model --households 5000 --periods 120
    """
    import dataclasses

    from companies_house_abm.abm.sector_model import (
        SECTOR_PROFILES,
        create_sector_representative_simulation,
    )

    typer.echo(
        f"Creating sector-representative simulation: "
        f"{len(SECTOR_PROFILES)} sectors, "
        f"{n_households} households, {n_banks} banks"
    )

    sim = create_sector_representative_simulation(
        n_households=n_households,
        n_banks=n_banks,
        seed=seed,
        periods=periods,
    )

    typer.echo(
        f"Agents initialised: {len(sim.firms)} sector firms, "
        f"{len(sim.households)} households, {len(sim.banks)} banks"
    )

    # Print sector summary
    typer.echo("\nSector firms:")
    total_turnover = sum(f.turnover for f in sim.firms)
    for firm in sim.firms:
        share = firm.turnover / total_turnover if total_turnover > 0 else 0.0
        typer.echo(
            f"  {firm.sector:<30}  "
            f"turnover=£{firm.turnover / 1e9:.1f}B/q  "
            f"employees={firm.employees:,}  "
            f"share={share:.1%}"
        )
    typer.echo(f"  {'TOTAL':<30}  turnover=£{total_turnover / 1e9:.1f}B/q\n")

    result = sim.run(periods=periods)
    typer.echo(f"Simulation complete: {len(result.records)} periods.")

    output.mkdir(parents=True, exist_ok=True)

    # Write CSV results
    import csv

    records_data = [dataclasses.asdict(r) for r in result.records]
    csv_path = output / "sector_model_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        if records_data:
            writer = csv.DictWriter(fh, fieldnames=records_data[0].keys())
            writer.writeheader()
            writer.writerows(records_data)
    typer.echo(f"  Results -> {csv_path}")

    if evaluate:
        from companies_house_abm.abm.evaluation import evaluate_simulation

        typer.echo("\nEvaluating against UK calibration targets...")
        report = evaluate_simulation(result, warm_up=warm_up)
        typer.echo(report.summary())
        _write_json(output / "sector_evaluation_report.json", report.as_dict())
        report_path = output / "sector_evaluation_report.json"
        typer.echo(f"\n  Evaluation report -> {report_path}")

    typer.echo("Done.")


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
    """Launch the deprecated FastAPI economy simulator web application."""
    message = (
        "The FastAPI `serve` command is deprecated and will be removed in a future "
        "release as the project moves toward Mesa-native simulation tooling."
    )
    warnings.warn(message, DeprecationWarning, stacklevel=2)
    typer.echo(f"Deprecation warning: {message}")
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


# ---------------------------------------------------------------------------
# Housing sub-app
# ---------------------------------------------------------------------------

housing_app = typer.Typer(
    name="housing",
    help="Housing market simulation commands.",
)
app.add_typer(housing_app, name="housing")


@housing_app.command(name="simulate-historical")
def simulate_historical(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory to write results.",
        ),
    ] = Path("results/historical"),
    start: Annotated[
        str,
        typer.Option(
            "--start",
            help="Start quarter (e.g. 2013Q1).",
        ),
    ] = "2013Q1",
    end: Annotated[
        str,
        typer.Option(
            "--end",
            help="End quarter (e.g. 2024Q4).",
        ),
    ] = "2024Q4",
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: csv, json, or parquet.",
        ),
    ] = "csv",
    evaluate: Annotated[
        bool,
        typer.Option(
            "--evaluate/--no-evaluate",
            help="Compare against actual UK housing data.",
        ),
    ] = False,
) -> None:
    """Run a historical UK housing market simulation.

    Drives the ABM with actual Bank Rate, mortgage rate, and income
    data from the specified period, applying regulatory events
    (MMR, stamp duty changes, COVID measures) at their historical
    dates.  Compares simulated house prices against actual UK HPI.

    Examples:

    \\b
        # Run full 2013-2024 simulation
        companies_house_abm housing simulate-historical

    \\b
        # Run 2015-2024 with evaluation
        companies_house_abm housing simulate-historical \\
            --start 2015Q1 --evaluate

    \\b
        # Save as JSON
        companies_house_abm housing simulate-historical \\
            --format json --output results/historical
    """
    from companies_house_abm.abm.historical import HistoricalSimulation
    from companies_house_abm.abm.scenarios import build_uk_2013_2024

    if output_format not in ("csv", "json", "parquet"):
        typer.echo(f"Error: unsupported format '{output_format}'", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Building UK housing scenario ({start} to {end})...")
    scenario = build_uk_2013_2024()

    # Trim scenario to requested window
    labels = scenario.quarter_labels
    if start != "2013Q1" or end != "2024Q4":
        try:
            s_idx = labels.index(start)
        except ValueError:
            typer.echo(f"Error: invalid start quarter '{start}'", err=True)
            raise typer.Exit(code=1) from None
        try:
            e_idx = labels.index(end)
        except ValueError:
            typer.echo(f"Error: invalid end quarter '{end}'", err=True)
            raise typer.Exit(code=1) from None

        from dataclasses import replace as dc_replace

        n = e_idx - s_idx + 1
        scenario = dc_replace(
            scenario,
            start_quarter=start,
            n_periods=n,
            initial_average_price=scenario.actual_hpi[s_idx],
            bank_rate_path=scenario.bank_rate_path[s_idx : e_idx + 1],
            mortgage_rate_path=scenario.mortgage_rate_path[s_idx : e_idx + 1],
            income_growth_path=scenario.income_growth_path[s_idx : e_idx + 1],
            regulatory_events=[
                dc_replace(e, period=e.period - s_idx)
                for e in scenario.regulatory_events
                if s_idx <= e.period <= e_idx
            ],
            actual_hpi=scenario.actual_hpi[s_idx : e_idx + 1],
            actual_transactions=scenario.actual_transactions[s_idx : e_idx + 1],
        )

    typer.echo(
        f"Scenario: {scenario.n_periods} periods, "
        f"{len(scenario.regulatory_events)} regulatory events"
    )

    typer.echo("Running historical simulation...")
    hsim = HistoricalSimulation(scenario)
    result = hsim.run()

    typer.echo(f"Simulation complete: {len(result.records)} periods.")
    typer.echo(result.summary())

    # ── Write results ────────────────────────────────────────────────
    output.mkdir(parents=True, exist_ok=True)

    import dataclasses

    records_data = [dataclasses.asdict(r) for r in result.records]

    # Add quarter labels and actual data
    for i, rec in enumerate(records_data):
        if i < len(result.quarter_labels):
            rec["quarter"] = result.quarter_labels[i]
        if i < len(result.actual_hpi):
            rec["actual_house_price"] = result.actual_hpi[i]
        if i < len(result.actual_transactions):
            rec["actual_transactions"] = result.actual_transactions[i]

    if output_format == "json":
        _write_json(output / "historical_results.json", records_data)
        typer.echo(f"  Results -> {output / 'historical_results.json'}")
    elif output_format == "parquet":
        try:
            import polars as pl

            df = pl.DataFrame(records_data)
            df.write_parquet(output / "historical_results.parquet")
            typer.echo(f"  Results -> {output / 'historical_results.parquet'}")
        except ImportError:
            typer.echo(
                "polars required for parquet. Falling back to CSV.",
                err=True,
            )
            output_format = "csv"

    if output_format == "csv":
        import csv

        csv_path = output / "historical_results.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            if records_data:
                writer = csv.DictWriter(fh, fieldnames=records_data[0].keys())
                writer.writeheader()
                writer.writerows(records_data)
        typer.echo(f"  Results -> {csv_path}")

    # ── Evaluation ───────────────────────────────────────────────────
    if evaluate:
        from companies_house_abm.abm.evaluation import evaluate_historical

        typer.echo("\nEvaluating against actual UK housing data...")
        report = evaluate_historical(result, warm_up=4)
        typer.echo(report.summary())
        _write_json(output / "historical_evaluation.json", report.as_dict())
        typer.echo(f"  Report -> {output / 'historical_evaluation.json'}")

    typer.echo("Done.")


if __name__ == "__main__":
    app()
