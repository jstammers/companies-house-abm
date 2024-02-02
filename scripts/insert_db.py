import duckdb
from pathlib import Path
# Path to your DuckDB database file
db_path = 'earningsai.db'

# Connect to DuckDB (this will create the database file if it doesn't exist)
con = duckdb.connect(database=db_path, read_only=False)

# Path to your Parquet file
parquet_file = 'data/03_primary/combined_records/combined_records_Accounts_Monthly_Data-April2010.parquet'

# Create a table and insert data from the Parquet file
# Replace 'your_table' with your desired table name
con.execute(f"CREATE TABLE IF NOT EXISTS accounts AS SELECT * FROM read_parquet('{parquet_file}')")

# Commit changes to make them persistent
con.commit()
con.execute("TRUNCATE TABLE accounts")
con.commit()
parquet_files = Path('data/03_primary/combined_records').glob('*.parquet')
for p in parquet_files:
    print(p)
    con.execute(f"INSERT INTO accounts SELECT * FROM read_parquet('{p}')")
    con.commit()
# Close the connection
con.close()

con = duckdb.connect(database=db_path, read_only=True)
con.execute("CREATE TABLE IF NOT EXISTS companies AS SELECT * FROM read_csv('data/03_primary/BasicCompanyDataAsOneFile-2023-11-01.csv', AUTO_DETECT=TRUE)")