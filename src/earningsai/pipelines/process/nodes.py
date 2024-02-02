"""
This is a boilerplate pipeline 'process'
generated using Kedro 0.18.13
"""
import pandas as pd
from dateutil.parser import parse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from kedro.io import DataSetError
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map, process_map
LOGGER = logging.getLogger(__name__)

def process_document(partition_id, partition_load_func):
    try:
        data = partition_load_func()
    except DataSetError as e:
        LOGGER.error(f"Failed to load {partition_id}")
        LOGGER.error(e)
        return None
    data["company"] = partition_id.split("_")[2]
    date_section = partition_id.split("_")[3]
    if "." in date_section:
        date_section = date_section.split(".")[0]
    data["filing_date"] = parse(date_section, yearfirst=True)
    return data

def load_documents(documents):
    num_items = len(documents)
    docs = []
    docs = process_map(process_document, documents.keys(),documents.values(), max_workers=8, desc="Loading documents", total=num_items, chunksize=1000)
    # docs = [process_document(pid, pload) for pid, pload in tqdm(documents.items(), total=num_items)]
    return docs


def combine_records(documents):
    """Combine all records into a single DataFrame"""
    docs = load_documents(documents)
    # for partition_id, partition_load_func in documents.items():
    #     try:
    #         data = partition_load_func()
    #     except DataSetError as e:
    #         LOGGER.error(f"Failed to load {partition_id}")
    #         LOGGER.error(e)
    #         continue
    #     data["company"] = partition_id.split("_")[2]
    #     date_section = partition_id.split("_")[3]
    #     if "." in date_section:
    #         date_section = date_section.split(".")[0]
    #     data["filing_date"] = parse(date_section, yearfirst=True)
    #     docs.append(data)
    return pd.concat(docs, ignore_index=True)
