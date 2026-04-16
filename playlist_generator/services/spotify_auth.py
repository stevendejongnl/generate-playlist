import asyncio
import logging
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.config import settings
from playlist_generator.encryption import encrypt, decrypt
from playlist_generator.models.user import User

logger = logging.getLogger(__name__)


def _create_oauth_manager(state: str | None = None) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
        scope=settings.SPOTIFY_SCOPES,
        show_dialog=True,
        state=state,
    )


def get_auth_url() -> str:
    """Get the Spotify authorization URL to redirect the user to."""
    auth_manager = _create_oauth_manager()
    return auth_manager.get_authorize_url()


async def handle_callback(code: str, db: AsyncSession) -> User:
    """Exchange the auth code for tokens, upsert the user, and return the User."""
    auth_manager = _create_oauth_manager()
    token_info = await asyncio.to_thread(auth_manager.get_access_token, code)

    # Get the user's Spotify profile
    sp = spotipy.Spotify(auth=token_info["access_token"])
    profile = await asyncio.to_thread(sp.current_user)

    spotify_user_id = profile["id"]
    display_name = profile.get("display_name")
    email = profile.get("email")
    images = profile.get("images", [])
    avatar_url = images[0]["url"] if images else None

    # Upsert user
    result = await db.execute(
        select(User).where(User.spotify_user_id == spotify_user_id)
    )
    user = result.scalar_one_or_none()

    encrypted_access = encrypt(token_info["access_token"])
    encrypted_refresh = encrypt(token_info["refresh_token"])
    expires_at = float(token_info["expires_at"])

    if user:
        user.display_name = display_name
        user.email = email
        user.avatar_url = avatar_url
        user.access_token = encrypted_access
        user.refresh_token = encrypted_refresh
        user.token_expires_at = expires_at
        user.token_scopes = settings.SPOTIFY_SCOPES
        user.updated_at = time.time()
        logger.info("Updated existing user: %s", spotify_user_id)
    else:
        user = User(
            spotify_user_id=spotify_user_id,
            display_name=display_name,
            email=email,
            avatar_url=avatar_url,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            token_expires_at=expires_at,
            token_scopes=settings.SPOTIFY_SCOPES,
        )
        db.add(user)
        logger.info("Created new user: %s", spotify_user_id)

    await db.commit()
    await db.refresh(user)
    return user


async def refresh_token_if_needed(user: User, db: AsyncSession) -> str:
    """Check if the user's Spotify token is expired and refresh it. Returns a valid access token."""
    if user.token_expires_at > time.time() + 60:
        return decrypt(user.access_token)

    logger.info("Refreshing expired Spotify token for user %s", user.spotify_user_id)
    auth_manager = _create_oauth_manager()
    refresh_token = decrypt(user.refresh_token)
    new_token_info = await asyncio.to_thread(
        auth_manager.refresh_access_token, refresh_token
    )

    user.access_token = encrypt(new_token_info["access_token"])
    user.token_expires_at = float(new_token_info["expires_at"])
    if "refresh_token" in new_token_info:
        user.refresh_token = encrypt(new_token_info["refresh_token"])
    user.updated_at = time.time()

    await db.commit()
    return new_token_info["access_token"]


async def get_spotify_client(user: User, db: AsyncSession) -> spotipy.Spotify:
    """Return a ready-to-use Spotify client with a valid access token."""
    access_token = await refresh_token_if_needed(user, db)
    return spotipy.Spotify(auth=access_token)
