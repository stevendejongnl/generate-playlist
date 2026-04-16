import logging
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, Response

from playlist_generator.database import get_db
from playlist_generator.dependencies import get_current_user, get_spotify
from playlist_generator.models.user import User
from playlist_generator.services import base_list as base_list_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/base-list", tags=["base-list"])

templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


@router.post("/tracks")
async def add_track(
    request: Request,
    value: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    track = await base_list_service.add_track(user.id, value, spotify, db)
    if track:
        return templates.TemplateResponse(
            request, "partials/track_row.html",
            {"item": track, "delete_url": f"/api/base-list/tracks/{track.id}"},
        )
    return HTMLResponse('<div class="alert alert-warning" data-auto-dismiss>Track already in list or invalid</div>')


@router.delete("/tracks/{track_id}")
async def delete_track(
    track_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await base_list_service.delete_track(user.id, track_id, db)
    return HTMLResponse("")


@router.post("/playlists")
async def add_playlist(
    request: Request,
    value: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    playlist = await base_list_service.add_playlist(user.id, value, spotify, db)
    if playlist:
        return templates.TemplateResponse(
            request, "partials/playlist_row.html",
            {"item": playlist, "delete_url": f"/api/base-list/playlists/{playlist.id}"},
        )
    return HTMLResponse('<div class="alert alert-warning" data-auto-dismiss>Playlist already in list or invalid</div>')


@router.delete("/playlists/{playlist_id}")
async def delete_playlist(
    playlist_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await base_list_service.delete_playlist(user.id, playlist_id, db)
    return HTMLResponse("")
