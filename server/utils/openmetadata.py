import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("OPENMETADATA_URL", "http://localhost:8585")
TOKEN = os.getenv("OPENMETADATA_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

async def search_tables(query: str, limit: int = 10):
    """Search tables by name or description using plain text."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/api/v1/search/query",
            params={
                "q": query,
                "index": "table_search_index",
                "from": 0,
                "size": limit
            },
            headers=HEADERS,
            timeout=30.0
        )
        resp.raise_for_status()
        return resp.json()

async def get_table_details(fqn: str):
    """Get full details of a table by its fully qualified name."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/api/v1/tables/name/{fqn}",
            params={
                "fields": "columns,tableConstraints,owner,tags,followers"
            },
            headers=HEADERS,
            timeout=30.0
        )
        resp.raise_for_status()
        return resp.json()

async def get_lineage(fqn: str):
    """Get upstream and downstream lineage for a table."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/api/v1/lineage/table/name/{fqn}",
            params={
                "upstreamDepth": 2,
                "downstreamDepth": 2
            },
            headers=HEADERS,
            timeout=30.0
        )
        resp.raise_for_status()
        return resp.json()

async def get_tables_missing_owners(limit: int = 20):
    """Find tables that have no assigned owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/api/v1/tables",
            params={
                "limit": limit,
                "include": "non-deleted"
            },
            headers=HEADERS,
            timeout=30.0
        )
        resp.raise_for_status()
        data = resp.json()
        # Filter only tables with no owner
        return [t for t in data.get("data", []) if not t.get("owners")]

async def get_tagged_tables(tag: str, limit: int = 10):
    """Find tables that have a specific tag — e.g. PII or PersonalData."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/api/v1/search/query",
            params={
                "q": f"tags.tagFQN:{tag}",
                "index": "table_search_index",
                "from": 0,
                "size": limit
            },
            headers=HEADERS,
            timeout=30.0
        )
        resp.raise_for_status()
        return resp.json()