# 📱 WhatsApp Group Summary Bot

![release version](https://img.shields.io/github/v/release/chocksmith/minime-wa-llm)
![Build Image](https://github.com/chocksmith/minime-wa-llm/actions/workflows/docker.yml/badge.svg)
![Release](https://github.com/chocksmith/minime-wa-llm/actions/workflows/release.yml/badge.svg)

AI-powered WhatsApp bot that **joins any group, tracks conversations, and generates intelligent summaries**.

> **About this repo:** `minime-wa-llm` is a personal project built on top of [ilanbenb/wa_llm](https://github.com/ilanbenb/wa_llm) (kept as the `upstream` git remote here). It's customized for personal/family use rather than being a general-purpose fork meant for upstream contribution — notably a Portuguese persona, a manual knowledge-base seeding endpoint (`/kb/seed`), an optional web-search tool for the Q&A agent, and support for running alongside other independent bot services (see "Companion services" below) that share the same WhatsApp session.

---

## Features

- 🤖 Automated group chat responses (when mentioned)
- 📝 Smart **LLM-based conversation summaries**
- 📚 Knowledge base integration for context-aware answers
- 📂 Persistent message history with PostgreSQL + `pgvector`
- 🔗 Support for multiple message types (text, media, links)
- 👥 Group management & customizable settings
- 🔕 **Opt-out feature**: Users can opt-out of being tagged in summaries/answers via DM.
- ⚡ REST API with Swagger docs (`localhost:8000/docs`)

---

## 🐳 Docker Compose Configurations

This project includes multiple Docker Compose files for different environments:

| File                           | Purpose                                                                        | Usage                                                  |
| ------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------ |
| `docker-compose.yml`           | **Default/Development**. Builds the application from source code.              | `docker compose up -d`                                 |
| `docker-compose.prod.yml`      | **Production**. Uses pre-built images from GHCR. Recommended for deployment.   | `docker compose -f docker-compose.prod.yml up -d`      |
| `docker-compose.local-run.yml` | **Local Execution**. For running the app on host while services run in Docker. | `docker compose -f docker-compose.local-run.yml up -d` |
| `docker-compose.base.yml`      | **Base Configuration**. Contains shared service definitions.                   | ❌ **Do not use directly**                             |

---

## 📋 Prerequisites

- 🐳 Docker and Docker Compose
- 🐍 Python 3.13+
- 🗄️ PostgreSQL with `pgvector` extension
- 🔑 Voyage AI API key
- 📲 WhatsApp account for the bot

## Quick Start

### 1. Clone & Configure

`git clone https://github.com/chocksmith/minime-wa-llm.git
cd minime-wa-llm`

### 2. Create .env file

- Copy `.env.example` to `.env` and fill in required values.

```
cp .env.example .env
```

#### Environment Variables

<div style="font-size: 10px;">

| Variable                       | Description                                                                        | Default                                                      |
| ------------------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `WHATSAPP_HOST`                | WhatsApp Web API URL                                                               | `http://localhost:3000`                                      |
| `WHATSAPP_BASIC_AUTH_USER`     | WhatsApp API user                                                                  | `admin`                                                      |
| `WHATSAPP_BASIC_AUTH_PASSWORD` | WhatsApp API password                                                              | `admin`                                                      |
| `VOYAGE_API_KEY`               | Voyage AI key                                                                      | –                                                            |
| `DB_URI`                       | PostgreSQL URI                                                                     | `postgresql+asyncpg://user:password@localhost:5432/postgres` |
| `LOG_LEVEL`                    | Log level (`DEBUG`, `INFO`, `ERROR`)                                               | `INFO`                                                       |
| `ANTHROPIC_API_KEY`            | Anthropic API key. You need to have a real anthropic key here, starts with sk-.... | –                                                            |
| `LOGFIRE_TOKEN`                | Logfire monitoring key, You need to have a real logfire key here                   | –                                                            |
| `DM_AUTOREPLY_ENABLED`         | Enable auto-reply for direct messages                                              | `False`                                                      |
| `DM_AUTOREPLY_MESSAGE`         | Message to send as auto-reply                                                      | `Hello, I am not designed to answer to personal messages.`   |

</div>

### 3. Starting the Services

**Option A: Development (Build from source)**

```bash
docker compose up -d
```

**Option B: Production (Use pre-built images)**

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Connect your device

1. Open http://localhost:3000
2. Scan the QR code with your WhatsApp mobile app.
3. Invite the bot device to any target groups you want to summarize.
4. Restart service: `docker compose restart wa_llm-web-server`

### 5. Activating the Bot for a Group

1. open pgAdmin or any other posgreSQL admin tool
2. connect using
   | Parameter | Value |
   | --------- | --------- |
   | Host | localhost |
   | Port | 5432 |
   | Database | postgres |
   | Username | user |
   | Password | password |

3. run the following update statement:

   ```
       UPDATE public."group"
       SET managed = true
       WHERE group_name = 'Your Group Name';
   ```

4. Restart the service: `docker compose restart wa_llm-web-server`

### 6. API usage

Swagger docs available at: `http://localhost:8000/docs`

#### Key Endpoints

- <b>/load_new_kbtopics (POST)</b> Distills recent chat history into knowledge-base topics for all managed groups.
- <b>/summarize_and_send_to_groups (POST)</b> Generates & dispatches daily summaries to all managed groups (and their linked community groups).
- <b>/kb/seed (POST)</b> Seeds a group's knowledge base with hand-written background info that didn't come from chat messages (e.g. the group's purpose, rules, reference facts). Re-seeding the same `subject` for a group overwrites that entry. Example:
  ```bash
  curl -X POST http://localhost:8000/kb/seed \
    -H "Content-Type: application/json" \
    -d '{
      "group_name": "Your Group Name",
      "topics": [
        {"subject": "Purpose", "content": "What this group is about..."}
      ]
    }'
  ```

### 7. Operations — Start / Stop / Status

All commands run from the repo root (where `docker-compose.yml` lives).

```bash
# Start everything (creates volumes/networks as needed; safe to re-run)
docker compose up -d

# Check what's running
docker compose ps

# Stop everything (containers stop, all data/volumes persist)
docker compose stop

# Fully remove containers (still keeps volumes/data — use before recreating)
docker compose down

# Watch logs
docker compose logs -f                 # everything
docker compose logs -f web-server       # one service
docker compose logs -f realestate-bot   # one service

# After an env change (picks up the new env without rebuilding)
docker compose up -d --no-deps <service>

# After a code change (rebuild image first, then recreate)
docker compose build <service> && docker compose up -d --no-deps <service>
```

Service names: `postgres`, `whatsapp`, `web-server`, `realestate-bot`.

All four services run with `restart: always`, so a Docker/host restart brings the whole stack back automatically — no manual intervention needed. `postgres` must be healthy before `whatsapp` will start (it depends on it); if you ever see `whatsapp` crash-looping right after a fresh start, this is almost always just startup ordering catching up, and it self-resolves within seconds.

**Never run** `docker compose down -v` or remove the `wa_llm_whatsapp` volume casually — that discards the paired WhatsApp session and forces re-scanning the QR code for every bot on the stack.

### 8. Opt-Out Feature

Users can control whether they are tagged in bot-generated messages (summaries, answers) by sending Direct Messages (DMs) to the bot:

| Command   | Description                                                                        |
| :-------- | :--------------------------------------------------------------------------------- |
| `opt-out` | Opt-out of being tagged. Your name will be displayed as text instead of a mention. |
| `opt-in`  | Opt-in to being tagged (default).                                                  |
| `status`  | Check your current opt-out status.                                                 |

> **Note:** This only affects messages generated by the bot. It does not prevent other users from tagging you manually.

---

## 🚀 Production Deployment

To deploy in a production environment using the optimized configuration:

1. **Create Production Environment File**:
   Copy `.env.example` to `.env.prod` and configure your production secrets.

   ```bash
   cp .env.example .env.prod
   ```

2. **Start Services**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

This configuration includes:

- Automatic restart policies (`restart: always`)

---

## Developing

### Setup

Install dependencies using `uv`:

```bash
uv sync --all-extras --dev
```

### Development Commands

The project uses **Poe the Poet** for task automation with parallel execution:

```bash
# Run all checks (format, then parallel lint/typecheck/test)
uv run poe check

# Individual tasks
uv run poe format     # Format code with ruff
uv run poe lint       # Lint code with ruff
uv run poe typecheck  # Type check with pyright
uv run poe test       # Run tests with pytest

# List all available tasks
uv run poe
```

The `check` command runs formatting first, then executes linting, type checking, and testing **in parallel** for faster execution.

### Key Files

- Main application: `app/main.py`
- WhatsApp client: `src/whatsapp/client.py`
- Message handler: `src/handler/__init__.py`
- Database models: `src/models/`

---

## Architecture

### Core components

- **`whatsapp`** — [GOWA](https://github.com/aldinokemal/go-whatsapp-web-multidevice) (`go-whatsapp-web-multidevice`), the self-hosted WhatsApp Web REST API. Owns the *one* paired WhatsApp session/phone number for the whole stack. Exposes a REST API on port `3000` (basic auth) and pushes every incoming event as a webhook.
- **`postgres`** — Postgres + `pgvector`, storing groups, messages, and the knowledge-base topic embeddings.
- **`web-server`** — this app. FastAPI backend (`app/main.py`) that receives WhatsApp webhooks, runs the message handler/router, and answers `@mentions` using an LLM agent (via `pydantic-ai`) backed by the Postgres knowledge base.

```
                  ┌────────────────────────┐
                  │   whatsapp (GOWA)      │
                  │   one WhatsApp session │
                  │   port 3000            │
                  └───────────┬────────────┘
                              │ every event is POSTed to
                              │ every URL in WHATSAPP_WEBHOOK
                ┌─────────────┴─────────────┐
                ▼                           ▼
    ┌───────────────────────┐   ┌─────────────────────────────┐
    │  web-server            │   │  (optional) other            │
    │  port 8000              │   │  webhook consumers            │
    │  only acts on groups    │   │  e.g. realestate-bot -         │
    │  it marked managed=true │   │  each ignores groups it        │
    │                         │   │  doesn't own (see below)       │
    └────────────┬────────────┘   └─────────────────────────────┘
                ▼
    ┌───────────────────────┐
    │  postgres              │
    │  pgvector KB           │
    └───────────────────────┘
```

GOWA's `WHATSAPP_WEBHOOK` env var accepts a **comma-separated list of URLs** — it will fan out every event to all of them. This means a single paired phone number can serve `web-server` *and* any number of other independent bot services at once, each deciding for itself which groups/messages are its business, with zero code coupling between them. `web-server`'s side of that decision is the `managed` boolean column on the `group` table (see "Activating the Bot for a Group" above) — any group that isn't `managed` is silently ignored by this app, after storing the message for its own records.

### Knowledge base & agent behavior

- Conversations in `managed` groups get periodically distilled into topics and embedded (`/load_new_kbtopics`), searchable via hybrid vector + keyword search.
- `POST /kb/seed` lets you inject hand-written background knowledge for a group directly (bypassing chat-history extraction) — useful for things like a group's purpose, rules, or reference facts that didn't come from conversation.
- The agent optionally has a live web-search tool (DuckDuckGo, no API key required) for questions the group's own knowledge can't answer.
- Persona/response-style instructions live in `src/templates/persona.j2`, shared by the summarize and Q&A prompts.

### Companion services (optional)

This stack is designed so **other bot personalities can share the same WhatsApp session** without touching this app's code at all — just add another `WHATSAPP_WEBHOOK` URL and let that service filter to its own group(s). One example run alongside this deployment: a `realestate-bot` service (from a separate repository) that answers questions and posts notifications in a dedicated group, backed by its own GitHub-repo-based knowledge store and email-polling pipeline, using Claude directly rather than this app's RAG pipeline. It's wired in via `docker-compose.yml` as an additional service (`build.context` pointing at that other repo's checkout) and requires no changes to this app beyond the extra webhook URL and never marking its group `managed`. If you don't have such a service configured, ignore this section — it has no effect on the rest of the stack.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## License

[LICENCE](CODE_OF_CONDUCT.md)
