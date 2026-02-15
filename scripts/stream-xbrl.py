import polars as pl
from stream_read_xbrl import stream_read_xbrl_sync

companies_house_schema = {
    # -------------------
    # Run-level fields
    # -------------------
    "run_code": pl.Utf8,
    # -------------------
    # Company-at-date fields
    # -------------------
    "company_id": pl.Utf8,
    "date": pl.Date,
    "file_type": pl.Utf8,
    "taxonomy": pl.Utf8,
    "balance_sheet_date": pl.Date,
    "companies_house_registered_number": pl.Utf8,
    "entity_current_legal_name": pl.Utf8,
    "company_dormant": pl.Boolean,
    "average_number_employees_during_period": pl.Decimal(20, 2),
    # -------------------
    # Period-level fields
    # -------------------
    "period_start": pl.Date,
    "period_end": pl.Date,
    # Balance sheet
    "tangible_fixed_assets": pl.Decimal(20, 2),
    "debtors": pl.Decimal(20, 2),
    "cash_bank_in_hand": pl.Decimal(20, 2),
    "current_assets": pl.Decimal(20, 2),
    "creditors_due_within_one_year": pl.Decimal(20, 2),
    "creditors_due_after_one_year": pl.Decimal(20, 2),
    "net_current_assets_liabilities": pl.Decimal(20, 2),
    "total_assets_less_current_liabilities": pl.Decimal(20, 2),
    "net_assets_liabilities_including_pension_asset_liability": pl.Decimal(20, 2),
    "called_up_share_capital": pl.Decimal(20, 2),
    "profit_loss_account_reserve": pl.Decimal(20, 2),
    "shareholder_funds": pl.Decimal(20, 2),
    # P&L
    "turnover_gross_operating_revenue": pl.Decimal(20, 2),
    "other_operating_income": pl.Decimal(20, 2),
    "cost_sales": pl.Decimal(20, 2),
    "gross_profit_loss": pl.Decimal(20, 2),
    "administrative_expenses": pl.Decimal(20, 2),
    "raw_materials_consumables": pl.Decimal(20, 2),
    "staff_costs": pl.Decimal(20, 2),
    "depreciation_other_amounts_written_off_tangible_intangible_fixed_assets": (
        pl.Decimal(20, 2)
    ),
    "other_operating_charges_format2": pl.Decimal(20, 2),
    "operating_profit_loss": pl.Decimal(20, 2),
    "profit_loss_on_ordinary_activities_before_tax": pl.Decimal(20, 2),
    "tax_on_profit_or_loss_on_ordinary_activities": pl.Decimal(20, 2),
    "profit_loss_for_period": pl.Decimal(20, 2),
    "error": pl.Utf8,
    "zip_url": pl.Utf8,
}

if __name__ == "__main__":
    with stream_read_xbrl_sync() as (
        columns,
        date_range_and_rows,
    ):
        for (_start_date, _end_date), rows in date_range_and_rows:
            # collect into parquet file
            df = pl.DataFrame(
                rows,
                orient="row",
                infer_schema_length=10000,
                schema=companies_house_schema,
            )
            df.write_parquet("companies_house_accounts.parquet")
