"""Companies House free company data fetcher.

Downloads and parses the monthly bulk company dataset published by Companies
House to provide SIC-code-to-company-number mappings required for sector
assignment in the ABM profiling pipeline.

Source
------
Free Company Data Product — Companies House:
https://download.companieshouse.gov.uk/en_output.html

The snapshot is updated within 5 working days of each month end and contains
basic information for all live companies registered in the UK, including up to
four SIC codes per company.

The downloaded file follows the naming pattern::

    BasicCompanyDataAsOneFile-YYYY-MM-01.zip

The output of :func:`fetch_sic_codes` is a Polars DataFrame with columns
``companies_house_registered_number`` and ``sic_code`` that can be passed
directly to
:func:`~companies_house_abm.data_sources.firm_distributions.assign_sectors`.

All data is published under the Companies House licence.
See https://resources.companieshouse.gov.uk/legal/termsAndConditions.shtml.
"""

from __future__ import annotations

import io
import logging
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL pattern
# ---------------------------------------------------------------------------

_BULK_URL_TEMPLATE = (
    "http://download.companieshouse.gov.uk/"
    "BasicCompanyDataAsOneFile-{year:04d}-{month:02d}-01.zip"
)

# ---------------------------------------------------------------------------
# CSV column names in the raw Companies House bulk data
# ---------------------------------------------------------------------------

_COL_COMPANY_NUMBER = "CompanyNumber"
_COL_SIC_1 = "SICCode.SicText_1"

# Timeout for the bulk download — the file is ~400 MB so needs more time than
# the default 30 s used for small API responses.
_DOWNLOAD_TIMEOUT = 600  # 10 minutes


def _bulk_url(year: int, month: int) -> str:
    """Build the download URL for the given month."""
    return _BULK_URL_TEMPLATE.format(year=year, month=month)


def _candidate_urls() -> list[str]:
    """Return download URLs to try, most recent first.

    Companies House typically publishes within 5 working days of month end, so
    the current-month file may not yet exist early in the month. We fall back
    to the previous month automatically.
    """
    today = date.today()
    urls = [_bulk_url(today.year, today.month)]
    # Previous month fallback
    if today.month == 1:
        urls.append(_bulk_url(today.year - 1, 12))
    else:
        urls.append(_bulk_url(today.year, today.month - 1))
    return urls


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _stream_to_tempfile(url: str) -> str:
    """Stream *url* to a temporary file and return its path.

    The caller is responsible for deleting the file when done.

    Args:
        url: URL to download.

    Returns:
        Path to the temporary file containing the downloaded bytes.

    Raises:
        urllib.error.URLError: On network errors.
    """
    from companies_house_abm.data_sources._http import _USER_AGENT

    logger.info("Downloading %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    fd, tmp_path_str = tempfile.mkstemp(suffix=".zip")
    tmp_path = Path(tmp_path_str)
    try:
        import os

        with (
            urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp,
            os.fdopen(fd, "wb") as tmp_file,
        ):
            total = 0
            while True:
                chunk = resp.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                tmp_file.write(chunk)
                total += len(chunk)
        logger.info("Downloaded %.1f MB to %s", total / 1024 / 1024, tmp_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return str(tmp_path)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_bulk_zip(zip_path: str) -> pl.DataFrame:
    """Parse the Companies House bulk ZIP file into a SIC lookup DataFrame.

    Only the ``CompanyNumber`` and primary SIC code columns are extracted
    to keep peak memory usage low.

    Args:
        zip_path: Path to the downloaded ZIP file on disk.

    Returns:
        Raw DataFrame before normalisation.
    """
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            msg = f"No CSV file found inside {zip_path}"
            raise ValueError(msg)
        csv_name = csv_names[0]
        logger.info("Parsing %s from ZIP", csv_name)
        with zf.open(csv_name) as csv_file:
            raw = csv_file.read()

    return pl.read_csv(
        io.BytesIO(raw),
        columns=[_COL_COMPANY_NUMBER, _COL_SIC_1],
        schema_overrides={_COL_COMPANY_NUMBER: pl.Utf8, _COL_SIC_1: pl.Utf8},
        ignore_errors=True,
    )


def _normalise(raw: pl.DataFrame) -> pl.DataFrame:
    """Normalise raw bulk data into the SIC lookup format.

    Transformations applied:

    - ``CompanyNumber`` → ``companies_house_registered_number``:
      strip whitespace and zero-pad to 8 characters.
    - ``SICCode.SicText_1`` → ``sic_code``:
      extract the leading 5-digit SIC code from strings like
      ``"62020 - Computer programming, consultancy and related activities"``.
    - Drop rows with missing or non-numeric SIC codes.
    - Deduplicate to one row per company (keep first).

    Args:
        raw: DataFrame as returned by :func:`_parse_bulk_zip`.

    Returns:
        Clean DataFrame with columns ``companies_house_registered_number``
        and ``sic_code``.
    """
    return (
        raw.lazy()
        .filter(
            pl.col(_COL_COMPANY_NUMBER).is_not_null() & pl.col(_COL_SIC_1).is_not_null()
        )
        .with_columns(
            pl.col(_COL_COMPANY_NUMBER)
            .str.strip_chars()
            .str.zfill(8)
            .alias("companies_house_registered_number"),
            # SIC entries look like "62020 - Description"; keep first 5 chars.
            pl.col(_COL_SIC_1).str.strip_chars().str.slice(0, 5).alias("sic_code"),
        )
        .select("companies_house_registered_number", "sic_code")
        # Retain only rows where sic_code is exactly 5 ASCII digits.
        .filter(pl.col("sic_code").str.len_chars() == 5)
        .filter(pl.col("sic_code").str.contains(r"^\d{5}$"))
        .unique(subset=["companies_house_registered_number"], keep="first")
        .collect()
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_sic_codes(
    *,
    output_path: Path | None = None,
) -> pl.DataFrame:
    """Download Companies House bulk data and extract primary SIC codes.

    Tries the current month's snapshot first, then falls back to the
    previous month if the current file is not yet published.

    The resulting DataFrame has one row per company and can be passed
    directly to
    :func:`~companies_house_abm.data_sources.firm_distributions.assign_sectors`
    via its *sic_path* argument (after saving to Parquet with
    *output_path*).

    Args:
        output_path: If provided, save the result as Parquet at this path.
            The parent directory is created if it does not exist.

    Returns:
        Polars DataFrame with columns:

        - ``companies_house_registered_number`` — zero-padded 8-char
          company registration number.
        - ``sic_code`` — 5-digit SIC 2007 code string (e.g. ``"62020"``).

    Raises:
        RuntimeError: If the download fails for all candidate URLs.

    Example::

        >>> from pathlib import Path
        >>> from companies_house_abm.data_sources.companies_house import fetch_sic_codes
        >>> df = fetch_sic_codes(output_path=Path("data/sic_codes.parquet"))
        >>> "sic_code" in df.columns
        True
    """
    last_exc: Exception | None = None
    for url in _candidate_urls():
        tmp_path: str | None = None
        try:
            tmp_path = _stream_to_tempfile(url)
            raw = _parse_bulk_zip(tmp_path)
            df = _normalise(raw)
            logger.info("Extracted SIC codes for %d companies", len(df))
            if output_path is not None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                df.write_parquet(output_path)
                logger.info("SIC code lookup saved to %s", output_path)
            return df
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("Could not fetch %s: %s", url, exc)
            last_exc = exc
        except Exception as exc:
            logger.warning("Failed to parse bulk data from %s: %s", url, exc)
            last_exc = exc
        finally:
            if tmp_path is not None:
                Path(tmp_path).unlink(missing_ok=True)

    raise RuntimeError(
        "Could not download Companies House bulk company data from any URL"
    ) from last_exc
