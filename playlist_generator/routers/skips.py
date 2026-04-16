import logging
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

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
) -> Response:
    """Detect frequently skipped tracks from play history."""
    assert templates is not None
    tracks = await skips_service.get_play_history_with_duration(spotify)
    summary = skips_service.get_skip_summary(tracks)
    # Only show tracks that were actually skipped at least once
    skipped = {tid: s for tid, s in summary.items() if s["skip_count"] > 0}
    return templates.TemplateResponse(
        request, "partials/skipped_tracks.html", {"skipped": skipped}
    )


@router.get("/history")
async def play_history(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
) -> Response:
    """Get the user's recent play history with actual play durations."""
    assert templates is not None
    tracks = await skips_service.get_play_history_with_duration(spotify)
    return templates.TemplateResponse(
        request, "partials/play_history.html", {"played": tracks}
    )
