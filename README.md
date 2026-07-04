# LifeOS v2

LifeOS v2 is an AI-powered personal operations agent that monitors email, classifies intent, executes automations, and provides human-in-the-loop control through Telegram. It is designed as a practical applied-AI system that combines orchestration, external API integrations, and an observable dashboard.

## Why This Project Matters

This project demonstrates production-relevant skills expected in strong software engineering and applied AI roles:

- Multi-agent orchestration across independent services (Gmail, Calendar, Notion, Telegram, weather).
- Human-in-the-loop automation with confirmation workflows for sensitive actions.
- Real-time API backend and dashboard for monitoring actions, stats, and system health.
- Secure configuration boundaries with environment-based credentials.
- Modular architecture with clear separation of agents, API layer, and data layer.

## Core Capabilities

- Monitors incoming mail and extracts actionable intents.
- Classifies email types (meeting, task, invoice, follow-up, generic).
- Schedules meetings on Google Calendar and checks slot conflicts.
- Creates and updates Notion records for meeting notes, tasks, and finance entries.
- Sends interactive Telegram prompts (yes/no and slot picker) for user approval.
- Generates AI-assisted meeting prep notes and reply drafts.
- Serves a FastAPI dashboard with history, stats, weather, and health endpoints.

## System Architecture

1. `monitor.py` polls email and routes each event to the right agent workflow.
2. `agents/classifier_agent.py` determines intent and action payloads.
3. Domain agents (`gmail`, `calendar`, `notion`, `telegram`, `weather`) execute specific actions.
4. `data/store.py` persists operation history and counters.
5. `api/server.py` exposes dashboard APIs and serves the frontend.

## Tech Stack

- Python 3.13+
- FastAPI + Uvicorn
- Google APIs (Gmail + Calendar)
- Notion API
- Telegram Bot API
- TinyDB

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Create `.env`

Add the following values in a new `.env` file in the project root:

```env
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_ACCESS_TOKEN=
GOOGLE_REFRESH_TOKEN=
TIMEZONE=Asia/Kolkata

NOTION_TOKEN=
NOTION_BRIEFING_PARENT_PAGE_ID=
NOTION_TASKS_DATABASE_ID=
NOTION_FINANCE_DATABASE_ID=
NOTION_MEETINGS_PARENT_PAGE_ID=

YOUR_EMAIL=
YOUR_NAME=
CITY=Chennai
TEMP_UNIT=celsius

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

EMAIL_POLL_INTERVAL=30
EMAIL_HISTORY_DAYS=7
PORT=8000
SECRET_KEY=change_this_to_a_strong_secret
```

### 3) Run the monitor

```bash
python monitor.py
```

### 4) Run the dashboard

```bash
python run.py
```

Open `http://localhost:8000`.

## API Endpoints

- `GET /api/health` -> service liveness
- `GET /api/history` -> recent operation history
- `GET /api/stats` -> aggregate counters
- `GET /api/weather` -> weather card data

## Validation and Quality Checks

Use these commands before pushing changes:

```bash
python -m compileall .
python run.py
python monitor.py
```

## Repository Layout

```text
lifeos_v2/
|-- monitor.py
|-- run.py
|-- config.py
|-- requirements.txt
|-- README.md
|-- agents/
|-- api/
|-- data/
`-- frontend/
```

## Security Notes

- Never commit `.env` or tokens.
- Rotate credentials immediately if exposed.
- Use least-privilege API scopes for Google and Notion integrations.

## What Recruiters and Interviewers Can Evaluate Here

- Ability to design reliable AI-assisted automation workflows.
- Skill in integrating multiple third-party APIs into one cohesive system.
- Practical backend engineering with clear modular boundaries.
- Focus on user trust via approval loops and observability.
- End-to-end ownership from idea to executable product.

## Future Improvements

- Add unit/integration tests and CI checks.
- Add retry queues and idempotency keys for external API operations.
- Add structured logging and distributed tracing.
- Add OAuth re-auth flow and token refresh monitoring.
