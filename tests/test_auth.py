import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.encryption import encrypt, decrypt
from playlist_generator.models.user import User
from playlist_generator.services import spotify_auth


@pytest.mark.asyncio
async def test_handle_callback_creates_new_user(db_session: AsyncSession):
    """First-time Spotify login should create a new user."""
    fake_token_info = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_at": time.time() + 3600,
    }
    fake_profile = {
        "id": "spotify_new_user",
        "display_name": "New User",
        "email": "new@example.com",
        "images": [{"url": "https://example.com/pic.jpg"}],
    }

    with (
        patch.object(spotify_auth, "asyncio") as mock_asyncio,
    ):
        # Make asyncio.to_thread return our fake data
        mock_asyncio.to_thread = AsyncMock(side_effect=[fake_token_info, fake_profile])

        user = await spotify_auth.handle_callback("fake_code", db_session)

    assert user.spotify_user_id == "spotify_new_user"
    assert user.display_name == "New User"
    assert user.email == "new@example.com"
    assert user.avatar_url == "https://example.com/pic.jpg"
    assert decrypt(user.access_token) == "new_access_token"
    assert decrypt(user.refresh_token) == "new_refresh_token"

    # Verify persisted
    result = await db_session.execute(
        select(User).where(User.spotify_user_id == "spotify_new_user")
    )
    assert result.scalar_one() is not None


@pytest.mark.asyncio
async def test_handle_callback_updates_existing_user(
    db_session: AsyncSession, sample_user: User
):
    """Returning user login should update tokens and profile."""
    fake_token_info = {
        "access_token": "updated_access_token",
        "refresh_token": "updated_refresh_token",
        "expires_at": time.time() + 7200,
    }
    fake_profile = {
        "id": sample_user.spotify_user_id,
        "display_name": "Updated Name",
        "email": "updated@example.com",
        "images": [],
    }

    with patch.object(spotify_auth, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(side_effect=[fake_token_info, fake_profile])

        user = await spotify_auth.handle_callback("fake_code", db_session)

    assert user.id == sample_user.id
    assert user.display_name == "Updated Name"
    assert decrypt(user.access_token) == "updated_access_token"
    assert user.avatar_url is None  # No images


@pytest.mark.asyncio
async def test_refresh_token_if_not_expired(
    db_session: AsyncSession, sample_user: User
):
    """Should return the existing token without refreshing if not expired."""
    original_access = decrypt(sample_user.access_token)
    token = await spotify_auth.refresh_token_if_needed(sample_user, db_session)
    assert token == original_access


@pytest.mark.asyncio
async def test_refresh_token_if_expired(
    db_session: AsyncSession, sample_user: User
):
    """Should refresh the token when it's expired."""
    sample_user.token_expires_at = time.time() - 100  # Already expired
    await db_session.commit()

    new_token_info = {
        "access_token": "refreshed_access_token",
        "expires_at": time.time() + 3600,
        "refresh_token": "new_refresh_too",
    }

    with patch.object(spotify_auth, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value=new_token_info)

        token = await spotify_auth.refresh_token_if_needed(sample_user, db_session)

    assert token == "refreshed_access_token"
    assert decrypt(sample_user.access_token) == "refreshed_access_token"
    assert decrypt(sample_user.refresh_token) == "new_refresh_too"


@pytest.mark.asyncio
async def test_get_spotify_client_returns_spotipy_instance(
    db_session: AsyncSession, sample_user: User
):
    """Should return a spotipy.Spotify instance with a valid token."""
    import spotipy

    client = await spotify_auth.get_spotify_client(sample_user, db_session)
    assert isinstance(client, spotipy.Spotify)
