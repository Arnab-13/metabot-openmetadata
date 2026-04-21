import asyncio
from utils.openmetadata import search_tables, get_tables_missing_owners

async def main():
    print("Testing search...")
    results = await search_tables("customer")
    hits = results.get("hits", {}).get("hits", [])
    print(f"Found {len(hits)} tables matching 'customer'")
    for h in hits[:3]:
        print(f"  - {h['_source'].get('fullyQualifiedName', 'unknown')}")

    print("\nTesting missing owners...")
    tables = await get_tables_missing_owners()
    print(f"Found {len(tables)} tables without owners")
    for t in tables[:3]:
        print(f"  - {t.get('fullyQualifiedName', 'unknown')}")

asyncio.run(main())