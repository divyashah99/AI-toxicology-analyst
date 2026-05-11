-- AI Toxicology Analyst — Supabase / Postgres schema
-- Run once in the Supabase SQL editor or via psql.

create extension if not exists "uuid-ossp";

create table if not exists papers (
    paper_id     uuid primary key,
    filename     text not null,
    title        text,
    pages        int  not null default 0,
    chunk_count  int  not null default 0,
    uploaded_at  timestamptz not null default now()
);

create table if not exists analyses (
    id           uuid primary key default uuid_generate_v4(),
    cid          int,
    name         text,
    smiles       text,
    risk_band    text check (risk_band in ('low','moderate','high')),
    score        numeric(4,3),
    created_at   timestamptz not null default now()
);

create table if not exists reports (
    id           uuid primary key default uuid_generate_v4(),
    analysis_id  uuid references analyses(id) on delete cascade,
    payload      jsonb not null,
    created_at   timestamptz not null default now()
);

create index if not exists papers_uploaded_at_idx on papers (uploaded_at desc);
create index if not exists analyses_created_at_idx on analyses (created_at desc);
create index if not exists reports_created_at_idx on reports (created_at desc);

-- Multi-tenant note: when introducing auth, add `user_id uuid` to each table
-- and a corresponding RLS policy `user_id = auth.uid()`.
