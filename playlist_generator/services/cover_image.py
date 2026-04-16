import asyncio
import base64
import logging
import os
from io import BytesIO

import spotipy
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.config import settings
from playlist_generator.models.cover_image import CoverImageConfig

logger = logging.getLogger(__name__)

_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "fonts")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def generate_image(
    text: str,
    font_size: int = 120,
    width: int = 1500,
    height: int = 1500,
    bg_color: str = "#496D89",
    text_color: str = "#FFFF00",
    font_name: str = "Roboto-Black.ttf",
) -> Image.Image:
    """Create a cover image with centered text."""
    bg_rgb = _hex_to_rgb(bg_color)
    text_rgb = _hex_to_rgb(text_color)

    img = Image.new("RGB", (width, height), color=bg_rgb)
    draw = ImageDraw.Draw(img)

    font_path = os.path.join(_FONTS_DIR, font_name)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError:
        logger.warning("Font not found: %s. Using default font.", font_path)
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (width - text_w) / 2
    y = (height - text_h) / 2
    draw.text((x, y), text, fill=text_rgb, font=font)

    return img


def image_to_jpeg_bytes(img: Image.Image) -> bytes:
    """Convert a PIL Image to JPEG bytes."""
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


async def upload_to_spotify(
    playlist_id: str, img: Image.Image, spotify: spotipy.Spotify
) -> None:
    """Upload a cover image to a Spotify playlist."""
    jpeg_bytes = image_to_jpeg_bytes(img)
    b64_data = base64.b64encode(jpeg_bytes).decode()
    await asyncio.to_thread(spotify.playlist_upload_cover_image, playlist_id, b64_data)


# ── Config CRUD ──────────────────────────────────────

async def get_configs(user_id: str, db: AsyncSession) -> list[CoverImageConfig]:
    result = await db.execute(
        select(CoverImageConfig)
        .where(CoverImageConfig.user_id == user_id)
        .order_by(CoverImageConfig.created_at.desc())
    )
    return list(result.scalars().all())


async def get_config(config_id: str, user_id: str, db: AsyncSession) -> CoverImageConfig | None:
    config = await db.get(CoverImageConfig, config_id)
    if config and config.user_id == user_id:
        return config
    return None


async def create_config(
    user_id: str,
    name: str,
    text: str,
    db: AsyncSession,
    font_size: int = 120,
    width: int = 1500,
    height: int = 1500,
    bg_color: str = "#496D89",
    text_color: str = "#FFFF00",
    font_name: str = "Roboto-Black.ttf",
    is_default: bool = False,
) -> CoverImageConfig:
    if is_default:
        await db.execute(
            update(CoverImageConfig)
            .where(CoverImageConfig.user_id == user_id)
            .values(is_default=0)
        )

    config = CoverImageConfig(
        user_id=user_id,
        name=name,
        text=text,
        font_size=font_size,
        width=width,
        height=height,
        bg_color=bg_color,
        text_color=text_color,
        font_name=font_name,
        is_default=1 if is_default else 0,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def delete_config(config_id: str, user_id: str, db: AsyncSession) -> bool:
    config = await db.get(CoverImageConfig, config_id)
    if not config or config.user_id != user_id:
        return False
    await db.delete(config)
    await db.commit()
    return True


async def generate_with_openai(prompt: str) -> Image.Image | None:
    """Generate a cover image using OpenAI DALL-E. Returns None if not configured."""
    if not settings.OPENAI_API_KEY:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = await asyncio.to_thread(
            client.images.generate,
            model="dall-e-3",
            prompt=f"Album cover art: {prompt}. Square format, no text, artistic, high quality.",
            n=1,
            size="1024x1024",
            response_format="b64_json",
        )

        if response.data and response.data[0].b64_json:
            import base64 as b64mod
            img_bytes = b64mod.b64decode(response.data[0].b64_json)
            img = Image.open(BytesIO(img_bytes))
            # Resize to Spotify's preferred 1500x1500
            img = img.resize((1500, 1500), Image.Resampling.LANCZOS)
            return img
    except Exception:
        logger.exception("OpenAI image generation failed")

    return None
