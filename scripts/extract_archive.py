import multiprocessing
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from earningsai.pipelines.process import create_pipeline
import logging

from kedro.runner import SequentialRunner

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def extract_zip(extract_path, zip_path):
    """Extracts a zip file to a given path."""
    import zipfile
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)


def run_kedro(extract_path, output_path, session):
    """Runs kedro project."""
    context = session.load_context()
    catalog = context.catalog.shallow_copy()
    catalog.datasets.bulk_data._path = str(extract_path)
    catalog.datasets.combined_records._filepath = output_path
    pipeline = create_pipeline()
    runner = SequentialRunner()
    runner.run(pipeline, catalog)


def cleanup(extract_path):
    """Removes the extracted zip file."""
    import shutil
    shutil.rmtree(extract_path, ignore_errors=True)


def process_zip(zipfile, PROJECT_PATH, EXTRACT_DIR, OUTPUT_DIR):
    session = KedroSession.create(PROJECT_PATH.as_posix())
    LOGGER.info(f"Extracting {zipfile}")
    extract_path = EXTRACT_DIR / zipfile.stem
    output_path = OUTPUT_DIR / f"combined_records_{zipfile.stem}.parquet"
    if output_path.exists():
        LOGGER.info(f"Skipping {zipfile.stem} as it already exists")
        return
    if not extract_path.exists():
        LOGGER.info(f"Extracting {zipfile.stem} to {extract_path}")
        extract_zip(extract_path, zipfile)
    else:
        LOGGER.info(
            f"Skipping extraction for {zipfile.stem} as it has already been extracted")
    LOGGER.info(f"Running kedro project")
    run_kedro(extract_path, output_path, session)
    LOGGER.info(f"Cleaning up")
    cleanup(extract_path)


def main():
    """Extracts the zip file, runs the kedro project, and cleans up."""
    PROJECT_PATH = Path(__file__).parent.parent
    INPUT_PATH = PROJECT_PATH / "data" / "01_raw"
    EXTRACT_DIR = PROJECT_PATH / "data" / "02_intermediate"
    OUTPUT_DIR = PROJECT_PATH / "data" / "03_primary" / "combined_records"
    bootstrap_project(project_path=PROJECT_PATH.as_posix())
    for zipfile in INPUT_PATH.glob("*.zip"):
        process_zip(zipfile, PROJECT_PATH, EXTRACT_DIR, OUTPUT_DIR)
    # with multiprocessing.Pool(num_workers) as pool:
    #     pool.starmap(process_zip,
    #                  [(zipfile, PROJECT_PATH, EXTRACT_DIR, OUTPUT_DIR) for zipfile in
    #                   INPUT_PATH.glob("*.zip")])


if __name__ == "__main__":
    main()
