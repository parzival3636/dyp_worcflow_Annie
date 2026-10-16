# Decisions Log

This document records architectural and technical decisions that differ from or clarify the team PRD v1.0.

| # | Decision | Reason |
|---|---|---|
| D-1 | Database is **PostgreSQL on Supabase**, not SQLite | Chosen by C; shared hosted DB for all four builders |
| D-2 | Connect via **session pooler, port 5432**, driver `postgresql+psycopg://` | Row locks and sessions need session mode. Never use port 6543 |
| D-3 | JSON fields use **JSONB**; all timestamps are **TIMESTAMPTZ (UTC)** | Consistent deadline and quiet-hour math |
| D-4 | `transition_task()` locks the row with `SELECT ... FOR UPDATE` | PRD's "single writer" assumption no longer holds |
| D-5 | Sessions are **sync**; async callers use `asyncio.to_thread()` | Avoid async SQLAlchemy risk in 24 hours |
| D-6 | Task keys are written `T-1..T-n` everywhere | PRD has a typo ("T1..T-n") |
| D-7 | Endpoints use hyphens: `confirm-assignment`, `override-verify` | PDF lost the hyphens; tell D |
| D-8 | `effort_hours = effort / total_effort * project_window_hours` | PRD F13 uses effort_hours without defining it |
| D-9 | Only **C** runs `reset_db.py` and `seed_demo.py`, and announces it first | One shared database |
| D-10 | Dependency direction: in `deps[].from` and `deps[].to`, `from` depends on `to` | Follows PRD example `{"from": "T-3", "to": "T-1"}` |
