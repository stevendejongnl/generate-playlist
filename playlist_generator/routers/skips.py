import logging
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, Response

from playlist_generator.database import get_db
from playlist_generator.dependencies import get_current_user, get_spotify
from playlist_generator.models.user import User
from playlist_generator.services import skips as skips_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skips", tags=["skips"])

templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


@router.post("/sync")
async def sync_history(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pages: int = 1,
) -> HTMLResponse:
    """Fetch new plays from Spotify and store them. Returns a status message."""
    new_count = await skips_service.sync_play_history(user.id, spotify, db, pages=pages)
    stats = await skips_service.get_history_stats(user.id, db)
    return HTMLResponse(
        f'<div class="alert alert-success" data-auto-dismiss>'
        f"Synced {new_count} new plays. Total: {stats['total_plays']} plays, "
        f"{stats['total_skips']} skips in your history."
        f"</div>"
    )


@router.get("/detect")
async def detect_skips(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Sync latest plays, then show skipped tracks from accumulated history."""
    assert templates is not None
    # Auto-sync latest plays first
    await skips_service.sync_play_history(user.id, spotify, db, pages=1)
    skipped = await skips_service.get_skip_summary(user.id, db)
    stats = await skips_service.get_history_stats(user.id, db)
    return templates.TemplateResponse(
        request, "partials/skipped_tracks.html",
        {"skipped": skipped, "stats": stats},
    )


@router.get("/history")
async def play_history(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Get persisted play history from the database."""
    assert templates is not None
    tracks = await skips_service.get_play_history(user.id, db, limit=100)
    stats = await skips_service.get_history_stats(user.id, db)
    return templates.TemplateResponse(
        request, "partials/play_history.html",
        {"played": tracks, "stats": stats},
    )
