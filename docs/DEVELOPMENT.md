# Development

## Prereqs

- Python 3.11+ (RDKit wheels are 3.11/3.12 friendly)
- Node 20+ and pnpm (or npm)
- Docker (optional, recommended)
- An OpenAI API key (or Groq key + `LLM_PROVIDER=groq`)

## Local run — without Docker

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env                            # fill in OPENAI_API_KEY
export $(grep -v '^#' ../.env | xargs)                # PowerShell: see below
uvicorn app.main:app --reload --port 8000
```

PowerShell variant for env vars:
```powershell
Get-Content ..\.env | Where-Object { $_ -and -not $_.StartsWith("#") } | ForEach-Object {
    $k,$v = $_ -split "=",2
    [System.Environment]::SetEnvironmentVariable($k, $v, "Process")
}
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pnpm install            # or npm install
cp .env.example .env.local
pnpm dev
```

Open http://localhost:3000.

## Local run — Docker Compose

```bash
cp .env.example .env    # fill in OPENAI_API_KEY
docker compose up --build
# in another shell:
cd frontend && pnpm install && pnpm dev
```

The compose file deliberately runs only the backend in a container; the
frontend stays on `pnpm dev` for fast iteration. Vercel handles it in prod.

## Smoke test the agent

```bash
curl -s http://localhost:8000/healthz
curl -s -X POST http://localhost:8000/api/analyze \
  -H 'content-type: application/json' \
  -d '{"query":{"name":"caffeine"}}' | jq '.report.toxicity'
```

You should see something like:
```json
{ "score": 0.0, "risk_band": "low", "confidence": 0.4, ... }
```

## Layout

```
backend/app/
  main.py              FastAPI entry
  config.py            settings (pydantic-settings)
  agent/               deterministic orchestrator + prompts + trace
  mcp_client/          drives the in-process MCP servers
  mcp_servers/         pubchem, rdkit, papers, toxicity
  services/            domain code each MCP server wraps
  api/routes/          analyze, papers, reports, chat
  db/                  Supabase wrapper + schema
  models/              pydantic schemas

frontend/
  app/                 Next 15 app router; (app)/* is the SaaS shell
  components/          sidebar, topbar, mcp-timeline, report-viewer, ...
  components/ui/       shadcn-style primitives
  lib/                 api client + types
  hooks/               use-analyze-stream
```

## Testing the SSE flow by hand

```bash
curl -N -X POST http://localhost:8000/api/analyze/stream \
  -H 'content-type: application/json' \
  -d '{"query":{"name":"aspirin"}}'
```

You'll see `event: tool_call`, `event: tool_result`, `event: llm_chunk` lines
stream as the agent runs.
