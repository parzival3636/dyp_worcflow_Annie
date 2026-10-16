-- Pilot schema – source of truth for Supabase Postgres
-- Run this in the Supabase SQL editor to create all tables.

create table project (
  id bigint generated always as identity primary key,
  code text unique not null, name text not null, idea text,
  repo_full_name text, repo_url text,
  lead_member_id bigint, telegram_group_id bigint,
  status text not null default 'planning',      -- planning | running | done
  starts_at timestamptz, ends_at timestamptz, last_polled_at timestamptz
);

create table member (
  id bigint generated always as identity primary key,
  project_id bigint references project(id) on delete cascade,
  name text, telegram_id bigint, telegram_username text,
  github_login text, skills text,
  aliases jsonb default '[]',                   -- nicknames used in group chat
  role text not null default 'member',          -- lead | member
  invite_status text not null default 'pending',
  onboarding_state text default 'new',          -- new | awaiting_github | done
  active_task_id bigint, awaiting_clarification boolean default false
);

create table block (
  id bigint generated always as identity primary key,
  project_id bigint references project(id) on delete cascade,
  name text, total_effort int, owner_member_id bigint, oversize_flag boolean default false
);

create table task (
  id bigint generated always as identity primary key,
  project_id bigint references project(id) on delete cascade,
  key text not null,                            -- always 'T-<number>'
  title text, description text, acceptance_criteria jsonb default '[]',
  effort int, status text not null default 'todo',
  is_milestone boolean default false, block_id bigint, owner_member_id bigint,
  deadline timestamptz, started_at timestamptz, completed_at timestamptz,
  progress int default 0, risk text default 'ok',
  last_checkin_at timestamptz, checkin_count int default 0,
  unique (project_id, key)
);

create table task_dep (
  task_id bigint references task(id) on delete cascade,
  depends_on_task_id bigint references task(id) on delete cascade,
  kind text not null default 'hard',            -- hard | handoff
  primary key (task_id, depends_on_task_id)
);

create table message (
  id bigint generated always as identity primary key,
  project_id bigint, member_id bigint, task_id bigint,
  direction text not null,                      -- out | in
  text text, parsed_json jsonb, created_at timestamptz default now(),
  source text default 'dm',                     -- dm | group
  chat_id bigint, tg_message_id bigint, reply_to_tg_message_id bigint,
  processed boolean default false,
  unique (chat_id, tg_message_id)
);

create table blocker (
  id bigint generated always as identity primary key,
  task_id bigint references task(id) on delete cascade,
  description text, type text, needed_from text,
  routed_to_member_id bigint,
  status text not null default 'open',          -- open | routed | resolved
  created_at timestamptz default now(), resolved_at timestamptz
);

create table contradiction (
  id bigint generated always as identity primary key,
  project_id bigint, task_ids jsonb, member_ids jsonb, summary text,
  status text not null default 'open',
  created_at timestamptz default now(), resolved_at timestamptz, resolution text
);

create table verification (
  id bigint generated always as identity primary key,
  task_id bigint references task(id) on delete cascade,
  verdict text, confidence real, matched_shas jsonb, criteria_results jsonb, reason text,
  created_at timestamptz default now()
);

create table commit_log (
  sha text primary key, project_id bigint, author_login text, member_id bigint,
  message text, files jsonb, additions int, deletions int,
  committed_at timestamptz, task_id bigint
);

create table event (
  id bigint generated always as identity primary key,
  project_id bigint, ts timestamptz default now(),
  actor_member_id bigint, type text not null, task_id bigint, payload jsonb
);

-- Indexes
create index on message (project_id, created_at);
create index on event (project_id, ts desc);
create index on task (project_id, status);

-- Disable RLS on every table
alter table project       enable row level security; alter table project       force row level security;
alter table member        enable row level security; alter table member        force row level security;
alter table block         enable row level security; alter table block         force row level security;
alter table task          enable row level security; alter table task          force row level security;
alter table task_dep      enable row level security; alter table task_dep      force row level security;
alter table message       enable row level security; alter table message       force row level security;
alter table blocker       enable row level security; alter table blocker       force row level security;
alter table contradiction enable row level security; alter table contradiction force row level security;
alter table verification  enable row level security; alter table verification  force row level security;
alter table commit_log    enable row level security; alter table commit_log    force row level security;
alter table event         enable row level security; alter table event         force row level security;

-- Allow all access (effectively disabling RLS)
do $$
declare
  tbl text;
begin
  for tbl in select unnest(array[
    'project','member','block','task','task_dep','message',
    'blocker','contradiction','verification','commit_log','event'
  ]) loop
    execute format('create policy "allow_all" on %I for all using (true) with check (true)', tbl);
  end loop;
end $$;
