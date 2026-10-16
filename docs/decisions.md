# Architecture Decisions

| # | Decision | Reason |
|---|----------|--------|
| 1 | Sync SQLModel sessions run via `asyncio.to_thread` from async handlers | psycopg v3 sync is simpler than async sessions; `to_thread` keeps the event loop unblocked |
| 2 | Bot uses long polling, not webhooks | No public URL needed for hackathon/demo |
| 3 | APScheduler `AsyncIOScheduler` shares the event loop with the bot | Single-process simplicity; no extra worker |
| 4 | Stubs return plausible fake data immediately | Teammates swap bodies without changing signatures |
