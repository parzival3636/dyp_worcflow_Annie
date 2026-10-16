# Pilot — `transcribe/` Module

Meeting Link → Transcript → Proposed Tasks (Pilot).

## Overview
Accepts meeting links (Google Meet, Zoom, Teams), coordinates Fireflies notetaker bot ingestion, normalizes transcripts, extracts commitments and action items using LLMs, and presents them for Telegram verification.

## Setup
```bash
cd transcribe
pip install -r requirements.txt
cp .env.example .env
```

## Running the API
```bash
uvicorn app.main:app --reload --port 8000
```

## Running Tests
```bash
pytest tests/
```
