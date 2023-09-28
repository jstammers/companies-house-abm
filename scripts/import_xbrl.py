import subprocess
import sqlalchemy as sa
xbrl_file = "../data/01_raw/small/Prod223_3517_00035838_20221231.html"
db = "/home/jimmy/Dropbox/Code/Python/EarningsAI/data/02_intermediate/reports.db"
conn = f"{db},5432,user,password,{db},sqliteSemantic,sqliteSemantic"

cmd = [
    "arelleCmdLine",
    "--plugin", "xbrlDB",
    "--file", xbrl_file,
    "--store-to-XBRL-DB", conn,
]

from arelle import ModelManager, Cntlr, ViewFileFactTable
from tempfile import NamedTemporaryFile
import pandas as pd
def fill_hierarchy(df, index_columns=None):
    # Iterate over all the columns except the last one
    col_fill = df[index_columns].ffill()
    row_fill = df[index_columns].ffill(axis=1)
    for i in range(1, len(index_columns)):
        prev_row = row_fill.iloc[:, i - 1].notna()
        col_fill.iloc[prev_row.values, i] = None
    # set column fill limits based on the row fills
    df[index_columns] = col_fill
    return df

def infer_taxonomy_details(model_xbrl, fact):
    # Retrieve the context object from the fact's contextID
    context = fact.context

    # Determine the time dimension
    if context.isInstantPeriod:
        period = context.instantDatetime
    elif context.isStartEndPeriod:
        period = (context.startDatetime, context.endDatetime)

    # Get entity information
    entity = context.entityIdentifier

    # Retrieve scenario or segment data (if any)
    scenario = context.qnameDims

    return {
        "period": period,
        "entity": entity,
        "scenario": scenario
    }
def parse_xbrl(xbrl_path):
    # Initialize the Arelle controller and model manager
    cntlr = Cntlr.Cntlr()
    model_manager = ModelManager.initialize(cntlr)

    model_xbrl = model_manager.load(xbrl_path)
    # Use a StringIO object as an in-memory file to hold the CSV output
    tmp = NamedTemporaryFile(suffix=".csv")
    # Create the fact table CSV view for the loaded XBRL instance
    ViewFileFactTable.viewFacts(model_xbrl, tmp.name)
    df = pd.read_csv(tmp.name)
    index_cols = [c for c in df.columns if c.startswith("Unnamed") or c.startswith("Concept")]
    index_renamer = {c: f"Hierarchy_{i}" for i, c in enumerate(index_cols)}
    df = fill_hierarchy(df, index_cols)
    df2 = df.set_index(index_cols).dropna(axis=0, how='all').dropna(axis=1, how='all')
    dfm = df2.melt(ignore_index=False).dropna().sort_index().reset_index()
    return dfm.rename(columns=index_renamer)
    facts = []
    for fact in model_xbrl.facts:
        if not fact.isNil:
            entity_name, entity_id = fact.context.entityIdentifier
            facts.append((entity_name, entity_id, fact.qname.namespaceURI, fact.contextID, fact.qname.localName, fact.context.startDatetime, fact.context.endDatetime, fact.context.instantDateTime, fact.value))
    return facts

facts = parse_xbrl(xbrl_file)