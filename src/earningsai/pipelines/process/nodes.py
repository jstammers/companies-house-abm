"""
This is a boilerplate pipeline 'process'
generated using Kedro 0.18.13
"""
import pandas as pd
from dateutil.parser import parse
import logging

from kedro.io import DataSetError

LOGGER = logging.getLogger(__name__)
def combine_records(documents):
    """Combine all records into a single DataFrame"""
    docs = []

    for partition_id, partition_load_func in documents.items():
        try:
            data = partition_load_func()
        except DataSetError as e:
            LOGGER.error(f"Failed to load {partition_id}")
            LOGGER.error(e)
            continue
        data["company"] = partition_id.split("_")[2]
        date_section = partition_id.split("_")[3]
        if "." in date_section:
            date_section = date_section.split(".")[0]
        data["filing_date"] = parse(date_section, yearfirst=True)
        docs.append(data)
    return pd.concat(docs, ignore_index=True)