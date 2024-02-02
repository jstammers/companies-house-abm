import polars as pl
from pathlib import Path

data_dir = Path().parent / "data" / "03_primary" / "combined_records"
schema = pl.scan_parquet(data_dir / "*.parquet").schema

df = pl.scan_parquet(data_dir / "*.parquet")
companies_per_date = df.group_by(["filing_date"]).agg(
    n_company=pl.n_unique("company")
).collect(streaming=True)
# set startdate, enddate and filing_date to datetime

# df = df.with_columns(
#     pl.col("startdate").cast(pl.Date),
#     pl.col("enddate").cast(pl.Date),
#     pl.col("filing_date").cast(pl.Date),
# )

# insert into duckdb
from duckdb import connect
con_string = "duckdb:///earningsai.db"
# read LazyFrame into duckdb
for p in data_dir.glob("*.parquet"):
    df = pl.scan_parquet(p)
    fd = df.schema['filing_date']
    if fd != pl.Utf8:
        print(p)
        df = pl.read_parquet(p)
        df = df.with_columns(pl.col('filing_date').cast(pl.Utf8))
        df.write_parquet(p)