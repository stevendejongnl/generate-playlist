import asyncio
import logging
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, Response

from playlist_generator.database import get_db
from playlist_generator.dependencies import get_current_user, get_spotify
from playlist_generator.models.target import TargetPlaylist
from playlist_generator.models.user import User
from playlist_generator.services.base_list import extract_playlist_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/targets", tags=["targets"])

templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


async def _get_targets(user_id: str, db: AsyncSession) -> list[TargetPlaylist]:
    result = await db.execute(
        select(TargetPlaylist)
        .where(TargetPlaylist.user_id == user_id)
        .order_by(TargetPlaylist.added_at.desc())
    )
    return list(result.scalars().all())


@router.post("")
async def add_target(
    request: Request,
    value: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    playlist_id = extract_playlist_id(value)
    if not playlist_id:
        return HTMLResponse('<div class="alert alert-warning" data-auto-dismiss>Invalid playlist</div>')

    existing = await db.execute(
        select(TargetPlaylist).where(
            TargetPlaylist.user_id == user.id,
            TargetPlaylist.spotify_playlist_id == playlist_id,
        )
    )
    if existing.scalar_one_or_none():
        return HTMLResponse('<div class="alert alert-warning" data-auto-dismiss>Target already added</div>')

    try:
        pl_data = await asyncio.to_thread(
            spotify.playlist, playlist_id, fields="name"
        )
        playlist_name = pl_data.get("name", "")
    except Exception:
        playlist_name = None

    # If this is the first target, make it default
    count_result = await db.execute(
        select(TargetPlaylist).where(TargetPlaylist.user_id == user.id)
    )
    is_first = not count_result.scalars().first()

    target = TargetPlaylist(
        user_id=user.id,
        spotify_playlist_id=playlist_id,
        playlist_name=playlist_name,
        is_default=1 if is_first else 0,
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)

    return templates.TemplateResponse(
        request, "partials/target_row.html", {"item": target}
    )


@router.delete("/{target_id}")
async def delete_target(
    target_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    target = await db.get(TargetPlaylist, target_id)
    if not target or target.user_id != user.id:
        return HTMLResponse("", status_code=404)
    await db.delete(target)
    await db.commit()
    return HTMLResponse("")


@router.patch("/{target_id}/default")
async def set_default(
    request: Request,
    target_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    target = await db.get(TargetPlaylist, target_id)
    if not target or target.user_id != user.id:
        return HTMLResponse("", status_code=404)

    # Clear all defaults for this user, then set the new one
    await db.execute(
        update(TargetPlaylist)
        .where(TargetPlaylist.user_id == user.id)
        .values(is_default=0)
    )
    target.is_default = 1
    await db.commit()

    # Return the full updated list
    targets = await _get_targets(user.id, db)
    return templates.TemplateResponse(
        request, "partials/target_list.html", {"targets": targets}
    )
