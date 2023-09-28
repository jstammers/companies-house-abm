from earningsai.ixbrl_dataset import IXBRLDataSet

from datetime import datetime
#
# d = datetime.strptime("0001-01-01", "%Y-%m-%d").astimezone()
#
def test_ixbrl_dataset():
    file_path = "data/Prod223_3517_13756628_20221130.html"
    ds = IXBRLDataSet(file_path)
    data = ds.load()