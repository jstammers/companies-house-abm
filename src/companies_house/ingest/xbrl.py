"""XBRL ingestion pipeline for Companies House bulk data.

Extracted from ``companies_house_abm.ingest`` — handles both old-style XML
(UK GAAP, pre-2014) and new inline iXBRL HTML archives transparently via
``stream-read-xbrl``.
"""

from __future__ import annotations

import io
import logging
import urllib.error
import urllib.request
import zipfile
from typing import TYPE_CHECKING

import polars as pl
from stream_read_xbrl import stream_read_xbrl_sync, stream_read_xbrl_zip

from companies_house.schema import COMPANIES_HOUSE_SCHEMA, DEDUP_COLUMNS

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from datetime import date
    from pathlib import Path

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "companies-house/ingest (+https://github.com/jstammers/companies-house-abm)"
)
# Byte ranges used when fetching just the ZIP central directory via HTTP Range.
_INITIAL_RANGE_BYTES = 33_554_432  # 32 MB
_RETRY_RANGE_BYTES = 67_108_864  # 64 MB


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def infer_start_date(parquet_path: Path) -> date | None:
    """Scan parquet for max ``date`` column value.

    Returns None if the file is missing or empty.
    """
    if not parquet_path.exists():
        return None
    try:
        result = pl.scan_parquet(parquet_path).select(pl.col("date").max()).collect()
        if result.is_empty() or result[0, 0] is None:
            return None
        return result[0, 0]
    except Exception:
        logger.warning("Could not read parquet at %s", parquet_path, exc_info=True)
        return None


def deduplicate(df: pl.DataFrame) -> pl.DataFrame:
    """Remove duplicate rows, keeping the last occurrence."""
    return df.unique(subset=DEDUP_COLUMNS, keep="last", maintain_order=True)


# ---------------------------------------------------------------------------
# ZIP / stream ingestion
# ---------------------------------------------------------------------------


def _zip_bytes_iter(zip_path: Path) -> Generator[bytes]:
    """Yield 64KB chunks from a local ZIP file."""
    chunk_size = 64 * 1024
    with zip_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def ingest_from_zips(zip_paths: Sequence[Path]) -> pl.DataFrame:
    """Process local ZIP files via ``stream_read_xbrl_zip``.

    Corrupt or unreadable ZIPs are logged and skipped.
    """
    frames: list[pl.DataFrame] = []
    for zip_path in zip_paths:
        try:
            with stream_read_xbrl_zip(
                _zip_bytes_iter(zip_path), zip_url=str(zip_path)
            ) as (_columns, rows):
                df = pl.DataFrame(
                    list(rows),
                    orient="row",
                    schema=COMPANIES_HOUSE_SCHEMA,
                )
                frames.append(df)
                logger.info("Ingested %d rows from %s", len(df), zip_path)
        except Exception:
            logger.warning("Skipping corrupt ZIP: %s", zip_path, exc_info=True)
    if not frames:
        return pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
    return pl.concat(frames)


def ingest_from_stream(*, start_date: date | None = None) -> pl.DataFrame:
    """Download and ingest XBRL data from Companies House.

    If *start_date* is provided, only data after that date is ingested.
    """
    import datetime

    if start_date is not None:
        after_date = start_date
    else:
        after_date = datetime.date(datetime.MINYEAR, 1, 1)

    frames: list[pl.DataFrame] = []
    with stream_read_xbrl_sync(
        ingest_data_after_date=after_date,
    ) as (_columns, date_range_and_rows):
        for (batch_start, batch_end), rows in date_range_and_rows:
            df = pl.DataFrame(
                list(rows),
                orient="row",
                schema=COMPANIES_HOUSE_SCHEMA,
            )
            frames.append(df)
            logger.info(
                "Ingested %d rows for %s to %s",
                len(df),
                batch_start,
                batch_end,
            )
    if not frames:
        return pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
    return pl.concat(frames)


def merge_and_write(
    new_data: pl.DataFrame,
    output_path: Path,
    *,
    existing_path: Path | None = None,
) -> pl.DataFrame:
    """Concat with existing parquet, deduplicate, and write."""
    if existing_path is not None and existing_path.exists():
        existing = pl.read_parquet(existing_path)
        combined = pl.concat([existing, new_data])
    else:
        combined = new_data

    result = deduplicate(combined)
    result.write_parquet(output_path)
    logger.info("Wrote %d rows to %s", len(result), output_path)
    return result


# ---------------------------------------------------------------------------
# Archive-directory helpers
# ---------------------------------------------------------------------------


def get_ingested_zip_basenames(parquet_path: Path) -> frozenset[str]:
    """Return the set of ZIP basenames already recorded in *parquet_path*.

    Returns an empty frozenset if the file is missing, empty, or unreadable.
    """
    from pathlib import Path as _Path

    p = _Path(parquet_path)
    if not p.exists():
        return frozenset()
    try:
        urls = (
            pl.scan_parquet(p)
            .select(pl.col("zip_url").drop_nulls())
            .collect()["zip_url"]
            .to_list()
        )
        return frozenset(_Path(u).name for u in urls)
    except Exception:
        logger.warning(
            "Could not read zip_url column from %s",
            parquet_path,
            exc_info=True,
        )
        return frozenset()


def ingest_from_archive_dir(
    archive_dir: Path,
    *,
    parquet_path: Path | None = None,
    progress: bool = True,
) -> pl.DataFrame:
    """Discover and ingest all ZIPs in *archive_dir*, skipping already-ingested.

    Parameters
    ----------
    archive_dir:
        Directory containing ``*.zip`` files from Companies House bulk download.
    parquet_path:
        If provided and the file exists, ZIP basenames already referenced in
        its ``zip_url`` column are skipped (incremental mode).
    progress:
        Emit ``logger.info`` messages about skip counts when ``True``.

    Returns
    -------
    pl.DataFrame
        Combined rows from all newly-processed ZIPs, or an empty
        schema-matching DataFrame if nothing new was found.
    """
    from pathlib import Path as _Path

    all_zips = sorted(_Path(archive_dir).glob("*.zip"))
    total = len(all_zips)

    if parquet_path is not None:
        already = get_ingested_zip_basenames(parquet_path)
        pending = [z for z in all_zips if z.name not in already]
        skipped = total - len(pending)
        if progress and skipped:
            logger.info(
                "Skipping %d / %d ZIPs already in parquet; %d to process.",
                skipped,
                total,
                len(pending),
            )
    else:
        pending = all_zips

    if not pending:
        logger.info("No new ZIPs to process.")
        return pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)

    logger.info("Processing %d ZIP file(s) from %s", len(pending), archive_dir)
    return ingest_from_zips(pending)


# ---------------------------------------------------------------------------
# Remote ZIP inspection
# ---------------------------------------------------------------------------


class _TailBuffer(io.RawIOBase):
    """Seekable file-like presenting the last N bytes of a larger file.

    Lets ``zipfile.ZipFile`` parse the ZIP central directory (at the end of
    the file) without downloading the entire archive.
    """

    def __init__(self, data: bytes, total_size: int) -> None:
        super().__init__()
        self._data = memoryview(data)
        self._total = total_size
        self._tail_start = total_size - len(data)
        self._pos = 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, pos: int, whence: int = 0) -> int:
        if whence == 0:
            new_pos = pos
        elif whence == 1:
            new_pos = self._pos + pos
        elif whence == 2:
            new_pos = self._total + pos
        else:
            raise ValueError(f"Invalid whence value: {whence}")
        self._pos = max(0, new_pos)
        return self._pos

    def read(self, n: int = -1) -> bytes:
        if self._pos >= self._total:
            return b""
        end = self._total if (n is None or n < 0) else min(self._pos + n, self._total)
        if self._pos < self._tail_start:
            # Returning zero bytes here would silently corrupt Zip64 EOCD parsing.
            # Raise instead so fetch_zip_index catches OSError and retries with a
            # larger range rather than misreading the archive structure.
            raise io.UnsupportedOperation(
                f"Read at offset {self._pos} is before the buffered tail "
                f"(tail starts at {self._tail_start}). "
                "Retry with a larger range."
            )
        buf_start = self._pos - self._tail_start
        buf_end = min(end - self._tail_start, len(self._data))
        result = bytes(self._data[buf_start:buf_end])
        self._pos = self._tail_start + buf_end
        return result

    def readinto(self, b: bytearray | memoryview) -> int:  # type: ignore[invalid-method-override]
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n


def _http_range_bytes(url: str, last_n: int, *, timeout: int) -> tuple[bytes, int]:
    """Fetch the last *last_n* bytes of *url* using HTTP Range."""
    req = urllib.request.Request(
        url,
        headers={
            "Range": f"bytes=-{last_n}",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        data = resp.read()
        if status == 206:
            content_range = resp.headers.get("Content-Range", "")
            try:
                total_size = int(content_range.split("/")[-1])
            except (ValueError, IndexError):
                total_size = len(data)
        elif status == 200:
            total_size = len(data)
        else:
            raise ValueError(f"Unexpected HTTP status {status} fetching {url}")
    return data, total_size


def fetch_zip_index(url: str, *, timeout: int = 30) -> list[str]:
    """Return member filenames in a remote ZIP via HTTP Range requests.

    Downloads only the ZIP central directory (at the end of the file).
    """
    for range_bytes in (_INITIAL_RANGE_BYTES, _RETRY_RANGE_BYTES):
        try:
            data, total_size = _http_range_bytes(url, range_bytes, timeout=timeout)
        except urllib.error.URLError:
            raise

        buf = _TailBuffer(data, total_size)
        try:
            with zipfile.ZipFile(io.BufferedReader(buf)) as zf:
                return zf.namelist()
        except (zipfile.BadZipFile, OSError):
            # BadZipFile: central directory not in this tail range.
            # OSError (including io.UnsupportedOperation): _TailBuffer read
            # crossed into pre-buffer region (Zip64 EOCD locator read-back).
            if range_bytes == _RETRY_RANGE_BYTES:
                raise zipfile.BadZipFile(
                    f"Could not parse ZIP central directory from {url} "
                    f"within {_RETRY_RANGE_BYTES} bytes"
                ) from None
            logger.debug(
                "Central directory not within %d bytes of %s; retrying with %d bytes.",
                range_bytes,
                url,
                _RETRY_RANGE_BYTES,
            )

    # Unreachable, but keeps type checkers happy
    # pragma: no cover
    raise zipfile.BadZipFile("Could not locate ZIP central directory")


def check_company_in_zip(zip_path: Path, company_id: str) -> bool:
    """Return True if *company_id* is the third segment of any member filename.

    Companies House ZIPs use filenames like
    ``Prod224_0012_01873499_20230131.html`` where the 8-digit company number
    is the third underscore-separated segment (index 2).  Segment matching
    avoids false positives from company IDs that appear elsewhere in filenames.

    Returns False on any error (corrupt archive, missing file, etc.).
    """
    from pathlib import Path as _Path

    def _id_in_name(name: str, cid: str) -> bool:
        basename = name.rsplit("/", 1)[-1]
        parts = basename.split("_")
        return len(parts) >= 3 and parts[2] == cid

    try:
        with zipfile.ZipFile(_Path(zip_path)) as zf:
            return any(_id_in_name(name, company_id) for name in zf.namelist())
    except Exception:
        logger.warning(
            "Could not inspect ZIP %s for company %s",
            zip_path,
            company_id,
            exc_info=True,
        )
        return False
