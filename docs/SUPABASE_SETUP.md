# Supabase free-tier setup

Without Supabase the backend still works — it just keeps reports in memory and
loses them on container restart. Wiring Supabase takes about 5 minutes and is
free for our scale.

## 1. Create the project

1. Go to **https://supabase.com** → **Start your project** → sign up (GitHub
   is fastest).
2. Click **New project**.
3. Fill in:
   - **Name**: `ai-toxicology-analyst` (anything works)
   - **Database password**: generate a strong one and save it to your password
     manager (you'll rarely use it again, but you can't recover it later).
   - **Region**: pick the one closest to where your backend will run (e.g.
     `eu-central-1` if your Railway/Render service is in Frankfurt).
   - **Plan**: **Free** (500 MB DB, 2 GB bandwidth — plenty for this app).
4. Click **Create new project**. Wait ~1 minute while it provisions.

## 2. Run the schema

1. In the left sidebar, click the **SQL Editor** icon (looks like a database).
2. Click **New query**.
3. Open [`backend/app/db/schema.sql`](../backend/app/db/schema.sql) in your editor,
   copy its full contents, paste them into the Supabase SQL editor.
4. Click **Run** (or `Ctrl+Enter` / `Cmd+Enter`).
5. You should see "Success. No rows returned." Three tables are now created:
   `papers`, `analyses`, `reports`.

To verify, click **Table Editor** in the sidebar — you should see those three
tables listed.

## 3. Copy the credentials

You need two values for the backend:

1. Sidebar → **Project Settings** (gear icon, bottom-left) → **API**.
2. Copy:
   - **Project URL** (looks like `https://abcdefghij.supabase.co`) → this is
     `SUPABASE_URL`.
   - Under **Project API keys**, copy the **`service_role`** key (NOT `anon`).
     This is `SUPABASE_SERVICE_KEY`.

> ⚠️ The `service_role` key bypasses Row-Level Security. **Never commit it,
> never put it in `NEXT_PUBLIC_*`, never ship it to the browser.** It only
> belongs in backend environment variables.

## 4. Wire it into the backend

### Local Docker

Open the project's `.env` file in the repo root and fill in:

```bash
SUPABASE_URL=https://abcdefghij.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOi...     # the service_role key, NOT anon
```

Then restart the backend:

```powershell
docker compose down
docker compose up --build -d
```

Check the logs — you should see `supabase.connected` instead of
`supabase.using_memory_store`:

```powershell
docker compose logs --tail 30 backend | findstr supabase
```

### Railway / Render (production)

Open your service's **Variables** tab and add both:

| Key | Value |
|---|---|
| `SUPABASE_URL` | your Project URL |
| `SUPABASE_SERVICE_KEY` | the `service_role` key |

Redeploy. The backend auto-detects the credentials on next boot.

## 5. Verify reports persist

1. Open http://localhost:3000/analyze and run "Caffeine".
2. Open http://localhost:3000/reports — you should see the caffeine report
   in the list with its risk badge.
3. Restart the backend (`docker compose restart backend`).
4. Refresh the Reports page — the report is **still there**. (Without Supabase,
   it would have disappeared.)
5. As a final check, in the Supabase dashboard go to **Table Editor → reports** —
   you'll see the row with its JSON payload.

## What the tables hold

| Table | Purpose |
|---|---|
| `papers` | One row per uploaded PDF: id, filename, title, page count, chunk count, upload time. Chunk *embeddings* live in ChromaDB, not here. |
| `analyses` | Reserved for compound-level metadata (currently unused — the agent writes straight to `reports`). |
| `reports` | One row per finished analysis. Whole `ToxicityReport` JSON in the `payload` column. |

## Cost ceiling on the free tier

The free tier gives you:

- 500 MB database (one report ≈ 5–10 KB → ~50,000 reports before you'd notice)
- Unlimited API requests
- 2 GB bandwidth / month

This app will not push any of those limits unless you start hammering it.

## Adding auth + multi-tenant later

When you're ready to make this a real product:

1. Enable Supabase Auth in the dashboard.
2. Add a `user_id uuid references auth.users(id)` column to each table.
3. Enable RLS on each table and add a policy:
   ```sql
   alter table reports enable row level security;
   create policy "users see their own reports"
       on reports for select
       using (user_id = auth.uid());
   ```
4. Replace the backend's `SUPABASE_SERVICE_KEY` with the `anon` key + a
   per-request user JWT, so RLS engages.
5. Add a Supabase auth flow on the frontend (`@supabase/ssr` package, ~50
   lines in middleware + a sign-in page).

This is intentionally out of scope for MVP. The schema is shaped so the
migration is additive, not a rewrite.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `supabase.using_memory_store` in logs after restart | Env vars not loaded. Check `docker compose config` shows them. |
| `supabase.init_failed` with `Invalid API key` | You copied the `anon` key by mistake — go back to **API settings → service_role**. |
| Reports page is empty even after running an analysis | Check backend logs for `report.save_failed`. Most common cause: schema not run; go back to step 2. |
| `supabase` Python errors about httpx/h2 versions | The `supabase` Python SDK pins versions strictly. Stick with the versions in `backend/requirements.txt`; bumping `httpx` independently breaks it. |
| Want to wipe everything | In SQL Editor: `truncate reports, papers, analyses;` |
