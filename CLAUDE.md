# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run locally (Flask dev server on port 5000)
uv run python -m playlist_generator.main

# Docker build and run
make docker-build
make docker-run

# Docker Compose (port 5888)
docker-compose up -d
```

No test or lint commands are configured. Type hints exist throughout but are not checked by tooling.

## Environment

Copy `deployment.yaml.example` → `deployment.yaml` and fill in credentials, or create `.env`:

```
SPOTIPY_CLIENT_ID=...
SPOTIPY_CLIENT_SECRET=...
SPOTIPY_REDIRECT_URI=http://localhost:5000/authenticate
PLAYLIST_ID=...
```

## Architecture

Flask app that authenticates with Spotify via OAuth and builds a playlist from multiple sources.

### Core modules (`playlist_generator/`)

- **`main.py`** — Flask app entry point. Defines routes (`/`, `/authenticate`, `/actions/<action_type>`, `/sign_out`), session config (filesystem-based, `.flask_session/`), and `@login_required` decorator.
- **`spotify_functions.py`** — `SpotifyManager` class. Handles OAuth, playlist building, and cover image generation. Playlist build logic: collects tracks from liked songs (max 30) + 4 hardcoded source playlists, deduplicates, removes blacklisted tracks, shuffles, then replaces target playlist contents (in chunks of 100 per Spotify API limit).
- **`blacklist.py`** — `BlacklistManager` class. Persists excluded track IDs to `data/blacklist.json`.
- **`config.py`** — Loads `.env` and exposes Spotify credentials, playlist ID, and cache path.

### Persistence

| Path | Contents |
|------|----------|
| `data/blacklist.json` | Blacklisted track IDs |
| `.cache/` | Spotify OAuth token cache |
| `.flask_session/` | Server-side session files |

### CI/CD

GitHub Actions (`.github/workflows/deploy.yml`) builds and pushes Docker image to `ghcr.io/stevendejongnl/generate-playlist` on every push to `master`. Deploy by applying `deployment.yaml` to the Kubernetes cluster (NGINX ingress at `spotify.madebysteven.nl`).
