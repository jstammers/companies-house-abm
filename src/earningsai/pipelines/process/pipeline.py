"""
This is a boilerplate pipeline 'process'
generated using Kedro 0.18.13
"""

from kedro.pipeline import Pipeline, pipeline, node
from .nodes import combine_records

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([node(combine_records,
                          inputs=["bulk_data"],
                          outputs="combined_records")])
