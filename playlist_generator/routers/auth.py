import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.responses import Response

from playlist_generator.dependencies import get_spotify_manager
from playlist_generator.spotify_functions import SpotifyManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/authenticate')
def authenticate(
    request: Request,
    spotify: Annotated[SpotifyManager, Depends(get_spotify_manager)],
) -> Response:
    logger.info('User requested authentication.')
    return spotify.authenticate(request)


@router.get('/sign_out')
def sign_out(request: Request) -> Response:
    logger.info('User signed out.')
    request.session.clear()
    from starlette.responses import RedirectResponse
    return RedirectResponse(url='/')
