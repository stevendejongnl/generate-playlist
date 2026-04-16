import logging
from typing import Annotated

import spotipy
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.database import get_db
from playlist_generator.models.user import User
from playlist_generator.services.spotify_auth import get_spotify_client

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the currently authenticated user from the session."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await db.get(User, user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_user_or_none(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Get the current user if authenticated, or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return await db.get(User, user_id)


async def get_spotify(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> spotipy.Spotify:
    """Get a Spotify client with a valid token for the current user."""
    return await get_spotify_client(user, db)
