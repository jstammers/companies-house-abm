from typing import Any

import pandas as pd
from kedro.io import AbstractDataSet
from kedro.io.core import _DI, _DO
from dateutil.parser import parse
import json
class IXBRLDataSet(AbstractDataSet):

    def __init__(self, filepath: str, fields=None) -> None:
        self._filepath = filepath
        components = filepath.split("/")[-1]
        self._company = components.split("_")[2]
        #parse YYYYMMDD into datetime
        self._filing_date = parse(components.split("_")[3].replace(".html",""), yearfirst=True)
        if fields is None:
            fields = ["schema", "name", "value", "unit", "instant", "startdate", "enddate"]
        self._fields = fields
    def _load(self) -> _DO:
        from ixbrlparse import IXBRL
        with open(self._filepath) as f:
            parser = IXBRL(f=f, raise_on_error=False)
            data = parser.to_table()
            content = [{k: d[k] for k in self._fields} for d in data]
        data = pd.DataFrame.from_records(content)

        return data

    def _save(self, data: _DI) -> None:
        raise NotImplementedError("Saving not implemented")

    def _describe(self) -> dict[str, Any]:
        return dict(filepath=self._filepath,
                    fields=self._fields,
                    company=self._company,
                    filing_date=self._filing_date)