import logging
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, Response, StreamingResponse

from playlist_generator.database import get_db
from playlist_generator.dependencies import get_current_user, get_spotify
from playlist_generator.models.target import TargetPlaylist
from playlist_generator.models.user import User
from playlist_generator.services import cover_image as cover_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cover-image", tags=["cover-image"])

templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


@router.post("/preview")
async def preview_image(
    text: Annotated[str, Form()],
    bg_color: Annotated[str, Form()] = "#496D89",
    text_color: Annotated[str, Form()] = "#FFFF00",
    font_size: Annotated[int, Form()] = 120,
    font_name: Annotated[str, Form()] = "Roboto-Black.ttf",
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Generate a preview image and return it as JPEG."""
    img = cover_service.generate_image(
        text=text,
        font_size=font_size,
        bg_color=bg_color,
        text_color=text_color,
        font_name=font_name,
        width=600,  # Smaller for preview
        height=600,
    )
    jpeg_bytes = cover_service.image_to_jpeg_bytes(img)
    from io import BytesIO

    return StreamingResponse(BytesIO(jpeg_bytes), media_type="image/jpeg")


@router.post("/preview-ai")
async def preview_ai_image(
    prompt: Annotated[str, Form()],
    user: User = Depends(get_current_user),
) -> Response:
    """Generate a preview image using OpenAI DALL-E."""
    img = await cover_service.generate_with_openai(prompt)
    if img is None:
        return HTMLResponse(
            '<div class="alert alert-warning">OpenAI not configured or generation failed</div>'
        )
    jpeg_bytes = cover_service.image_to_jpeg_bytes(img)
    from io import BytesIO

    return StreamingResponse(BytesIO(jpeg_bytes), media_type="image/jpeg")


@router.post("/upload/{target_id}")
async def upload_image(
    target_id: str,
    text: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
    bg_color: Annotated[str, Form()] = "#496D89",
    text_color: Annotated[str, Form()] = "#FFFF00",
    font_size: Annotated[int, Form()] = 120,
    font_name: Annotated[str, Form()] = "Roboto-Black.ttf",
    use_ai: Annotated[str, Form()] = "",
    ai_prompt: Annotated[str, Form()] = "",
) -> Response:
    """Generate and upload a cover image to a Spotify playlist."""
    target = await db.get(TargetPlaylist, target_id)
    if not target or target.user_id != user.id:
        return HTMLResponse('<div class="alert alert-danger">Invalid target</div>')

    if use_ai and ai_prompt:
        img = await cover_service.generate_with_openai(ai_prompt)
        if img is None:
            return HTMLResponse('<div class="alert alert-warning">AI generation failed, using text fallback</div>')
    else:
        img = cover_service.generate_image(
            text=text,
            font_size=font_size,
            bg_color=bg_color,
            text_color=text_color,
            font_name=font_name,
        )

    await cover_service.upload_to_spotify(target.spotify_playlist_id, img, spotify)

    return HTMLResponse(
        f'<div class="alert alert-success" data-auto-dismiss>'
        f"Cover image uploaded to {target.playlist_name or target.spotify_playlist_id}!"
        f"</div>"
    )


@router.post("/configs")
async def save_config(
    request: Request,
    name: Annotated[str, Form()],
    text: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    bg_color: Annotated[str, Form()] = "#496D89",
    text_color: Annotated[str, Form()] = "#FFFF00",
    font_size: Annotated[int, Form()] = 120,
    font_name: Annotated[str, Form()] = "Roboto-Black.ttf",
) -> Response:
    assert templates is not None
    config = await cover_service.create_config(
        user_id=user.id,
        name=name,
        text=text,
        db=db,
        font_size=font_size,
        bg_color=bg_color,
        text_color=text_color,
        font_name=font_name,
    )
    return templates.TemplateResponse(
        request, "partials/cover_config_row.html", {"config": config}
    )


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await cover_service.delete_config(config_id, user.id, db)
    return HTMLResponse("")
