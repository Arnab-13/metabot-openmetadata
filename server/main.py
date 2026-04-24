from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
import os
import asyncio
from dotenv import load_dotenv
from tools.pii import detect_pii_columns, summarize_pii_findings
from utils.openmetadata import (
    search_tables,
    get_table_details,
    get_lineage,
    get_tables_missing_owners,
    get_tagged_tables
)

load_dotenv()

app = FastAPI(
    title="MetaBot",
    description="AI-powered natural language agent for OpenMetadata",
    version="1.0.0"
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")


# ── Request/Response models ──────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    tool_used: str
    tables_found: int = 0


# ── Ollama helper ────────────────────────────────────────────────────────────

async def ask_ollama(prompt: str) -> str:
    """Send a prompt to local Ollama and return the response text."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        resp.raise_for_status()
        return resp.json()["response"]


# ── Query router ─────────────────────────────────────────────────────────────

def detect_intent(question: str) -> str:
    """
    Detect what the user is asking about based on keywords.
    Returns one of: lineage, missing_owners, pii, search
    """
    q = question.lower()

    if any(w in q for w in ["lineage", "upstream", "downstream", "flow", "pipeline", "source"]):
        return "lineage"

    if any(w in q for w in ["missing owner", "no owner", "without owner", "unowned"]):
        return "missing_owners"

    if any(w in q for w in ["pii", "personal data", "sensitive", "private", "gdpr", "compliance"]):
        return "pii"

    return "search"


def extract_table_hint(question: str) -> str:
    """
    Extract meaningful search terms from the question.
    Keeps domain words like 'orders', 'customers', 'sales' etc.
    """
    q = question.lower()
    
    # These are the only words to strip — keep domain/business words
    stop_words = {
    "show", "find", "get", "what", "which", "list", "tell",
    "me", "the", "a", "an", "of", "for", "in", "on", "is",
    "are", "does", "do", "have", "has", "any", "all", "about",
    "related", "to", "with", "from", "table", "tables",
    "lineage", "upstream", "downstream", "flow", "pipeline",
    "sensitive", "pii", "personal", "data", "columns", "column",
    "owner", "owners", "missing", "without", "unowned"
}
    
    words = q.split()
    meaningful = [w for w in words if w not in stop_words and len(w) > 2]
    result = " ".join(meaningful) if meaningful else question
    return result


# ── Route handlers ───────────────────────────────────────────────────────────

async def handle_lineage(question: str) -> QueryResponse:
    hint = extract_table_hint(question)
    results = await search_tables(hint, limit=3)
    hits = results.get("hits", {}).get("hits", [])

    if not hits:
        return QueryResponse(
            question=question,
            answer="I couldn't find any tables matching your query. Try using the table name directly.",
            tool_used="lineage",
            tables_found=0
        )

    fqn = hits[0]["_source"].get("fullyQualifiedName", "")
    lineage_data = await get_lineage(fqn)

    # Extract upstream and downstream nodes cleanly
    nodes = lineage_data.get("nodes", [])
    edges = lineage_data.get("edges", [])
    upstream = []
    downstream = []

    for edge in edges:
        if edge.get("toEntity", {}).get("fqn") == fqn:
            upstream.append(edge.get("fromEntity", {}).get("fqn", "unknown"))
        elif edge.get("fromEntity", {}).get("fqn") == fqn:
            downstream.append(edge.get("toEntity", {}).get("fqn", "unknown"))

    context = f"""
Table: {fqn}
Total nodes in lineage graph: {len(nodes)}
Upstream tables (sources): {upstream if upstream else ['No upstream sources found']}
Downstream tables (consumers): {downstream if downstream else ['No downstream consumers found']}
"""

    prompt = f"""You are MetaBot, a helpful data catalog assistant.

The user asked: "{question}"

Here is the lineage information from OpenMetadata:
{context}

Explain this lineage in a clear, friendly way. 
Mention what data flows into this table and what uses this table.
Keep it under 150 words and use bullet points."""

    answer = await ask_ollama(prompt)
    return QueryResponse(
        question=question,
        answer=answer,
        tool_used="lineage",
        tables_found=len(nodes)
    )


async def handle_missing_owners(question: str) -> QueryResponse:
    tables = await get_tables_missing_owners(limit=20)

    if not tables:
        return QueryResponse(
            question=question,
            answer="Great news — all tables currently have assigned owners!",
            tool_used="missing_owners",
            tables_found=0
        )

    table_list = [t.get("fullyQualifiedName", "unknown") for t in tables]
    context = f"Found {len(tables)} tables with no owner:\n" + "\n".join(f"- {t}" for t in table_list)

    prompt = f"""You are MetaBot, a helpful data catalog assistant.

The user asked: "{question}"

{context}

Summarize this clearly. List the tables and explain why having unowned tables 
is a data governance problem. Keep it under 200 words."""

    answer = await ask_ollama(prompt)
    return QueryResponse(
        question=question,
        answer=answer,
        tool_used="missing_owners",
        tables_found=len(tables)
    )


async def handle_pii(question: str) -> QueryResponse:
    hint = extract_table_hint(question)
    results = await search_tables(hint, limit=5)
    hits = results.get("hits", {}).get("hits", [])

    if not hits:
        return QueryResponse(
            question=question,
            answer="I couldn't find any tables matching your query for PII scanning.",
            tool_used="pii",
            tables_found=0
        )

    all_findings = []
    # Scan top 3 matching tables
    for hit in hits[:3]:
        fqn = hit["_source"].get("fullyQualifiedName", "")
        try:
            details = await get_table_details(fqn)
            columns = details.get("columns", [])
            flagged = detect_pii_columns(columns)
            if flagged:
                summary = summarize_pii_findings(fqn, flagged)
                all_findings.append(summary)
        except Exception:
            continue

    if not all_findings:
        context = "No PII columns detected in the scanned tables."
    else:
        context = "\n\n".join(all_findings)

    prompt = f"""You are MetaBot, a helpful data catalog assistant specializing in data governance.

The user asked: "{question}"

Here are the PII scan results:
{context}

Summarize the findings clearly. Explain which tables have sensitive data and 
what should be done about it from a compliance perspective.
Keep it under 200 words and use bullet points."""

    answer = await ask_ollama(prompt)
    return QueryResponse(
        question=question,
        answer=answer,
        tool_used="pii",
        tables_found=len(hits)
    )


async def handle_search(question: str) -> QueryResponse:
    hint = extract_table_hint(question)
    results = await search_tables(hint, limit=5)
    hits = results.get("hits", {}).get("hits", [])

    if not hits:
        return QueryResponse(
            question=question,
            answer=f"I couldn't find any tables related to '{hint}'. Try different keywords.",
            tool_used="search",
            tables_found=0
        )

    table_summaries = []
    for hit in hits[:5]:
        src = hit["_source"]
        table_summaries.append({
            "name": src.get("fullyQualifiedName", "unknown"),
            "description": src.get("description", "No description available"),
            "tableType": src.get("tableType", "unknown")
        })

    context = json.dumps(table_summaries, indent=2)

    prompt = f"""You are MetaBot, a helpful data catalog assistant.

The user asked: "{question}"

Here are the most relevant tables found in OpenMetadata:
{context}

Describe these tables in a helpful way. Explain what data they contain 
and how they might be useful. Keep it under 200 words and use bullet points."""

    answer = await ask_ollama(prompt)
    return QueryResponse(
        question=question,
        answer=answer,
        tool_used="search",
        tables_found=len(hits)
    )


# ── API endpoints ────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def handle_query(req: QueryRequest):
    """Main endpoint — accepts a natural language question and returns an answer."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    intent = detect_intent(req.question)

    if intent == "lineage":
        return await handle_lineage(req.question)
    elif intent == "missing_owners":
        return await handle_missing_owners(req.question)
    elif intent == "pii":
        return await handle_pii(req.question)
    else:
        return await handle_search(req.question)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": OLLAMA_MODEL,
        "openmetadata": os.getenv("OPENMETADATA_URL")
    }


@app.get("/intents")
async def list_intents():
    """Show what kinds of questions MetaBot understands."""
    return {
        "supported_intents": {
            "lineage": "Questions about data flow, upstream/downstream tables",
            "missing_owners": "Questions about unowned or ungoverned tables",
            "pii": "Questions about sensitive or personal data columns",
            "search": "General questions about finding tables or data"
        },
        "example_questions": [
            "What is the lineage of dim_customer?",
            "Which tables have missing owners?",
            "Does the customer table have any PII columns?",
            "Show me tables related to orders"
        ]
    }