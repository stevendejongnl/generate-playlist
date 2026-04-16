# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Commands

```bash
# Install dependencies
uv sync              # Python
npm install          # Frontend (TypeScript)

# Run locally (port 5000)
uv run uvicorn playlist_generator.main:app --host 0.0.0.0 --port 5000 --reload

# Build frontend
npm run build        # Production bundle → static/js/app.iife.js
npm run dev          # Watch mode

# Tests
uv run pytest        # Python tests (54 tests, async)
npm test             # TypeScript tests (6 tests, vitest)
npm run typecheck    # TypeScript type checking

# Database migrations
uv run alembic upgrade head          # Apply migrations
uv run alembic revision --autogenerate -m "description"  # Create new migration

# Docker
docker-compose up -d                 # Port 5888
```

## Environment

Create `.env` in the project root:

```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:5000/callback
SECRET_KEY=...                          # Session signing key
ENCRYPTION_KEY=...                      # Fernet key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
DATABASE_URL=sqlite+aiosqlite:///./data/playlist_generator.db
OPENAI_API_KEY=...                      # Optional: for AI cover art and smart discovery
```

## Architecture

Multi-user FastAPI app. Spotify OAuth is the account system (no passwords). Data stored in SQLite via async SQLAlchemy.

### Project Structure

```
playlist_generator/
    main.py              — App factory, lifespan, middleware, router mounts
    config.py            — pydantic-settings config from .env
    database.py          — Async SQLAlchemy engine + session factory
    encryption.py        — Fernet encrypt/decrypt for Spotify tokens
    dependencies.py      — FastAPI Depends: get_db, get_current_user, get_spotify
    models/              — SQLAlchemy ORM models (8 tables)
    schemas/             — Pydantic request/response schemas
    services/            — Business logic (no HTTP concerns)
        spotify_auth.py  — OAuth flow, token refresh, client factory
        base_list.py     — Source tracks/playlists CRUD
        blacklist.py     — Blocked tracks/playlists CRUD
        generation.py    — Core: collect → filter → discover → limit → write
        cover_image.py   — PIL image gen + OpenAI DALL-E (optional)
    routers/             — HTTP route handlers
        auth.py          — /login, /callback, /logout
        pages.py         — SSR page routes (Jinja2)
        base_list.py     — CRUD API (HTMX partials)
        blacklist.py     — CRUD API (HTMX partials)
        targets.py       — CRUD API (HTMX partials)
        generation.py    — Preview + execute endpoints
        cover_image.py   — Image preview/upload + config CRUD

frontend/src/            — TypeScript source (Vite build)
    main.ts              — Entry point
    htmx-setup.ts        — HTMX configuration
    flash.ts             — Auto-dismiss alert messages
    confirm.ts           — Confirm dialogs for destructive actions

templates/               — Jinja2 templates
    layouts/base.html    — Dark theme shell with nav
    pages/               — Full page templates (9 pages)
    partials/            — HTMX fragment templates

static/                  — CSS, built JS, fonts
alembic/                 — Database migrations
tests/                   — pytest (async) + vitest
```

### Key Patterns

- **Auth**: Spotify OAuth → session cookie. User created on first login.
- **Tokens**: Fernet-encrypted in SQLite. Auto-refreshed via `get_spotify` dependency.
- **HTMX**: API routes return HTML partials, swapped into the page without full reload.
- **Async bridge**: `asyncio.to_thread()` wraps synchronous spotipy calls.
- **Generation**: collect base tracks → blacklist filter → discovery → shuffle → limits → write.

### Database

SQLite at `data/playlist_generator.db`. 8 tables: users, base_tracks, base_playlists, blacklist_tracks, blacklist_playlists, target_playlists, cover_image_configs, generation_history.

### CI/CD

GitHub Actions: semantic-release → Docker build → push to ghcr.io. Deploy via K8s.
