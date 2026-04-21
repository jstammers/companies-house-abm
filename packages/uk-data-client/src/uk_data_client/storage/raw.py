"""Raw JSON blob persistence for provenance and replay."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RawStore:
    """Persist raw source payloads as JSON files."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, *, source: str, key: str, payload: Any) -> Path:
        """Write a payload to the raw store."""
        stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
        directory = self.root / 'raw' / source / key
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f'{stamp}.json'
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return path

    def read(self, path: Path) -> Any:
        """Read a previously stored raw payload."""
        return json.loads(path.read_text())
