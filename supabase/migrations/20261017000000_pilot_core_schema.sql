-- Supabase Migration: Pilot Multi-User Platform
-- Tables: user, invite, project, member, block, task, task_dep, message, blocker, contradiction, verification, commit_log, event

CREATE TABLE IF NOT EXISTS "user" (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'leader',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "invite" (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    token TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    invited_by_user_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

ALTER TABLE project ADD COLUMN IF NOT EXISTS leader_user_id BIGINT;
ALTER TABLE project ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE project ADD COLUMN IF NOT EXISTS functional_requirements TEXT;
ALTER TABLE project ADD COLUMN IF NOT EXISTS non_functional_requirements TEXT;
ALTER TABLE project ADD COLUMN IF NOT EXISTS constraints TEXT;
ALTER TABLE project ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT;
ALTER TABLE project ADD COLUMN IF NOT EXISTS telegram_status TEXT DEFAULT 'disconnected';
ALTER TABLE project ADD COLUMN IF NOT EXISTS plan_status TEXT DEFAULT 'draft';
ALTER TABLE project ADD COLUMN IF NOT EXISTS provisioning JSONB DEFAULT '{}'::jsonb;
ALTER TABLE project ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE member ADD COLUMN IF NOT EXISTS user_id BIGINT;
ALTER TABLE member ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE member ADD COLUMN IF NOT EXISTS github_invite_status TEXT DEFAULT 'none';

ALTER TABLE task ADD COLUMN IF NOT EXISTS tag TEXT;

ALTER TABLE verification ADD COLUMN IF NOT EXISTS claimed_by_member_id BIGINT;
ALTER TABLE verification ADD COLUMN IF NOT EXISTS claim_message_id BIGINT;
ALTER TABLE verification ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

ALTER TABLE message ADD COLUMN IF NOT EXISTS intent TEXT;

CREATE INDEX IF NOT EXISTS idx_project_leader_user_id ON project (leader_user_id);
CREATE INDEX IF NOT EXISTS idx_project_telegram_chat_id ON project (telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_member_user_id ON member (user_id);
CREATE INDEX IF NOT EXISTS idx_member_project_id ON member (project_id);
CREATE INDEX IF NOT EXISTS idx_invite_token ON invite (token);
CREATE INDEX IF NOT EXISTS idx_invite_project_id ON invite (project_id);
