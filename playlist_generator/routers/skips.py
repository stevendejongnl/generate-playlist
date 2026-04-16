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


@router.get("/detect")
async def detect_skips(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Detect skipped tracks from recent generations."""
    assert templates is not None
    skipped = await skips_service.detect_skipped_tracks(user.id, spotify, db)
    return templates.TemplateResponse(
        request, "partials/skipped_tracks.html", {"skipped": skipped}
    )


@router.get("/history")
async def play_history(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
) -> Response:
    """Get the user's recent play history."""
    assert templates is not None
    played = await skips_service.get_recently_played(spotify, limit=50)
    return templates.TemplateResponse(
        request, "partials/play_history.html", {"played": played}
    )
