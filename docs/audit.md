# Pilot Codebase Audit
*Generated: 2026-10-17 — Step 0 of the full product migration*

## Legend
- **EXISTS** — implementation is present and correct for the new spec
- **PARTIAL** — code exists but needs non-trivial changes to meet spec  
- **MISSING** — capability does not exist; must be built

---

## 1. Database Layer

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| Supabase Postgres connection | **EXISTS** | `backend/db.py` `get_engine()` | psycopg v3, DATABASE_URL |
| SQLite path still in code | **PARTIAL** | `backend/db.py` L23-27 | SQLite branch must be removed; `pilot.db` exists |
| Alembic migrations | **MISSING** | — | Only `schema.sql` + `create_all()` |
| Versioned SQL in /supabase/migrations | **MISSING** | — | |
| `scripts/migrate_sqlite_to_postgres.py` | **MISSING** | — | |
| JSONB fields | **EXISTS** | `backend/models.py` `JSONB_COMPAT` | sqlite variant still present |
| Unique indexes (all required) | **PARTIAL** | `backend/schema.sql` | Missing: `project.telegram_chat_id`, `invite.token`, `(project_id, telegram_message_id)` |
| RLS enabled with no public policies | **PARTIAL** | `backend/schema.sql` L102-126 | RLS ON but `allow_all` policy immediately negates it |
| `sslmode=require` in DATABASE_URL | **EXISTS** | `backend/.env` L6 | |
| `pool_pre_ping=True` | **EXISTS** | `backend/db.py` L32 | |
| docker-compose.yml for local dev | **MISSING** | — | |
| Missing tables: `user`, `invite` | **MISSING** | — | |
| Missing columns on `project` | **MISSING** | — | `leader_user_id`, `description`, `functional_requirements`, `non_functional_requirements`, `constraints`, `telegram_chat_id` (rename), `telegram_status`, `provisioning`, `plan_status` |
| Missing columns on `member` | **MISSING** | — | `user_id`, `github_invite_status` |
| Missing columns on `verification` | **MISSING** | — | `claimed_by_member_id`, `claim_message_id` |
| Missing columns on `message` | **MISSING** | — | `intent`, rename `tg_message_id` |

## 2. Auth & Roles

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| Three roles: leader/guide/member | **MISSING** | — | Only `lead`/`member` on member table; no user table |
| Leader signup at /signup | **MISSING** | — | |
| Email+password auth (bcrypt) | **MISSING** | — | |
| HttpOnly signed session cookie | **MISSING** | — | |
| GET /api/auth/me | **MISSING** | — | |
| POST /api/auth/logout | **MISSING** | — | |
| `get_current_user` FastAPI dependency | **MISSING** | — | |
| `require_role(...)` dependency | **MISSING** | — | |
| CORS with credentials=True + specific origin | **PARTIAL** | `backend/main.py` L138-144 | `allow_origins=["*"]` — must change |
| Login rate limiting | **MISSING** | — | |
| Permission matrix on all endpoints | **MISSING** | — | All routes unauthenticated |

## 3. Invites & Email

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| `invite` table | **MISSING** | — | |
| `secrets.token_urlsafe(32)` | **MISSING** | — | |
| SMTP email sending | **MISSING** | — | |
| POST /api/projects/{id}/invites | **MISSING** | — | |
| GET /api/invites/{token} | **MISSING** | — | |
| POST /api/invites/{token}/accept | **MISSING** | — | |
| POST /api/invites/{id}/resend | **MISSING** | — | |
| DELETE /api/invites/{id} | **MISSING** | — | |
| /invite/:token accept page | **MISSING** | — | |
| GitHub username validation (real API) | **PARTIAL** | `backend/stubs.py` | Stub returns True; real implementation in `annie/services/github_service.py` |
| GitHub collaborator invite | **PARTIAL** | `backend/stubs.py` → `annie/services/github_service.py` | Stub; real code exists in GitHubService |
| Dev SMTP debug server script | **MISSING** | — | |

## 4. Project Creation & Provisioning

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| POST /api/projects (REST, leader) | **PARTIAL** | `backend/bot.py` `cmd_newproject()` | Only via Telegram DM, no REST, no auth |
| Rich project fields (desc, FR, NFR, constraints) | **MISSING** | — | `project` has only `code`, `name`, `idea` |
| project_code 6-char slug | **EXISTS** | `backend/bot.py` `_gen_code()` | |
| Provisioning steps as jsonb | **MISSING** | — | No `provisioning` column |
| `create_repo` step (real GitHub) | **PARTIAL** | `backend/stubs.py` → `annie/services/github_service.py` | Stub is fake; real impl exists |
| README + CONTRIBUTING (commit rule) | **MISSING** | — | |
| `send_invites` provisioning step | **MISSING** | — | |
| Telegram manual step | **MISSING** | — | |
| Live provisioning checklist UI | **MISSING** | — | |
| Retry per step | **MISSING** | — | |

## 5. Telegram Bot (Group-based)

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| Bot token / long polling startup | **EXISTS** | `backend/bot.py` `start_bot()` | python-telegram-bot v20+, async |
| `@safe` decorator | **EXISTS** | `backend/bot.py` `safe()` | |
| `/link <project_code>` in group | **PARTIAL** | `backend/bot.py` `cmd_linkgroup()` | Named `/linkgroup`; no leader identity check; no `telegram_status` update |
| Leader identity validation for /link | **MISSING** | — | |
| `telegram_status` field | **MISSING** | — | Column missing on project |
| Handle group->supergroup migration | **EXISTS** | `backend/bot.py` `migrate_handler()` | |
| Handle bot removed (my_chat_member) | **MISSING** | — | No handler registered |
| Setup card with instructions in UI | **MISSING** | — | |
| Check connection button | **MISSING** | — | |
| Bot self-diagnostic (privacy mode) | **MISSING** | — | |
| Member identity by telegram_id | **EXISTS** | `backend/ingest.py` L127-134 | |
| Member identity by telegram_username (case-insensitive) | **MISSING** | — | Only telegram_id match |
| /iam <email> command | **MISSING** | — | |
| Hint-once to unmatched sender | **MISSING** | — | |
| Telegram match status in UI | **MISSING** | — | |
| Store every group message in DB | **EXISTS** | `backend/ingest.py` L160-179 | |
| ON CONFLICT DO NOTHING (atomic) | **PARTIAL** | `backend/ingest.py` L161-167 | SELECT-then-INSERT, not atomic |
| Read-only group chat panel in UI | **MISSING** | — | |
| Kickoff posts to group (not DM) | **PARTIAL** | `backend/bot.py` `cmd_kickoff()` | Sends DMs, not group |
| Check-ins posted to group | **MISSING** | — | `checkin_tick` sends DMs |
| `allowed_updates` includes my_chat_member | **MISSING** | — | |

## 6. Message Ingestion & Conversation Loop

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| Cheap filter | **EXISTS** | `backend/ingest.py` `_cheap_filter()` | |
| Debounce buffer + flush | **EXISTS** | `backend/ingest.py` | |
| P3G group extraction LLM call | **EXISTS** | `backend/ingest.py` L390-395 | |
| apply_observations() | **EXISTS** | `backend/loop.py` `apply_observations()` | |
| Task resolution via reply_to_message_id | **MISSING** | — | Not used; spec says this is primary |
| Task resolution via LLM | **PARTIAL** | `backend/ingest.py` | P3G takes task list; no explicit fallback chain |
| Status state machine with row lock | **PARTIAL** | `backend/state.py` `transition_task()` | WITH FOR UPDATE exists in state.py; loop.py uses different function |
| off_topic -> no reply | **MISSING** | — | No explicit off_topic intent |
| Partial completion -> in_progress + question | **MISSING** | — | P3G extracts progress kind; no follow-up question sent |
| Done-but-waiting -> blocked, no verify | **PARTIAL** | `backend/loop.py` L794-828 | Blocker handling exists; pattern combo not explicit |
| 60s debounce for verification | **MISSING** | — | |
| Idempotent per claim_message_id | **MISSING** | — | Column missing |
| Bot replies in-thread (reply_to) | **MISSING** | — | send_message without reply_to_message_id |
| Telegram rate limit queue (20/min) | **MISSING** | — | |
| Edited messages re-interpretation | **EXISTS** | `backend/ingest.py` `handle_group_edit()` | |
| Ignore other bots | **MISSING** | — | Only own bot ID checked |

## 7. GitHub Verification Pipeline

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| verify.py background task | **MISSING** | — | Only `stubs.verify_task()` (returns no_evidence) |
| On-demand GitHub commit fetch | **MISSING** | — | |
| Fetch across all branches + open PRs | **MISSING** | — | |
| Author match by login then email | **MISSING** | — | |
| Upsert into commit_log | **MISSING** | — | Table exists; nothing writes to it |
| Deterministic pre-check (zero commits) | **MISSING** | — | |
| Candidate commit selection [T-4] first | **MISSING** | — | |
| LLM verification (P4Verdict / Pydantic) | **PARTIAL** | `backend/llm.py` `P4Verdict` | Schema exists; `annie/services/gemini_service.py` has impl; not wired |
| VERIFY_CONFIDENCE_MIN threshold | **MISSING** | — | `COMPLETION_THRESHOLD=85` for Annie; different pipeline |
| Transaction + row lock on verify | **PARTIAL** | `backend/state.py` `transition_task()` | WITH FOR UPDATE exists; not called by stub |
| verified_done only from verifier/lead_override | **EXISTS** | `backend/loop.py`, `backend/state.py` | |
| Store verification row | **PARTIAL** | `backend/models.py` `Verification` | Table exists; missing claimed_by_member_id, claim_message_id |
| Write verification events | **MISSING** | — | |
| Telegram in-thread reply with verdict | **MISSING** | — | |
| Re-verify on new [T-key] commit | **MISSING** | — | |
| Guide Re-verify + Override in UI | **MISSING** | — | |
| GitHub rate limit -> keep claimed_done, retry 3x | **MISSING** | — | |
| 45s GitHub commit poller | **MISSING** | — | GITHUB_POLL_SECONDS not in config |

## 8. AI Plan / Equal Assignment

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| LLM plan generation (12-20 tasks, P2Plan) | **EXISTS** | `backend/planner.py` `generate_plan()` | |
| Task fields (all except FR/NFR tag) | **PARTIAL** | `backend/llm.py` `P2Task` | Missing `tag` field |
| POST /api/projects/{id}/plan/generate | **PARTIAL** | `backend/routes.py` `trigger_plan()` | No auth; uses `idea` not FR/NFR fields |
| Regeneration protects started tasks | **MISSING** | — | Deletes ALL tasks unconditionally |
| Bundling (union-find) | **EXISTS** | `backend/planner.py` `bundle()` | |
| Milestones excluded from blocks | **EXISTS** | `backend/planner.py` `bundle()` | |
| Equal assignment greedy | **EXISTS** | `backend/planner.py` `assign()` | |
| Oversize flag (>1.4x) | **EXISTS** | `backend/planner.py` `assign()` | |
| Auto-assign after generation if members accepted | **MISSING** | — | |
| POST /api/projects/{id}/plan/rebalance | **PARTIAL** | `backend/routes.py` `confirm_assignment()` | No role check; doesn't skip started tasks |
| Frontend Plan page | **EXISTS** | `frontend/src/pages/Plan.jsx` | Uses mock data |
| Kickoff requires telegram_status=connected | **MISSING** | — | |
| Kickoff posts to group | **MISSING** | — | Only sets DB status |

## 9. Guide Drag & Drop

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| Drag handles shown only for guide role | **MISSING** | — | |
| PATCH /api/tasks/{id}/assign (guide only) | **MISSING** | — | patch_task() has no auth |
| PATCH /api/blocks/{id}/assign (guide only) | **MISSING** | — | No endpoint |
| Hard-dep cut dialog | **MISSING** | — | |
| Cut dep -> kind=handoff + event | **PARTIAL** | `backend/planner.py` `apply_split()` | Via different mechanism |
| Optimistic UI + rollback | **MISSING** | — | |
| Bot announces reassignment in group | **MISSING** | — | |

## 10. Frontend — Static vs Dynamic

| Capability | Status | File / Symbol | Notes |
|---|---|---|---|
| TanStack Query with polling | **MISSING** | — | Raw setInterval + fetch; no @tanstack/react-query |
| API client with credentials: "include" | **MISSING** | — | fetch() without credentials |
| Route guards | **MISSING** | — | |
| Demo/mock data removed from default path | **MISSING** | — | getDemoSnapshot() is fallback on every API error |
| /login, /signup routes | **MISSING** | — | |
| /app (my projects list) | **MISSING** | — | |
| /app/projects/new | **MISSING** | — | |
| /invite/:token page | **MISSING** | — | |
| Loading skeletons | **MISSING** | — | |
| Team page (invites, GitHub, Telegram status) | **MISSING** | — | |
| Group chat panel | **MISSING** | — | |
| Supabase JS client removed | **MISSING** | — | `frontend/src/lib/supabase.js` has hardcoded anon key |

## 11. ENV / Config

| Capability | Status | Notes |
|---|---|---|
| SECRET_KEY | **MISSING** | Not in config |
| FRONTEND_URL | **PARTIAL** | Hardcoded in config.py |
| SMTP_* vars | **MISSING** | |
| BOT_USERNAME | **MISSING** | |
| GITHUB_OWNER | **MISSING** | Only GITHUB_USERNAME |
| GITHUB_POLL_SECONDS | **MISSING** | |
| VERIFY_CONFIDENCE_MIN | **MISSING** | Has COMPLETION_THRESHOLD=85 (different) |
| DATABASE_URL_TEST | **MISSING** | |

## 12. Tests

| Capability | Status | File | Notes |
|---|---|---|---|
| State machine unit tests | **EXISTS** | `backend/tests/test_state_machine.py` | |
| Group extraction unit tests | **EXISTS** | `backend/tests/test_group_extraction.py` | |
| Reply interpretation tests | **EXISTS** | `backend/tests/test_reply_interpretation.py` | |
| Tests against docker Postgres | **MISSING** | — | |
| Verification tests (mocked GitHub + LLM) | **MISSING** | — | |
| Auth / permission tests | **MISSING** | — | |
| Invite lifecycle tests | **MISSING** | — | |
| Bot handler unit tests | **MISSING** | — | |
| Bundling / assignment tests | **MISSING** | — | |

---

## Summary

| Category | EXISTS | PARTIAL | MISSING |
|---|---|---|---|
| Database Layer | 5 | 4 | 7 |
| Auth & Roles | 0 | 1 | 10 |
| Invites & Email | 0 | 2 | 9 |
| Project Provisioning | 1 | 3 | 9 |
| Telegram Bot | 4 | 4 | 12 |
| Conversation Loop | 4 | 3 | 7 |
| GitHub Verification | 1 | 3 | 13 |
| AI Plan/Assignment | 5 | 4 | 4 |
| Guide Drag & Drop | 0 | 1 | 5 |
| Frontend | 0 | 1 | 11 |
| Tests | 3 | 0 | 5 |

## Key Reuse Decisions

| Module | Decision |
|---|---|
| `backend/state.py` `transition_task()` | **KEEP** — has `WITH FOR UPDATE`, correct `verified_done` guard |
| `backend/loop.py` `apply_observations()` | **KEEP** — migrate DM sends to group in-thread reply |
| `backend/ingest.py` | **KEEP** — debounce, cheap filter, P3G. Fix: add reply_to resolution first |
| `backend/planner.py` | **KEEP** — `generate_plan()`, `bundle()`, `assign()` all solid. Add NFR tag, protect started tasks |
| `backend/llm.py` `call_json()`, `P4Verdict` | **KEEP** — reuse for verification |
| `backend/annie/services/github_service.py` | **KEEP** — `create_repo()`, `invite_collaborator()` are real. Wire into provisioning |
| `backend/annie/workers/webhook_worker.py` | **REPLACE** — uses Supabase JS client directly; replace with new `verify.py` |
| `frontend/src/lib/supabase.js` | **DELETE** — violates spec |
| `frontend/src/mock/snapshot.ts` | **MOVE** to `scripts/dev_seed.py` |
| `frontend/src/hooks/useSnapshot.js` | **REFACTOR** — replace interval with TanStack Query, add credentials |

