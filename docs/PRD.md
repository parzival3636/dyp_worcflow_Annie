# Pilot — Product Requirements Document

## Problem Statement (W-PS-1)

College group projects suffer from coordination failures: unclear task ownership, missed deadlines, silent blockers, and he-said-she-said status disputes. Existing tools (Trello, Asana, Notion) require manual updates that students ignore.

## Solution

Pilot is an AI coordinator bot that lives where students already communicate — Telegram. It:

1. **Creates and plans projects** from a text description
2. **Assigns tasks** with deadlines and acceptance criteria
3. **Checks in periodically** via DM, interpreting free-text replies
4. **Reads group chat** to extract status updates from normal conversation
5. **Tracks blockers** and routes them to the right person
6. **Detects contradictions** between what people say about each other's work
7. **Verifies completion** against commit evidence (when available)

## Core Differentiator

The group-chat listener. Students don't need to update a dashboard — they just talk normally, and Pilot extracts actionable status updates.

## Key Example (Must Pass)

- Kabir owns "Connect the payment API", status: todo
- Bot asks Kabir for an update
- Kabir: "The API is connected, but I am waiting for test credentials."
- **Expected:** task → **blocked**, blocker = "test credentials", NOT complete
- Later: "got the credentials, testing is done" → blocker resolved, task → **claimed_done**

## Status Values

`todo` → `in_progress` → `blocked` ↔ `in_progress` → `claimed_done` → `verified_done`

## Architecture

- Telegram Bot (python-telegram-bot v20+, long polling)
- Supabase Postgres (SQLModel + psycopg v3)
- OpenAI-compatible LLM (async httpx)
- APScheduler for periodic check-ins
- FastAPI for health + demo endpoints

## Team Scope

| Person | Scope |
|---|---|
| Person A (this bot) | Telegram bot, group listener, core loop, state machine |
| Person B | GitHub integration, commit tracking |
| Person C | Planner, task generation, bundling |
| Person D | Verification engine |
| Person E | Guide module, frontend dashboard |

Stubs are provided for B/C/D/E modules with exact signatures.
