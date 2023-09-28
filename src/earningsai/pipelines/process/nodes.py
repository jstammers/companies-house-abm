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
        except DataSetError:
            LOGGER.error(f"Failed to load {partition_id}")
            continue
        data["company"] = partition_id.split("_")[2]
        data["filing_date"] = parse(partition_id.split("_")[3], yearfirst=True)
        docs.append(data)
    return pd.concat(docs, ignore_index=True)