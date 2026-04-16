import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.user import User
from playlist_generator.services import cover_image as cover_service


def test_generate_image_creates_correct_size():
    img = cover_service.generate_image("Test", width=500, height=500)
    assert isinstance(img, Image.Image)
    assert img.size == (500, 500)


def test_generate_image_default_size():
    img = cover_service.generate_image("Hello")
    assert img.size == (1500, 1500)


def test_image_to_jpeg_bytes():
    img = cover_service.generate_image("Test", width=100, height=100)
    data = cover_service.image_to_jpeg_bytes(img)
    assert isinstance(data, bytes)
    assert len(data) > 0
    # JPEG magic bytes
    assert data[:2] == b"\xff\xd8"


def test_hex_to_rgb():
    assert cover_service._hex_to_rgb("#FF0000") == (255, 0, 0)
    assert cover_service._hex_to_rgb("#1db954") == (29, 185, 84)
    assert cover_service._hex_to_rgb("000000") == (0, 0, 0)


def test_generate_image_custom_colors():
    img = cover_service.generate_image(
        "Colors", bg_color="#FF0000", text_color="#00FF00", width=100, height=100
    )
    # Check that the background pixel is red-ish
    pixel = img.getpixel((0, 0))
    assert pixel == (255, 0, 0)


@pytest.mark.asyncio
async def test_create_and_get_configs(db_session: AsyncSession, sample_user: User):
    config = await cover_service.create_config(
        user_id=sample_user.id,
        name="Chill Vibes",
        text="Chill",
        db=db_session,
        bg_color="#1a1a2e",
        text_color="#e94560",
    )
    assert config.name == "Chill Vibes"

    configs = await cover_service.get_configs(sample_user.id, db_session)
    assert len(configs) == 1
    assert configs[0].name == "Chill Vibes"


@pytest.mark.asyncio
async def test_delete_config(db_session: AsyncSession, sample_user: User):
    config = await cover_service.create_config(
        user_id=sample_user.id, name="Delete Me", text="Test", db=db_session
    )
    deleted = await cover_service.delete_config(config.id, sample_user.id, db_session)
    assert deleted is True

    configs = await cover_service.get_configs(sample_user.id, db_session)
    assert len(configs) == 0


@pytest.mark.asyncio
async def test_delete_config_wrong_user(db_session: AsyncSession, sample_user: User):
    config = await cover_service.create_config(
        user_id=sample_user.id, name="Protected", text="Test", db=db_session
    )
    deleted = await cover_service.delete_config(config.id, "wrong_user", db_session)
    assert deleted is False
