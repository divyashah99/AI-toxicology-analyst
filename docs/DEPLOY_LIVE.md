# Deploy a live public link — free

Goal: a shareable `https://...vercel.app` URL anyone can hit, costing $0/month.

**Stack we'll use**

| Layer | Host | Cost |
|---|---|---|
| Frontend (Next.js) | **Vercel Hobby** | Free, no credit card |
| Backend (FastAPI + MCP) | **Render free Web Service** | Free, no credit card |
| Postgres | **Supabase free** | Free (already set up) |
| Vector store | ChromaDB on the backend container | Free, but **resets on cold start** — see caveats |
| LLM | OpenAI or Groq | Pay-as-you-go; $0.05 covers a busy demo session |

**Total deploy time**: ~20 minutes if it's your first time.

---

## Honest caveats up front

Read these before you start so you're not surprised:

1. **Render free spins down after 15 min of inactivity.** The next request triggers a cold start: ~30-60 s wait before the first response. The frontend will look "stuck" loading. For a demo, just hit the URL ~30 s before showing it.
2. **Render free has no persistent disk.** Uploaded PDFs and their ChromaDB embeddings vanish on every restart / cold start. Compound analysis works fine (no PDFs needed). Papers + chat features need a fresh upload each session.
3. **Render free is 512 MB RAM.** The backend image with RDKit + ChromaDB + onnxruntime fits, but barely. If you hit OOMs, the doc below has fallback options.
4. **Reports persist** — they're in Supabase, not Chroma. Survives everything.

If those caveats are dealbreakers, jump to the [Bullet-proof alternative](#bullet-proof-alternative-flyio-needs-a-credit-card) section.

---

## Step 0 — Prereqs

You need:
- A **GitHub** account
- Git installed locally (`git --version` should print a version)
- The Supabase project you set up earlier
- Your `OPENAI_API_KEY` (or `GROQ_API_KEY`)

---

## Step 1 — Push the repo to GitHub

The project isn't a git repo yet. Run from the project root (`C:\Users\divya\Repos\ProjectRepo\AI-toxicology-analyst`):

```powershell
git init
git add .
git status                        # sanity check — make sure .env is NOT listed
git commit -m "Initial commit: AI Toxicology Analyst MVP"
```

Confirm `.env` is **ignored**:
```powershell
git check-ignore -v .env
# should print: .gitignore:2:.env  .env
```

If `.env` shows up in `git status`, stop and fix `.gitignore` before you push. Your API keys are in that file.

Now create the GitHub repo:

1. Go to https://github.com/new
2. Name: `ai-toxicology-analyst` (or anything)
3. **Private** is fine (you can flip it later)
4. **Don't** add a README / .gitignore / license — we already have them
5. Click **Create repository**

GitHub will show a "push an existing repository" snippet. Run it locally:

```powershell
git branch -M main
git remote add origin https://github.com/<your-username>/ai-toxicology-analyst.git
git push -u origin main
```

Refresh the GitHub page — your code should be there.

---

## Step 2 — Deploy the backend to Render

1. Go to https://render.com → **Get Started** → sign in **with GitHub**. Authorize.
2. From the dashboard click **New +** → **Web Service**.
3. Connect your `ai-toxicology-analyst` repo. (If you don't see it, click "Configure account" and grant access.)
4. Fill in:

   | Field | Value |
   |---|---|
   | **Name** | `ai-toxicology-analyst-backend` (or any) |
   | **Region** | pick one near you |
   | **Branch** | `main` |
   | **Root Directory** | `backend` |
   | **Runtime** | **Docker** (Render auto-detects the Dockerfile) |
   | **Instance Type** | **Free** |

5. Scroll down to **Environment Variables** → click **Add Environment Variable** for each:

   | Key | Value |
   |---|---|
   | `OPENAI_API_KEY` | your OpenAI key |
   | `OPENAI_MODEL` | `gpt-4.1-mini` |
   | `LLM_PROVIDER` | `openai` |
   | `SUPABASE_URL` | your Supabase project URL |
   | `SUPABASE_SERVICE_KEY` | your Supabase **service_role** key |
   | `BACKEND_CORS_ORIGINS` | leave blank for now — you'll fill this after Vercel deploys |
   | `CHROMA_PERSIST_DIR` | `/tmp/chroma` (free tier has no persistent disk — ephemeral is fine for the demo) |
   | `UPLOAD_DIR` | `/tmp/uploads` |

6. Click **Create Web Service**.

Render starts the first build. Watch the logs — RDKit + ChromaDB pull is ~3-5 min the first time. You're looking for:

```
{"event": "startup", "model": "gpt-4.1-mini", "provider": "openai", ...}
{"event": "mcp.start", "servers": ["pubchem", "rdkit", "papers", "toxicity"], ...}
INFO: Uvicorn running on http://0.0.0.0:10000
INFO: Application startup complete.
```

The status pill at the top turns **green / Live**. Copy the URL Render assigns — it looks like:
```
https://ai-toxicology-analyst-backend.onrender.com
```

Smoke-test it:
```powershell
curl https://ai-toxicology-analyst-backend.onrender.com/healthz
# {"status":"ok"}
```

> **If the build OOMs or the service fails to start**, jump to [Memory troubleshooting](#memory-troubleshooting) below. The most common fix is switching to Render's $7/mo Starter plan.

---

## Step 3 — Deploy the frontend to Vercel

1. Go to https://vercel.com/new → sign in with GitHub.
2. Import the `ai-toxicology-analyst` repo.
3. Vercel asks for project settings:

   | Field | Value |
   |---|---|
   | **Framework Preset** | Next.js (auto-detected) |
   | **Root Directory** | `frontend` ← **important** |
   | **Build Command** | leave default (`next build`) |
   | **Output Directory** | leave default |

4. Expand **Environment Variables** and add:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://ai-toxicology-analyst-backend.onrender.com` ← your Render URL, no trailing slash |

5. Click **Deploy**. Build takes ~60 s.

Vercel gives you a URL like `https://ai-toxicology-analyst.vercel.app`. Don't open it yet — one more step.

---

## Step 4 — Wire CORS

The backend currently doesn't whitelist the Vercel domain, so the frontend can't talk to it.

1. Copy your Vercel URL.
2. Render dashboard → your backend service → **Environment** tab → edit `BACKEND_CORS_ORIGINS`:
   ```
   https://ai-toxicology-analyst.vercel.app
   ```
   (No trailing slash. If you'll use multiple Vercel preview URLs, comma-separate them.)
3. Click **Save Changes**. Render auto-redeploys.
4. Wait ~30 s for the redeploy, then open the Vercel URL.

You should see the landing page. Click **Open app →** → **Compound analysis** → click **Caffeine**.

The first call after a cold start is slow (~30-60 s while Render wakes the container). After that it's responsive.

🎉 **You now have a live public link to share.**

---

## Step 5 — Share it

Send anyone:
- **The app**: `https://ai-toxicology-analyst.vercel.app`
- **Backend docs (optional, dev-facing)**: `https://ai-toxicology-analyst-backend.onrender.com/docs`

Tell them to give it ~30 s on first click — the backend spins down between visitors on the free tier.

---

## Optional: keep the backend warm

Cold starts make the demo feel sluggish. Two ways to mitigate:

**a) Manual pre-warm** — 30 s before showing the demo, just hit `/healthz` yourself.

**b) Free uptime pinger** — set up a free [cron-job.org](https://cron-job.org) (or [UptimeRobot](https://uptimerobot.com)) entry to hit `/healthz` every 10 minutes.

> ⚠️ Render's terms allow health pings, but if you ping too aggressively to dodge the free-tier idle timer, they may flag the service. 10-minute intervals are fine.

---

## Updating the deployed app

```powershell
# edit code locally
git add .
git commit -m "describe the change"
git push
```

Both Render and Vercel watch the `main` branch and auto-redeploy on push. Vercel finishes in ~60 s, Render in ~2-3 min.

---

## Memory troubleshooting

If Render free tier OOMs (you'll see the container restart in a loop with "out of memory" in the logs), pick one:

### Option A — Upgrade Render (most reliable, $7/mo)
Render Starter plan: 512 MB → can be set higher, never spins down, persistent disk available. Worth it if you're showing this seriously.

### Option B — Cut ChromaDB
ChromaDB pulls `onnxruntime` (~200 MB resident). If you don't need the Papers / Chat features for the demo, you can remove the eager import. Drop these lines from `backend/requirements.txt`:
```
chromadb==0.5.18
```
And stub `backend/app/services/chroma.py` to no-op (return empty list from `query`, ignore writes). Compound analysis is unaffected.

### Option C — Switch backend host
See [Bullet-proof alternative](#bullet-proof-alternative-flyio-needs-a-credit-card) below.

---

## Bullet-proof alternative: Fly.io (needs a credit card)

Fly.io is more permissive on memory + has free persistent volumes, but they require a credit card on file even though small workloads stay free. If that's OK:

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. From the repo root:
   ```powershell
   fly auth signup
   fly launch --dockerfile backend/Dockerfile --name ai-toxicology-analyst
   ```
3. When prompted:
   - Region: closest to you
   - Postgres / Redis: **No** (we use Supabase)
   - Deploy now: **Yes**
4. Set secrets:
   ```powershell
   fly secrets set OPENAI_API_KEY=sk-... `
                   SUPABASE_URL=https://....supabase.co `
                   SUPABASE_SERVICE_KEY=eyJ... `
                   BACKEND_CORS_ORIGINS=https://your-vercel.vercel.app
   ```
5. Attach a persistent volume so Chroma + uploads survive restarts:
   ```powershell
   fly volumes create tox_data --region <same-region> --size 1
   ```
   Then edit `fly.toml` to mount it at `/data`, and set `CHROMA_PERSIST_DIR=/data/chroma`, `UPLOAD_DIR=/data/uploads`.

Backend URL: `https://ai-toxicology-analyst.fly.dev`. Frontend deploy on Vercel is identical to Step 3.

---

## Costs at this point

Assuming a typical demo cadence (5–10 analyses per visitor, occasional PDF upload):

| Item | Cost |
|---|---|
| Vercel | $0 |
| Render free | $0 |
| Supabase free | $0 |
| OpenAI (gpt-4.1-mini + embeddings) | ~$0.001 per compound analysis, ~$0.002 per PDF page embedded |
| **Total monthly for a demo seeing 100 visitors** | **< $1** |

Switch to `LLM_PROVIDER=groq` (Groq free tier) and that drops to **$0**.

---

## Tear-down

To stop everything:

- Render: dashboard → service → **Settings** → **Suspend** or **Delete**
- Vercel: dashboard → project → **Settings** → **Delete Project**
- Supabase: dashboard → **Settings** → **Pause project** (preserves data) or **Delete**
