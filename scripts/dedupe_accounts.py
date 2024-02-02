import duckdb

con = duckdb.connect(database="../earningsai.db", read_only=False)

unique_filing_dates = con.execute("SELECT DISTINCT filing_date::date AS filing_date FROM accounts").fetchdf()

for filing_date in unique_filing_dates['filing_date']:
    print(f"Processing {filing_date}")
    con.execute(f"""
    UPDATE accounts
    SET current_year = enddate = filing_date::date or instant = filing_date::date
    WHERE filing_date::date = '{filing_date}';""")

min_dates = con.execute("SELECT company, MIN(filing_date::date) AS min_date FROM accounts GROUP BY company").fetchdf()

