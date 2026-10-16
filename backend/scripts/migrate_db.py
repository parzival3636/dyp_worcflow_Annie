"""
Script to apply required schema additions (tables and columns) safely to Supabase Postgres.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from db import get_engine

DDL = """
-- Create user table if not exists
CREATE TABLE IF NOT EXISTS "user" (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'leader',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create invite table if not exists
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

-- Add columns to project
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

-- Add columns to member
ALTER TABLE member ADD COLUMN IF NOT EXISTS user_id BIGINT;
ALTER TABLE member ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE member ADD COLUMN IF NOT EXISTS github_invite_status TEXT DEFAULT 'none';

-- Add columns to task
ALTER TABLE task ADD COLUMN IF NOT EXISTS tag TEXT;

-- Add columns to verification
ALTER TABLE verification ADD COLUMN IF NOT EXISTS claimed_by_member_id BIGINT;
ALTER TABLE verification ADD COLUMN IF NOT EXISTS claim_message_id BIGINT;
ALTER TABLE verification ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Add columns to message
ALTER TABLE message ADD COLUMN IF NOT EXISTS intent TEXT;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_project_leader_user_id ON project (leader_user_id);
CREATE INDEX IF NOT EXISTS idx_project_telegram_chat_id ON project (telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_member_user_id ON member (user_id);
CREATE INDEX IF NOT EXISTS idx_member_project_id ON member (project_id);
CREATE INDEX IF NOT EXISTS idx_invite_token ON invite (token);
CREATE INDEX IF NOT EXISTS idx_invite_project_id ON invite (project_id);
"""

def run_migration():
    engine = get_engine()
    with engine.begin() as conn:
        for statement in DDL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
    print("Database migration completed successfully!")

if __name__ == "__main__":
    run_migration()
