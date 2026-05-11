# Deployment

Two services to deploy: the **backend** (FastAPI + MCP servers + Chroma) and
the **frontend** (Next.js). Both fit on free tiers.

## Vercel (frontend)

1. Push the repo to GitHub.
2. In Vercel: New Project → import the repo → set the root to `frontend/`.
3. Framework: Next.js (auto-detected). No build overrides needed.
4. Environment variables:
   - `NEXT_PUBLIC_API_BASE` = your deployed backend URL (e.g.
     `https://tox-backend.up.railway.app`).
5. Deploy.

The frontend is fully static + edge except for the `/api/backend/*` rewrite
(set in `next.config.ts`), which proxies to the backend if you'd rather not
expose `NEXT_PUBLIC_API_BASE` directly.

## Railway (backend)

1. New Project → Deploy from GitHub repo.
2. Set the **service root** to `backend/`. Railway will detect the Dockerfile.
3. Add a **persistent volume** at `/data` (1 GB free tier is plenty for
   Chroma + a handful of PDFs).
4. Variables (copy from `.env.example`):
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL=gpt-4.1-mini`
   - `CHROMA_PERSIST_DIR=/data/chroma`
   - `UPLOAD_DIR=/data/uploads`
   - `BACKEND_CORS_ORIGINS=https://your-vercel-app.vercel.app`
   - (optional) `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
5. Deploy. The healthcheck hits `/healthz`.

The default Dockerfile uses one uvicorn worker on purpose — Chroma's
PersistentClient is single-process. To scale, replicate the container
horizontally and put a load balancer in front; do **not** raise `--workers`.

## Render (backend, alternative)

1. New Web Service → connect repo → set the root directory to `backend/`.
2. Environment: Docker. Render will pick up the Dockerfile.
3. Add a Disk mounted at `/data`.
4. Same env vars as the Railway list above.
5. Health check path: `/healthz`.

## Supabase

Optional but recommended for persistence beyond a single container restart.

Full walkthrough with screenshots-worthy steps: [SUPABASE_SETUP.md](SUPABASE_SETUP.md).

Short version:
1. Create a free project at supabase.com.
2. SQL editor → paste [`backend/app/db/schema.sql`](../backend/app/db/schema.sql) → Run.
3. Project settings → API → copy **Project URL** and **service_role** key
   into the backend env as `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.

If Supabase env vars are absent, the backend transparently falls back to an
in-memory store — useful for the cheapest possible demo.

## Cost ceiling — back-of-envelope

| Item | Free-tier path |
|---|---|
| Frontend hosting | Vercel Hobby |
| Backend hosting | Railway $5 credit / Render free / Fly.io free |
| Vector DB | Chroma on persistent volume (no SaaS fee) |
| Postgres | Supabase free tier (500 MB) |
| LLM | `gpt-4.1-mini` (~$0.15 per 1M in / $0.60 per 1M out) — agent is bounded to ~3 calls per analysis. Or set `LLM_PROVIDER=groq` for free Llama-3.1-70B inference. |
| Embeddings | `text-embedding-3-small` (~$0.02 / 1M tokens). A 30-page PDF ≈ <$0.001 to embed. |

A demo session of 10 compound analyses + 5 PDFs typically costs **< $0.05**
on OpenAI. Groq mode is **$0**.

## Production checklist (when you outgrow MVP)

- [ ] Add Supabase RLS + auth UI (Next.js middleware).
- [ ] Move Chroma → Supabase pgvector (one module swap in `services/chroma.py`).
- [ ] Split MCP servers into sidecar containers if you need process isolation.
- [ ] Add Sentry / structured log shipping.
- [ ] Replace heuristic toxicity with a hosted ML model behind the same
      `mcp_servers/toxicity_server.py` interface.
