# 🤖 MetaBot — AI-Powered Natural Language Agent for OpenMetadata

> **WeMakeDevs × OpenMetadata Hackathon 2026**  
> Track: T-01 (MCP Ecosystem & AI Agents) + T-06 (Governance & Classification)

<div align="center">

![MetaBot Demo](demo/preview.png)

**Ask your data catalog anything. In plain English.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![OpenMetadata](https://img.shields.io/badge/OpenMetadata-1.12.5-orange?style=flat-square)](https://open-metadata.org)
[![Ollama](https://img.shields.io/badge/Ollama-Mistral_7B-purple?style=flat-square)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## 🎯 What is MetaBot?

MetaBot is an **AI-powered MCP (Model Context Protocol) server** that lets you query your entire OpenMetadata data catalog using plain English — no SQL, no dashboards, no complex UI.

Instead of navigating menus to find tables, check lineage, or audit PII, you just ask:

```
"Which tables have missing owners?"
"Does the customer table have sensitive PII columns?"
"What is the lineage of fact_order?"
"Show me tables related to orders"
```

MetaBot understands your question, queries OpenMetadata's REST API, runs AI analysis where needed, and returns a clear human-readable answer — powered by a **local Mistral 7B LLM running on your GPU via Ollama**. Zero API costs. Complete privacy.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Natural Language Search** | Find tables by describing what you're looking for |
| 🔐 **PII Detection** | Auto-scan columns for personal data using pattern matching + spaCy NLP |
| 🔗 **Lineage Queries** | Trace upstream and downstream data flow in plain English |
| 👤 **Governance Audit** | Find tables with missing owners and get actionable recommendations |
| 🤖 **Local LLM** | Runs Mistral 7B on your GPU via Ollama — no API keys, no cost |
| 💬 **Chat Interface** | Clean dark-themed chat UI with example queries and session stats |
| ⚡ **Fast Routing** | Intent detection routes queries to the right tool instantly |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Demo Chat UI                        │
│              (HTML + CSS + JS — port 3000)              │
└──────────────────────┬──────────────────────────────────┘
                       │ POST /query
┌──────────────────────▼──────────────────────────────────┐
│                   MCP Server                            │
│               (FastAPI — port 8001)                     │
│                                                         │
│  detect_intent() → routes to correct handler            │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐     │
│  │ search   │ │ lineage  │ │   pii   │ │  owners  │     │
│  └────┬─────┘ └────┬─────┘ └────┬────┘ └────┬─────┘     │
└───────┼────────────┼────────────┼────────────┼──────────┘
        │            │            │            │
┌───────▼────────────▼────────────▼────────────▼──────────┐
│              OpenMetadata REST API                      │
│                  (port 8585)                            │
│   /search/query  /lineage  /tables  + spaCy NLP         │
└─────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────┐
│                  Ollama (local LLM)                      │
│            Mistral 7B — RTX 3050 GPU                     │
│                   port 11434                             │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Docker Desktop | Latest | Run OpenMetadata |
| Ollama | Latest | Local LLM inference |
| WSL2 (Windows) | Ubuntu 22.04 | Linux environment |
| NVIDIA GPU | 4GB+ VRAM | Run Mistral 7B |

> **No GPU?** Use `phi3:mini` instead — runs on CPU. Change `OLLAMA_MODEL=phi3:mini` in `.env`.

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/metabot-openmetadata.git
cd metabot-openmetadata
```

### Step 2 — Set up Python environment

```bash
python3 -m venv venv
source venv/bin/activate          # Linux / WSL
# venv\Scripts\activate           # Windows CMD

pip install -r requirements.txt
python3 -m spacy download en_core_web_sm
```

### Step 3 — Start OpenMetadata with Docker

```bash
# Create a separate folder for OpenMetadata
mkdir ~/openmetadata-docker && cd ~/openmetadata-docker

# Download the compose file
curl -sL -o docker-compose.yml https://github.com/open-metadata/OpenMetadata/releases/download/1.12.5-release/docker-compose.yml

# Start dependencies first
docker compose up -d mysql elasticsearch
sleep 30

# Run migrations
docker compose up execute-migrate-all

# Start everything
docker compose up -d
```

Wait for `openmetadata_server` to show `(healthy)` in `docker ps`.

Open `http://localhost:8585` — login with `admin@open-metadata.org` / `admin`.

### Step 4 — Install and start Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Mistral 7B (~4.1 GB)
ollama pull mistral

# Verify
ollama run mistral "Say hello in one sentence"
```

### Step 5 — Configure environment

```bash
cd metabot-openmetadata
cp .env.example .env
```

Edit `.env`:
```env
OPENMETADATA_URL=http://localhost:8585
OPENMETADATA_TOKEN=your_jwt_token_here
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

To get your JWT token: OpenMetadata UI → Settings → Bots → ingestion-bot → copy token.

### Step 6 — Start MetaBot server

```bash
source venv/bin/activate
cd server
uvicorn main:app --reload --port 8001
```

You should see:
```
INFO: Application startup complete.
```

### Step 7 — Open the demo UI

```bash
# In a second terminal
cd demo
python3 -m http.server 3000
```

Get your WSL IP:
```bash
hostname -I
```

Open browser → `http://YOUR_WSL_IP:3000`

Click ⚙ config → set server URL to `http://YOUR_WSL_IP:8001` → Save.

Green dot = you're live. Start asking questions!

---

## 📁 Project Structure

```
metabot-openmetadata/
│
├── server/                          # MCP Server (FastAPI)
│   ├── main.py                      # Main server — routing + Ollama integration
│   ├── utils/
│   │   └── openmetadata.py          # OpenMetadata REST API client
│   └── tools/
│       └── pii.py                   # PII detection — patterns + spaCy NLP
│
├── demo/                            # Frontend chat interface
│   ├── index.html                   # Main HTML
│   ├── style.css                    # Dark terminal theme
│   └── app.js                       # Chat logic + API calls
│
├── .env.example                     # Environment variables template
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

---

## 🔌 API Reference

### `POST /query`

Main endpoint — accepts a natural language question.

**Request:**
```json
{
  "question": "does the customer table have PII columns?"
}
```

**Response:**
```json
{
  "question": "does the customer table have PII columns?",
  "answer": "The dim_customer table contains 6 high-confidence PII columns including first_name, last_name, email, phone, and shipping_address...",
  "tool_used": "pii",
  "tables_found": 4
}
```

### `GET /health`

Health check — confirms server and model are running.

```json
{
  "status": "ok",
  "model": "mistral",
  "openmetadata": "http://localhost:8585"
}
```

### `GET /intents`

Lists all supported query types with examples.

---

## 🧠 How Intent Detection Works

MetaBot uses keyword-based intent detection to route questions to the right tool:

| Intent | Trigger keywords | Tool called |
|--------|-----------------|-------------|
| `greeting` | hi, hello, hey | Friendly intro response |
| `lineage` | lineage, upstream, downstream, flow | `get_lineage()` |
| `missing_owners` | missing owner, no owner, unowned | `get_tables_missing_owners()` |
| `pii` | pii, sensitive, personal data, gdpr | `detect_pii_columns()` |
| `search` | everything else | `search_tables()` |

---

## 🔐 PII Detection

MetaBot uses a **two-layer PII detection system**:

**Layer 1 — Pattern matching (High confidence)**
Checks column names against 24 known PII patterns:
```
email, phone, first_name, last_name, ssn, passport,
address, dob, credit_card, national_id, salary, ...
```

**Layer 2 — spaCy NLP (Medium confidence)**
Runs the `en_core_web_sm` model on column descriptions.
Flags columns whose descriptions mention sensitive entity types:
`PERSON`, `GPE` (location), `LOC`

Results are returned with confidence levels so humans can make final decisions.

---

## 💻 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | FastAPI + Python | Async, fast, auto-docs |
| LLM | Mistral 7B via Ollama | Free, local, private |
| NLP | spaCy `en_core_web_sm` | Lightweight PII detection |
| Metadata | OpenMetadata 1.12.5 | Open source data catalog |
| HTTP client | httpx | Async HTTP requests |
| Data validation | Pydantic | Request/response schemas |
| Frontend | HTML + CSS + JS | Zero dependencies, runs anywhere |


---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [OpenMetadata](https://open-metadata.org) — the open source metadata platform powering this project
- [WeMakeDevs](https://wemakedevs.org) — for organizing this hackathon
- [Ollama](https://ollama.com) — for making local LLMs accessible
- [Mistral AI](https://mistral.ai) — for the Mistral 7B model

---

<div align="center">
Built with ❤️ for the WeMakeDevs × OpenMetadata Hackathon 2026
</div>
