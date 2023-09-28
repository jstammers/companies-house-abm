"""A script to download archive files from Companies House."""
url = "http://download.companieshouse.gov.uk/historicmonthlyaccountsdata.html"
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import logging
from urllib.request import urlretrieve

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

LOGGER = logging.getLogger(__name__)


ROOT_PATH = Path(__file__).parent.parent / "data" / "01_raw"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")
links = soup.find_all("a")
download_links = []
for link in links:
    if "zip" in link.text:
        download_links.append(link["href"])

for link in download_links:
    LOGGER.info(f"Downloading {link}")
    filename = link.split("/")[-1]
    src = "http://download.companieshouse.gov.uk/" + link
    dst = ROOT_PATH / filename
    urlretrieve(src, dst)
    LOGGER.info(f"Saved {src} to {dst}")