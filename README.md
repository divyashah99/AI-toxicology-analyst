# AI Toxicology Analyst

A full-stack AI platform for compound toxicity analysis, scientific literature retrieval, and structured report generation — built around **Model Context Protocol (MCP)** tool orchestration.

The system takes a compound (name or SMILES string) or a research PDF, runs a deterministic agent over a coordinated set of MCP tool servers, and produces a structured toxicity report with a transparent, step-by-step reasoning trace visible in the UI.

---

## What it does

### Compound Analysis
Enter any compound by common name (e.g. "caffeine") or SMILES string. The agent automatically:
1. Resolves the compound identity via PubChem (canonical name, CID, molecular formula, InChI key, SMILES)
2. Computes molecular descriptors via RDKit (molecular weight, logP, H-bond donors/acceptors, rotatable bonds, TPSA, ring count)
3. Generates a Morgan fingerprint and checks Tanimoto similarity against any previously analyzed compounds
4. Runs structural alert screening against a library of SMARTS patterns (epoxides, Michael acceptors, aldehydes, nitro groups, quinones, alkyl halides, and more)
5. Applies Lipinski rule-of-five flags
6. Scores the compound on a 0–100 toxicity scale derived from how many alert categories fire
7. Classifies risk as LOW / MODERATE / HIGH / VERY HIGH with a confidence estimate
8. Queries the embedded paper library for relevant literature passages
9. Passes all of the above — PubChem data, descriptors, alert hits, retrieved passages — to an LLM that writes a structured toxicity narrative with citations and mechanistic rationale

The full tool call sequence is streamed live to the UI as an MCP activity timeline so you can follow exactly which server answered which step.

### Scientific Literature (Papers)
Upload research PDFs. The backend:
- Extracts text with `pypdf`
- Chunks it into overlapping segments
- Embeds each chunk with OpenAI's embedding model
- Stores vectors in ChromaDB with paper metadata

During compound analysis or chat, the Papers MCP server performs semantic retrieval over the stored library and returns ranked passages. `library_stats` reports total papers and chunks indexed.

### Chat
A streaming chat interface grounded in the uploaded paper library. Ask questions in natural language; the agent retrieves the most relevant passages from ChromaDB and uses them as context before generating a response. Answers cite the source papers.

### Reports
Every compound analysis is persisted to Supabase PostgreSQL as a structured JSON payload. The reports list page shows:
- Total reports, counts by risk band, most common structural alert
- Search by compound name
- Filter by risk band (All / High / Moderate / Low)
- Alert count per row

Each report detail page shows the full `CompoundCard` (identity, descriptors, risk badge, score breakdown) and the complete rendered report, with a **Re-analyze** button that pre-fills the analyze form and re-runs the agent.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15, TypeScript, Tailwind, shadcn/ui)      │
│  Landing · Dashboard · Analyze · Papers · Chat · Reports     │
│  SSE streaming consumer · MCP activity timeline              │
└──────────────┬───────────────────────────────────────────────┘
               │ HTTPS  (Server-Sent Events for streaming)
┌──────────────▼───────────────────────────────────────────────┐
│  Backend (FastAPI, fully async)                              │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Agent Orchestrator                                  │    │
│  │  Deterministic tool graph → LLM synthesis step       │    │
│  │  Emits SSE trace events at each tool call            │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │  MCP ClientSession (JSON-RPC)      │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  MCP Servers (4, in-process)                         │    │
│  │  pubchem · rdkit · papers · toxicity                 │    │
│  └──────┬──────────┬──────────┬──────────┬─────────────┘    │
│         │          │          │          │                   │
│   PubChem REST   RDKit    ChromaDB   Rule engine             │
│         │                    │                               │
│   Supabase PostgreSQL   OpenAI Embeddings API                │
└──────────────────────────────────────────────────────────────┘
```

All MCP servers run **in-process** inside the same backend container — no microservice sprawl, straightforward to deploy on a single free-tier host.

---

## MCP servers and tools

The backend exposes four MCP servers, each implementing the `mcp.server.Server` interface. The agent drives them through `ClientSession` over in-memory JSON-RPC streams (no socket, no subprocess).

### `pubchem`
Wraps the PubChem PUG REST API. No API key required.

| Tool | What it does |
|---|---|
| `search_compound` | Resolves a name or SMILES to a PubChem CID, returns canonical name, molecular formula, InChI key |
| `get_properties` | Fetches SMILES, MW, logP, TPSA, H-bond counts, rotatable bonds, heavy atom count for a given CID |
| `get_synonyms` | Returns the full synonym list for a CID (trade names, IUPAC name, CAS number, database cross-refs) |

### `rdkit`
Runs RDKit calculations locally — no external call, deterministic, fast.

| Tool | What it does |
|---|---|
| `descriptors` | Computes Lipinski descriptors (MW, logP, HBD, HBA), TPSA, ring count, rotatable bonds from a SMILES string |
| `canonicalize` | Returns the canonical RDKit SMILES for any input SMILES (normalizes representation) |
| `fingerprint` | Generates a Morgan fingerprint (radius 2, 2048 bits) as a bit-vector string |
| `similarity` | Computes Tanimoto similarity between two SMILES strings using Morgan fingerprints |

### `papers`
Manages the embedded literature library backed by ChromaDB.

| Tool | What it does |
|---|---|
| `retrieve` | Semantic search over all ingested paper chunks; returns top-k passages with source metadata and similarity scores |
| `library_stats` | Returns total document count, total chunk count, and collection metadata |

### `toxicity`
Rule-based screening engine. All logic runs locally in Python — no model weights, deterministic output.

| Tool | What it does |
|---|---|
| `score` | Runs structural alert SMARTS matching + Lipinski flag checks; returns a 0–100 score and per-category hit list |
| `alerts` | Returns the full list of structural alerts that fired, each with name, SMARTS, and severity |
| `classify` | Maps a numeric score to a risk band (LOW / MODERATE / HIGH / VERY HIGH) with a confidence estimate |

**Important**: the toxicity score is a structural heuristic, not a trained predictive model. It correctly scores parent structures that carry electrophilic or reactive groups directly. Compounds whose toxicity arises from metabolic bioactivation (e.g. Aflatoxin B1, which requires CYP450 conversion to its reactive epoxide) will score low on the parent structure. The LLM synthesis step compensates for this by reasoning over known mechanisms when literature is present.

---

## API endpoints

All endpoints are served from the FastAPI backend. The frontend proxies them through `/api/backend/*` (configured in `next.config.ts`).

| Method | Path | Description |
|---|---|---|
| `GET` | `/healthz` | Liveness check — returns `{"status":"ok"}` |
| `POST` | `/analyze` | One-shot compound analysis; returns full report JSON |
| `POST` | `/analyze/stream` | Streaming compound analysis; SSE stream of trace events + final report |
| `GET` | `/analyze/servers` | Lists all registered MCP servers and their available tools |
| `POST` | `/papers/upload` | Upload a PDF; triggers extraction, chunking, and embedding |
| `GET` | `/papers` | Lists all uploaded papers with metadata |
| `DELETE` | `/papers/{paper_id}` | Removes a paper and its embeddings from ChromaDB |
| `POST` | `/chat/stream` | Streaming RAG chat; SSE stream of grounded response tokens |
| `GET` | `/reports` | Lists all persisted toxicity reports (id, compound name, risk band, created_at) |
| `GET` | `/reports/{report_id}` | Fetches full report payload for a single report |
| `DELETE` | `/reports/{report_id}` | Permanently deletes a report |

Interactive API docs are available at `/docs` (Swagger UI) and `/redoc`.

---

## Frontend pages

| Route | Description |
|---|---|
| `/` | Landing page — project overview and call-to-action |
| `/dashboard` | Activity summary — recent reports, quick stats |
| `/analyze` | Compound analysis form; streams MCP timeline + renders report live |
| `/papers` | Upload and manage PDFs; shows library stats |
| `/chat` | Streaming RAG chat grounded in uploaded literature |
| `/reports` | Paginated, searchable, filterable list of all saved reports |
| `/reports/[id]` | Full report detail — compound card, descriptors, risk badge, narrative, re-analyze |

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.11, async/await throughout |
| MCP | `mcp` Python SDK — `mcp.server.Server`, `ClientSession`, in-process JSON-RPC |
| Cheminformatics | RDKit (descriptors, fingerprints, SMARTS), PubChem PUG REST API |
| Vector store | ChromaDB with persistent local storage |
| Embeddings | OpenAI `text-embedding-3-small` (or compatible) |
| LLM | OpenAI (default: `gpt-4.1-mini`) or Groq (free-tier compatible) |
| Database | Supabase PostgreSQL; falls back to in-process memory store if not configured |
| Streaming | FastAPI `StreamingResponse` (SSE) → Next.js `EventSource` |
| Rate limiting | SlowAPI (per-IP, configurable) |
| Containerization | Docker + Docker Compose |

---

## Quick start (local)

**Prerequisites**: Docker + Docker Compose, Node 20+, Python 3.11+, an OpenAI or Groq API key.

```bash
cp .env.example .env        # fill in keys — see table below
docker compose up --build   # starts backend (FastAPI) + ChromaDB volume
cd frontend && pnpm install && pnpm dev
```

Open http://localhost:3000.

To run without Docker, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | Yes | `openai` | `openai` or `groq` |
| `OPENAI_API_KEY` | If provider=openai | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4.1-mini` | Chat model ID |
| `OPENAI_EMBED_MODEL` | No | `text-embedding-3-small` | Embedding model ID |
| `GROQ_API_KEY` | If provider=groq | — | Groq API key |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model ID |
| `SUPABASE_URL` | No | — | Supabase project URL; omit to use in-memory store |
| `SUPABASE_SERVICE_KEY` | No | — | Supabase service role key |
| `CHROMA_PERSIST_DIR` | No | `/data/chroma` | Directory for ChromaDB storage |
| `UPLOAD_DIR` | No | `/data/uploads` | Directory for uploaded PDFs |
| `MAX_UPLOAD_MB` | No | `20` | Maximum PDF upload size |
| `BACKEND_CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed origins |
| `RATE_LIMIT_PER_MIN` | No | `30` | Requests per IP per minute |
| `NEXT_PUBLIC_API_BASE` | Yes (prod) | `http://localhost:8000` | Backend base URL seen by the frontend |

---

## Deploy (free tier)

The full stack can be deployed at no cost:

| Layer | Host |
|---|---|
| Frontend | Vercel Hobby (free) |
| Backend | Render free Web Service |
| Database | Supabase free tier |
| Vector store | ChromaDB on the backend container (ephemeral on Render free — resets on cold start) |

Step-by-step instructions: [docs/DEPLOY_LIVE.md](docs/DEPLOY_LIVE.md).

---

## Repo layout

```
AI-toxicology-analyst/
├── frontend/                  Next.js 15 application
│   └── app/
│       ├── (app)/             Authenticated app shell
│       │   ├── analyze/       Compound analysis page
│       │   ├── chat/          RAG chat page
│       │   ├── dashboard/     Summary dashboard
│       │   ├── papers/        PDF library management
│       │   └── reports/       Report list + detail pages
│       └── page.tsx           Landing page
├── backend/
│   └── app/
│       ├── api/routes/        HTTP endpoints (analyze, papers, chat, reports)
│       ├── agent/             Orchestrator, prompt templates, SSE trace emitter
│       ├── mcp_servers/       4 in-process MCP servers (pubchem, rdkit, papers, toxicity)
│       ├── mcp_client/        ClientSession wrapper that drives the servers
│       ├── services/          PubChem HTTP client, RDKit helpers, ChromaDB service
│       └── db/                Supabase client + in-memory fallback store
├── docs/
│   ├── DEVELOPMENT.md         Local dev setup (no Docker)
│   ├── DEPLOY_LIVE.md         Free-tier cloud deployment walkthrough
│   └── SUPABASE_SETUP.md      Supabase schema and configuration guide
├── data/seed/                 Sample compounds for offline testing
└── docker-compose.yml
```

---

## Known limitations

- **Structural alert heuristic**: the toxicity score matches SMARTS patterns against the parent structure. Compounds toxic only after metabolic activation (e.g. prodrugs, mycotoxins that form reactive epoxides via CYP450) will score lower than their actual hazard. The LLM synthesis step reasons over known mechanisms to partially compensate, but this is not a substitute for metabolite-aware or experimentally-validated models.
- **Not for regulatory use**: reports are informational. They should not be used as the basis for clinical, occupational health, or regulatory decisions without expert review and validated assay data.
- **ChromaDB on free hosting**: Render's free tier has no persistent disk. Uploaded PDFs and their embeddings are lost on container restarts. Compound analysis and reports are unaffected (those persist in Supabase).
- **Single-worker backend**: the backend runs with `--workers 1` to keep in-process ChromaDB and MCP server state consistent. Scale by replicating containers behind a load balancer.

---

## License

MIT
