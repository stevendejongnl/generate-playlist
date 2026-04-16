import logging
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, Response

from playlist_generator.database import get_db
from playlist_generator.dependencies import get_current_user, get_spotify
from playlist_generator.models.target import TargetPlaylist
from playlist_generator.models.user import User
from playlist_generator.services import generation as gen_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generation"])

templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


def _parse_optional_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    try:
        v = int(value)
        return v if v > 0 else None
    except ValueError:
        return None


def _parse_optional_float(value: str | None) -> float | None:
    if not value or not value.strip():
        return None
    try:
        v = float(value)
        return v if v > 0 else None
    except ValueError:
        return None


@router.post("/preview")
async def preview(
    request: Request,
    target_id: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
    max_tracks: Annotated[str | None, Form()] = None,
    max_minutes: Annotated[str | None, Form()] = None,
    discovery_mode: Annotated[str | None, Form()] = None,
    discovery_value: Annotated[str | None, Form()] = None,
) -> Response:
    assert templates is not None

    # Validate target belongs to user
    target = await db.get(TargetPlaylist, target_id)
    if not target or target.user_id != user.id:
        return HTMLResponse('<div class="alert alert-danger">Invalid target playlist</div>')

    result = await gen_service.preview(
        user_id=user.id,
        spotify=spotify,
        db=db,
        max_tracks=_parse_optional_int(max_tracks),
        max_minutes=_parse_optional_int(max_minutes),
        discovery_mode=discovery_mode if discovery_mode else None,
        discovery_value=_parse_optional_float(discovery_value),
    )

    total_minutes = result.total_duration_ms // 60_000
    total_seconds = (result.total_duration_ms % 60_000) // 1000

    return templates.TemplateResponse(
        request, "partials/generation_preview.html",
        {
            "tracks": result.tracks,
            "track_count": len(result.tracks),
            "discovery_count": result.discovery_count,
            "total_duration": f"{total_minutes}m {total_seconds}s",
            "target_id": target_id,
            "target_name": target.playlist_name or target.spotify_playlist_id,
        },
    )


@router.post("/execute")
async def execute(
    request: Request,
    target_id: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
    max_tracks: Annotated[str | None, Form()] = None,
    max_minutes: Annotated[str | None, Form()] = None,
    discovery_mode: Annotated[str | None, Form()] = None,
    discovery_value: Annotated[str | None, Form()] = None,
) -> Response:
    assert templates is not None

    target = await db.get(TargetPlaylist, target_id)
    if not target or target.user_id != user.id:
        return HTMLResponse('<div class="alert alert-danger">Invalid target playlist</div>')

    result = await gen_service.execute(
        user_id=user.id,
        target_playlist_id=target.spotify_playlist_id,
        target_playlist_name=target.playlist_name,
        spotify=spotify,
        db=db,
        max_tracks=_parse_optional_int(max_tracks),
        max_minutes=_parse_optional_int(max_minutes),
        discovery_mode=discovery_mode if discovery_mode else None,
        discovery_value=_parse_optional_float(discovery_value),
    )

    total_minutes = result.total_duration_ms // 60_000

    return HTMLResponse(
        f'<div class="alert alert-success" data-auto-dismiss>'
        f"Playlist generated! {len(result.tracks)} tracks "
        f"({total_minutes} min) written to {target.playlist_name or target.spotify_playlist_id}."
        f"</div>"
    )
