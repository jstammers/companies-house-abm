"""parse_xbrl_json.py - Parse XBRL documents into JSON using arelle"""
import json
import os
from pathlib import Path

import requests

from arelle import ModelManager, Cntlr, ModelXbrl, XbrlConst, ModelDocument
from arelle.plugin.xbrlDB.XbrlSemanticJsonDB import insertIntoDB

controller = Cntlr.Cntlr()
modelManager = controller.modelManager
def get_json(xbrl_path:Path):
    """Parse XBRL document into JSON"""
    json_path = xbrl_path.replace(".xbrl", ".json")
    base_url = "http://localhost:8080/rest/xbrl/view"
    # doc = requests.get(base_url, params={"media": "json", "file": Path(xbrl_path).absolute(), "view":"factTable"}).json()
    modelXbrl = modelManager.load(xbrl_path)
    insertIntoDB(modelXbrl,host='jsonFile' )

d = get_json("notebooks/test.xml")