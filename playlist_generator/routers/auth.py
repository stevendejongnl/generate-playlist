import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from playlist_generator.database import get_db
from playlist_generator.services import spotify_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.get("/login")
async def login() -> RedirectResponse:
    """Redirect the user to Spotify's authorization page."""
    auth_url = spotify_auth.get_auth_url()
    logger.info("Redirecting to Spotify login")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    """Handle the Spotify OAuth callback — create or update the user."""
    user = await spotify_auth.handle_callback(code, db)
    request.session["user_id"] = user.id
    logger.info("User %s logged in (spotify: %s)", user.id, user.spotify_user_id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Clear the session and redirect to the landing page."""
    request.session.clear()
    logger.info("User logged out")
    return RedirectResponse(url="/", status_code=303)
