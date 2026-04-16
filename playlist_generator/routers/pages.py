import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from playlist_generator.database import get_db
from playlist_generator.dependencies import get_current_user, get_current_user_or_none
from playlist_generator.models.user import User
from playlist_generator.models.target import TargetPlaylist
from playlist_generator.config import settings
from playlist_generator.models.cover_image import CoverImageConfig
from playlist_generator.models.history import GenerationHistory
from playlist_generator.services import base_list as base_list_service
from playlist_generator.services import blacklist as blacklist_service
from playlist_generator.services import cover_image as cover_service
from playlist_generator.services import skips as skips_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pages"])

templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


@router.get("/")
async def index(
    request: Request,
    user: Annotated[User | None, Depends(get_current_user_or_none)],
) -> Response:
    assert templates is not None
    if user:
        return templates.TemplateResponse(
            request, "pages/dashboard.html", {"user": user}
        )
    return templates.TemplateResponse(request, "pages/landing.html")


@router.get("/profile")
async def profile(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    assert templates is not None
    return templates.TemplateResponse(
        request, "pages/profile.html", {"user": user}
    )


@router.get("/base-list")
async def base_list_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    tracks = await base_list_service.get_tracks(user.id, db)
    playlists = await base_list_service.get_playlists(user.id, db)
    return templates.TemplateResponse(
        request, "pages/base_list.html",
        {"user": user, "tracks": tracks, "playlists": playlists},
    )


@router.get("/blacklist")
async def blacklist_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    tracks = await blacklist_service.get_tracks(user.id, db)
    playlists = await blacklist_service.get_playlists(user.id, db)
    return templates.TemplateResponse(
        request, "pages/blacklist.html",
        {"user": user, "tracks": tracks, "playlists": playlists},
    )


@router.get("/targets")
async def targets_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    result = await db.execute(
        select(TargetPlaylist)
        .where(TargetPlaylist.user_id == user.id)
        .order_by(TargetPlaylist.added_at.desc())
    )
    targets = list(result.scalars().all())
    return templates.TemplateResponse(
        request, "pages/targets.html",
        {"user": user, "targets": targets},
    )


@router.get("/generate")
async def generate_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    result = await db.execute(
        select(TargetPlaylist)
        .where(TargetPlaylist.user_id == user.id)
        .order_by(TargetPlaylist.is_default.desc(), TargetPlaylist.added_at.desc())
    )
    targets = list(result.scalars().all())
    return templates.TemplateResponse(
        request, "pages/generate.html",
        {"user": user, "targets": targets},
    )


@router.get("/history")
async def history_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    result = await db.execute(
        select(GenerationHistory)
        .where(GenerationHistory.user_id == user.id)
        .order_by(GenerationHistory.created_at.desc())
        .limit(50)
    )
    history = list(result.scalars().all())
    return templates.TemplateResponse(
        request, "pages/history.html",
        {"user": user, "history": history},
    )


@router.get("/cover-image")
async def cover_image_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    assert templates is not None
    configs = await cover_service.get_configs(user.id, db)
    result = await db.execute(
        select(TargetPlaylist)
        .where(TargetPlaylist.user_id == user.id)
        .order_by(TargetPlaylist.is_default.desc())
    )
    targets = list(result.scalars().all())
    return templates.TemplateResponse(
        request, "pages/cover_image.html",
        {
            "user": user,
            "configs": configs,
            "targets": targets,
            "has_openai": bool(settings.OPENAI_API_KEY),
        },
    )


@router.get("/skips")
async def skips_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    assert templates is not None
    return templates.TemplateResponse(
        request, "pages/skips.html", {"user": user}
    )
