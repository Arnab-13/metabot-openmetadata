import asyncio
from utils.openmetadata import get_table_details
from tools.pii import detect_pii_columns, summarize_pii_findings

async def main():
    # Test on a table that likely has PII columns
    fqn = "sample_data.ecommerce_db.shopify.dim_customer"
    print(f"Scanning: {fqn}\n")

    details = await get_table_details(fqn)
    columns = details.get("columns", [])

    print(f"Total columns found: {len(columns)}")
    print("Column names:", [c["name"] for c in columns])
    print()

    flagged = detect_pii_columns(columns)
    summary = summarize_pii_findings(fqn, flagged)
    print(summary)

asyncio.run(main())