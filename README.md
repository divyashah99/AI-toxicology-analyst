# AI Toxicology Analyst

A production-shaped MVP of a biotech AI platform for compound analysis, scientific literature retrieval, and toxicity reporting — built around **Model Context Protocol (MCP)** tool orchestration.

> **What it is**: a deployable AI research assistant that takes a compound (name or SMILES) or a research PDF, runs a deterministic agent over a set of MCP servers (PubChem, RDKit, Papers, Toxicity), and produces a citation-aware toxicity report with a transparent reasoning trace.
>
> **What it isn't**: a clinical decision system. The toxicity scoring is a rule-based heuristic layer combined with LLM reasoning over real data (PubChem, RDKit descriptors, retrieved literature). It is suitable for screening / interview demo, not regulatory submission.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15, TS, Tailwind, shadcn/ui)              │
│  - landing / dashboard / analyze / papers / reports          │
│  - streaming chat + MCP activity timeline                    │
└──────────────┬───────────────────────────────────────────────┘
               │ HTTPS (SSE for streaming)
┌──────────────▼───────────────────────────────────────────────┐
│  Backend (FastAPI, async)                                    │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  Agent Orchestrator  (deterministic graph + LLM)      │   │
│  └──────────────┬────────────────────────────────────────┘   │
│                 │  MCP client (in-process stdio bridge)      │
│  ┌──────────────▼────────────────────────────────────────┐   │
│  │  MCP Servers (4)                                      │   │
│  │   • PubChem  • RDKit  • Papers  • Toxicity            │   │
│  └──────────────┬────────────────────────────────────────┘   │
│                 │                                            │
│   Supabase Postgres   ChromaDB (persistent)   PubChem REST   │
└──────────────────────────────────────────────────────────────┘
```

All MCP servers run in-process inside the same backend container — no
microservice sprawl, free-tier friendly, single deploy unit.

See [ARCHITECTURE.md](ARCHITECTURE.md) for design details and trade-offs.

---

## Features

| Capability | Status | Notes |
|---|---|---|
| Compound lookup by name / SMILES | ✅ real | PubChem PUG REST |
| Molecular descriptors / fingerprints | ✅ real | RDKit |
| PDF ingest → chunk → embed → retrieve | ✅ real | pypdf + ChromaDB + OpenAI embeddings |
| Toxicity score | ⚠️ heuristic | structural alerts + Lipinski + LLM rationale; **not a trained model** |
| MCP tool orchestration | ✅ real | MCP Python SDK; `mcp.server.Server` + `ClientSession` over in-memory streams |
| Streaming reasoning trace | ✅ real | SSE from FastAPI to Next.js |
| Auth / multi-tenant | ❌ MVP | Supabase wired but RLS not enforced |

---

## Quick start (local)

Prereqs: Docker + Docker Compose, Node 20+, Python 3.11+, an OpenAI API key.

```bash
cp .env.example .env                   # fill in keys
docker compose up --build              # backend + chroma
cd frontend && pnpm install && pnpm dev
```

Open http://localhost:3000.

Run without Docker: see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Deploy

- **Frontend**: Vercel — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#vercel)
- **Backend**: Railway or Render — same doc, [Railway](docs/DEPLOYMENT.md#railway) / [Render](docs/DEPLOYMENT.md#render)

---

## Repo layout

```
AI-toxicology-analyst/
├── frontend/              Next.js 15 app
├── backend/               FastAPI + MCP servers
│   └── app/
│       ├── api/routes/    HTTP endpoints
│       ├── agent/         Orchestrator + prompts + trace
│       ├── mcp_servers/   4 in-process MCP servers
│       ├── mcp_client/    Client that drives them
│       ├── services/      PubChem, RDKit, papers, chroma...
│       └── db/            Supabase + schema
├── data/seed/             Demo compounds for offline demo
├── docs/                  Deployment + development guides
└── docker-compose.yml
```

## Cost posture

The agent uses LLMs only for: routing tool selection, summarization, and report
prose. All numeric work (descriptors, similarity, toxicity rules, retrieval
ranking) happens in Python. The default model is `gpt-4.1-mini`; swap to Groq
via `LLM_PROVIDER=groq` for free-tier inference.

## License

MIT.
