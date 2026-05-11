# Architecture

## Goals

1. **Demonstrate MCP** end-to-end: client → multiple servers → tool selection → result synthesis.
2. **Stay cheap**: free-tier deployable, minimal LLM tokens, no GPU.
3. **Stay deterministic**: an agent that reliably terminates and produces structured output, not a recursive autonomous loop.
4. **Look like a real product**: streaming UI, reasoning timeline, polished SaaS shell.

## Why MCP, and how we use it

MCP gives us a uniform tool-server contract. A future client (Claude Desktop, an
internal IDE plugin, another agent runtime) can connect to the same servers
without changes. The four servers are split by domain so each stays small and
testable:

| Server | Boundary | External deps |
|---|---|---|
| `pubchem_server` | Identity + metadata | PubChem PUG REST |
| `rdkit_server` | Pure-compute cheminformatics | RDKit only |
| `papers_server` | Document ingestion + retrieval | pypdf, Chroma, embeddings API |
| `toxicity_server` | Risk scoring + structural alerts | RDKit |

We run them **in-process** via the MCP Python SDK's in-memory stream
transport (`create_connected_server_and_client_session`). Each server is a
real `mcp.server.Server` with `@list_tools()` / `@call_tool()` handlers; the
FastAPI worker starts them in an anyio task group at lifespan startup and
connects a `ClientSession` to each. Every tool call is JSON-RPC over an
in-memory stream pair — the same protocol an external client would use over
stdio, just without serialising bytes through a pipe.

Why this matters: the only thing separating us from running each server as a
subprocess (or remote service) is swapping
`create_connected_server_and_client_session` for `stdio_client(...)` in
`mcp_client/client.py`. The server modules themselves don't change. This is
the "exit ramp" — and because we're using the real SDK both sides, we know
the swap will actually work.

## Agent design

The orchestrator is **not** a fully autonomous ReAct loop. It is a small graph:

```
classify_intent → plan_tools → execute (parallel where safe) → synthesize → finalize
```

- `classify_intent` is a single small LLM call (cheap) that picks one of
  {compound_analysis, paper_qa, full_report}.
- `plan_tools` is deterministic: each intent maps to a fixed tool sequence.
  The LLM only enters again at `synthesize` (one call) and `finalize` (one
  call, structured output).
- The "agent reasoning trace" the UI shows is real: every tool call, args,
  duration, and LLM step is appended to a trace event stream.

This gives us reasoning transparency without unbounded token cost. Worst case
per analysis: ~3 LLM calls.

## Toxicity scoring — honest disclosure

Real toxicity prediction needs ML models trained on Tox21 / ToxCast / DrugBank
labels (e.g., DeepTox, ProTox-II). Including a trained model would blow the
free-tier budget and inflate the deploy artifact.

What we ship instead:

1. **Structural alerts**: a curated SMARTS list (PAINS, reactive groups,
   mutagenicity flags from the public Brenk + PAINS A/B/C alerts) matched via
   RDKit substructure search.
2. **Physchem flags**: Lipinski Ro5 violations, TPSA, logP outliers — derived
   from RDKit descriptors.
3. **LLM rationale**: the LLM is given the structural-alert hits and physchem
   flags and asked to write the human-readable risk summary, citing the
   retrieved literature. It does **not** invent a numeric score; the score is
   computed in Python from rule weights.

The report viewer surfaces this caveat explicitly.

## Data flow: PDF analysis

```
upload → pypdf parse → 1.2k-token chunks (200 overlap)
       → OpenAI text-embedding-3-small → ChromaDB (persistent volume)
       → at query time: top-k=6 retrieval → LLM synthesis with inline [n] cites
```

Chunks store: `{paper_id, chunk_idx, page, text, embedding}`. The viewer
resolves citations back to page numbers.

## Persistence

| Store | Used for |
|---|---|
| Supabase Postgres | Users, analyses, reports, paper metadata |
| ChromaDB (volume) | Chunk embeddings |
| Local FS (volume) | Uploaded PDFs |

Schema lives in [backend/app/db/schema.sql](backend/app/db/schema.sql).

## Trade-offs we accepted

- **In-process MCP**: simpler deploy, gives up process isolation. Acceptable
  for MVP; documented exit path is to run each server as a sidecar.
- **Heuristic toxicity**: see above. Honest about it in UI + README.
- **No vector DB SaaS**: Chroma on a persistent volume is free and good enough
  at MVP scale. Pinecone / Supabase pgvector is a swap of one module.
- **No queue**: PDF ingest is sync with a progress stream. Past ~50 pages we'd
  need a worker — out of scope for MVP.
- **No auth UI**: Supabase is wired, but the demo runs as a single-tenant
  workspace. Adding auth is a frontend addition, not an architecture change.

## Scaling exit ramps

- Split MCP servers into separate containers (config-only).
- Move embeddings to pgvector (drop Chroma).
- Add Celery/Arq + Redis for async ingest.
- Replace heuristic toxicity with a hosted ML inference endpoint behind the
  same MCP server interface — the agent doesn't change.
