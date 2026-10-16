-- Annie: GitHub Task Verification System
-- Run this in your Supabase SQL Editor to set up all tables.

-- ─── Repos ───────────────────────────────────────────────────
create table if not exists repos (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  full_name   text not null unique,
  url         text not null,
  owner       text not null,
  collaborators text[] default '{}',
  created_at  timestamptz default now()
);

-- ─── Tasks ───────────────────────────────────────────────────
create table if not exists tasks (
  id               uuid primary key default gen_random_uuid(),
  title            text not null,
  description      text not null,
  keywords         text[] default '{}',
  repo_name        text not null,
  assigned_to      text[] default '{}',
  status           text not null default 'pending'
                   check (status in ('pending', 'in_progress', 'complete')),
  confidence_score float,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);

-- ─── Webhook Events (Queue) ───────────────────────────────────
create table if not exists webhook_events (
  id             uuid primary key default gen_random_uuid(),
  repo_name      text not null,
  commit_sha     text not null,
  commit_message text,
  author         text,
  diff_url       text,
  raw_payload    jsonb,
  status         text not null default 'pending'
                 check (status in ('pending', 'processing', 'processed', 'failed')),
  created_at     timestamptz default now()
);

-- ─── Verifications ───────────────────────────────────────────
create table if not exists verifications (
  id                uuid primary key default gen_random_uuid(),
  task_id           uuid references tasks(id) on delete cascade,
  event_id          uuid references webhook_events(id) on delete cascade,
  commit_sha        text not null,
  confidence_score  float not null,
  reasoning         text,
  matched_keywords  text[] default '{}',
  status_updated_to text,
  processed_at      timestamptz default now()
);

-- ─── Indexes ─────────────────────────────────────────────────
create index if not exists idx_webhook_events_status on webhook_events(status);
create index if not exists idx_tasks_repo on tasks(repo_name);
create index if not exists idx_tasks_status on tasks(status);
create index if not exists idx_verifications_task on verifications(task_id);

-- ─── Enable Realtime (for the frontend live updates) ─────────
alter publication supabase_realtime add table webhook_events;
alter publication supabase_realtime add table tasks;
