import shutil
from typing import Any

import pandas as pd
from kedro.io import AbstractDataSet
from kedro.io.core import _DI, _DO
from dateutil.parser import parse
import json
import logging
from pathlib import Path
LOGGER = logging.getLogger(__name__)
class IXBRLDataSet(AbstractDataSet):

    def __init__(self, filepath: str, fields=None) -> None:
        self._filepath = filepath
        components = filepath.split("/")[-1]
        # self._company = components.split("_")[2]
        #parse YYYYMMDD into datetime
        # self._filing_date = parse(components.split("_")[3].replace(".html",""), yearfirst=True)
        if fields is None:
            fields = ["schema", "name", "value", "unit", "instant", "startdate", "enddate"]
        self._fields = fields
    def _load(self) -> _DO:
        from ixbrlparse import IXBRL
        try:
            with open(self._filepath) as f:
                parser = IXBRL(f=f, raise_on_error=False)
                data = parser.to_table()
                content = [{k: d[k] for k in self._fields} for d in data]
            return pd.DataFrame.from_records(content)
        except Exception as e:
            LOGGER.error(f"Error parsing {self._filepath}")
            LOGGER.error(e)
            failed_path = self._filepath.replace("02_intermediate", "03_primary")
            if not Path(failed_path).parent.exists():
                Path(failed_path).parent.mkdir(parents=True)
            shutil.copy(self._filepath, failed_path)
            LOGGER.error(f"Moved {self._filepath} to {failed_path}")
            raise e
    def _save(self, data: _DI) -> None:
        raise NotImplementedError("Saving not implemented")

    def _describe(self) -> dict[str, Any]:
        return dict(filepath=self._filepath,
                    fields=self._fields)