import base64
import logging
import os
import tempfile
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, Response

from playlist_generator.database import get_db
from playlist_generator.dependencies import get_current_user, get_spotify
from playlist_generator.models.target import TargetPlaylist
from playlist_generator.models.user import User
from playlist_generator.services import cover_image as cover_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cover-image", tags=["cover-image"])

templates: Jinja2Templates | None = None
_PREVIEW_DIR = os.path.join(tempfile.gettempdir(), "playlist-cover-previews")
os.makedirs(_PREVIEW_DIR, exist_ok=True)


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


def _save_preview(user_id: str, img: Image.Image) -> None:
    """Save a preview image for later upload."""
    img.save(os.path.join(_PREVIEW_DIR, f"{user_id}.png"), format="PNG")


def _load_preview(user_id: str) -> Image.Image | None:
    """Load a previously saved preview image."""
    path = os.path.join(_PREVIEW_DIR, f"{user_id}.png")
    if os.path.exists(path):
        return Image.open(path).copy()
    return None


def _img_to_html(jpeg_bytes: bytes) -> str:
    b64 = base64.b64encode(jpeg_bytes).decode()
    return (
        f'<img src="data:image/jpeg;base64,{b64}" alt="Cover preview" '
        f'style="max-width:100%;border-radius:8px;">'
    )


@router.post("/preview")
async def preview_image(
    text: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
    bg_color: Annotated[str, Form()] = "#496D89",
    text_color: Annotated[str, Form()] = "#FFFF00",
    font_size: Annotated[int, Form()] = 120,
    font_name: Annotated[str, Form()] = "Roboto-Black.ttf",
) -> HTMLResponse:
    """Generate a preview image, cache it, and return as HTML."""
    img = cover_service.generate_image(
        text=text,
        font_size=font_size,
        bg_color=bg_color,
        text_color=text_color,
        font_name=font_name,
    )
    _save_preview(user.id, img)
    # Show a smaller version for preview
    preview = img.copy()
    preview.thumbnail((600, 600))
    return HTMLResponse(_img_to_html(cover_service.image_to_jpeg_bytes(preview)))


@router.post("/preview-ai")
async def preview_ai_image(
    prompt: Annotated[str, Form()],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Generate an AI preview image, cache it, and return as HTML."""
    img = await cover_service.generate_with_openai(prompt)
    if img is None:
        return HTMLResponse(
            '<div class="alert alert-warning">OpenAI not configured or generation failed</div>'
        )
    _save_preview(user.id, img)
    preview = img.copy()
    preview.thumbnail((600, 600))
    return HTMLResponse(_img_to_html(cover_service.image_to_jpeg_bytes(preview)))


@router.post("/upload/{target_id}")
async def upload_image(
    target_id: str,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Upload the previously previewed cover image to Spotify."""
    target = await db.get(TargetPlaylist, target_id)
    if not target or target.user_id != user.id:
        return HTMLResponse('<div class="alert alert-danger">Invalid target</div>')

    img = _load_preview(user.id)
    if img is None:
        return HTMLResponse(
            '<div class="alert alert-warning">No preview found. Generate a preview first.</div>'
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
