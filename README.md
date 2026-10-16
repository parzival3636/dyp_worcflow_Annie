# Pilot — AI Group-Project Coordinator (Telegram Bot)

Pilot is a Telegram bot that coordinates group projects. It tracks task status via DMs and group-chat listening, interprets natural language updates, and keeps the team in sync.

## Quick Start

### Prerequisites
- Python 3.11+
- A Supabase project (free tier works)
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- An OpenAI-compatible LLM endpoint

### 1. Create the Supabase tables

Open the Supabase SQL Editor and run [`backend/schema.sql`](backend/schema.sql).

### 2. Configure BotFather

1. Go to [@BotFather](https://t.me/BotFather) → `/mybots` → select your bot.
2. **Disable privacy mode:** `/setprivacy` → select bot → **Disable**.  
   *(This lets the bot read group messages. After changing this, remove and re-add the bot to any existing group.)*
3. Set commands:
   ```
   /setcommands
   start - Start or join a project
   help - Show all commands
   newproject - Create a new project
   plan - Generate task plan
   kickoff - Start the project
   mytasks - Your current tasks
   status - Project overview
   ask - Ask about the project
   report - Get a project report
   followup - Force a check-in now
   linkgroup - Link a Telegram group
   ```

### 3. Set up environment

```bash
cd backend
cp .env.example .env
# Edit .env with your actual values:
#   TELEGRAM_BOT_TOKEN, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, DATABASE_URL
```

### 4. Install and run

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The bot starts long polling automatically. No public URL or webhook needed.

### 5. Seed demo data (optional)

```bash
python seed_demo.py
```

Creates a demo project "PayFlow" with 4 members and 4 tasks (including Kabir's "Connect the payment API").  
⚠️ Update the `telegram_id` fields in the member rows to match real Telegram user IDs.

---

## Demo Flow (DEMO_MODE)

Set `DEMO_MODE=true` in `.env` for accelerated timings (check-ins every 2 min, no cooldown/quiet hours).

1. `/newproject <idea>` → get a project code + invite link  
2. Second account joins via invite link → onboards with GitHub username  
3. `/plan` → `/kickoff` → everyone gets their tasks  
4. `/followup` → immediate check-in with buttons  
5. Reply with free text (e.g. *"The API is connected, but I am waiting for test credentials."*)  
6. Task updates to **blocked** (not complete)  
7. Reply *"got the credentials, testing is done"* → task becomes **claimed_done**  
8. In the group chat, normal conversation is analyzed; status updates extracted automatically  

Full loop visible in under 15 minutes.

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Returns `{telegram, llm, db}` each `"ok"` or `"error: <reason>"` |
| `/api/projects/{code}/followup` | POST | Trigger an immediate check-in cycle |
| `/api/projects/{code}/inject_reply` | POST | Run `{member_id, text}` through the reply handler (for judges) |

---

## Architecture

```
main.py          — FastAPI app; lifespan starts bot + scheduler
config.py        — pydantic-settings, loads .env once
db.py            — engine, session helper
models.py        — SQLModel tables
schema.sql       — Supabase SQL (source of truth)
llm.py           — call_json() + logging, retries, safe defaults
prompts.py       — P3/P3G/P-checkin prompts + Pydantic output models
bot.py           — Telegram handlers (DM + group + callbacks)
ingest.py        — Group message filter, debounce buffer, window builder
loop.py          — transition(), check-in selection, reply handling
stubs.py         — Placeholder functions for teammate modules
seed_demo.py     — Demo project seeder
```

### State Machine

```
todo → in_progress → blocked ↔ in_progress
                   → claimed_done → verified_done (verifier only)
                                  → needs_review (verifier only)
```

**Hard rules:**
- Chat (DM or group) can never produce `verified_done` or `needs_review`
- A blocker outranks a completion claim in the same message
- Only the task owner's own messages change that task's status
- Confidence < 0.6 → no status change

---

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

- `test_state_machine.py` — All allowed/disallowed transitions + event recording
- `test_reply_interpretation.py` — 12 mandatory intent classification cases
- `test_group_extraction.py` — Group conversation with banter, contradictions, nicknames

---

## Group Chat Setup

1. Set `/setprivacy` → **Disable** in BotFather
2. Remove and re-add the bot to the group  
3. Each member must also `/start` the bot in a private chat  
4. In the group, run `/linkgroup <project_code>`  
5. The bot reads normal conversation and extracts work updates silently

---

## Environment Variables

See [`.env.example`](backend/.env.example) for all configuration options.

Key settings:
- `DEMO_MODE=true` — Accelerated timings for demo
- `VERIFY_MODE=soft|strict` — How verification stubs behave
- `CHECKIN_HOURS=4` — Hours between check-ins (2 min in demo mode)
- `GROUP_DEBOUNCE_SECONDS=12` — Quiet time before processing a group message batch
