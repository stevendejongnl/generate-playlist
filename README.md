# Playlist Generator

Multi-user web app that generates curated Spotify playlists from your favourite tracks and playlists.

## Features

- **Spotify OAuth login** — your Spotify account is your identity
- **Source management** — curate individual tracks and playlists as your base mix
- **Blacklist** — block tracks or entire playlists from ever appearing
- **Playlist generation** — deduplicate, shuffle, and push to a target Spotify playlist
- **Discovery** — optionally add Spotify recommendations (percentage or fixed count)
- **Limits** — set max tracks and/or max minutes
- **Cover art** — configurable text-based covers or AI-generated art (OpenAI DALL-E)
- **Generation history** — track what was generated and when

## Quick Start

```bash
# Install dependencies
uv sync
npm install

# Build frontend
npm run build

# Configure
cp .env.example .env   # fill in your Spotify credentials

# Run
uv run uvicorn playlist_generator.main:app --port 5000 --reload
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, async SQLAlchemy, SQLite |
| Frontend | Jinja2 + HTMX + TypeScript (Vite) |
| Auth | Spotify OAuth |
| Image gen | Pillow + OpenAI DALL-E (optional) |
| Deploy | Docker, Kubernetes, GitHub Actions |

## Tests

```bash
uv run pytest        # 54 Python tests
npm test             # 6 TypeScript tests
npm run typecheck    # Type checking
```
