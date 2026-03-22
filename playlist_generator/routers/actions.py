import logging
import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response, RedirectResponse

from playlist_generator.blacklist import BlacklistManager
from playlist_generator.playlists import PlaylistManager, extract_playlist_id
from playlist_generator.spotify_functions import SpotifyManager
from playlist_generator.dependencies import (
    get_blacklist_manager,
    get_playlist_manager,
    get_spotify_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter()
templates: Optional[Jinja2Templates] = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


def _require_auth(request: Request) -> bool:
    return bool(request.session.get('token_info'))


@router.get('/actions/generate')
def action_generate(
    request: Request,
    blacklist: Annotated[BlacklistManager, Depends(get_blacklist_manager)],
    playlists: Annotated[PlaylistManager, Depends(get_playlist_manager)],
    spotify: Annotated[SpotifyManager, Depends(get_spotify_manager)],
) -> Response:
    if not _require_auth(request):
        return RedirectResponse(url='/')
    logger.info('Building playlist...')
    try:
        source_ids = [p['id'] for p in playlists.get_sources()] or None
        return spotify.build_playlist(request, blacklist.get_tracks(), source_ids, playlists)
    except Exception as e:
        logger.error(f"Error building playlist: {e}", exc_info=True)
        return templates.TemplateResponse(request, 'pages/error.html', {'message': str(e)})


@router.get('/actions/image')
def action_image(
    request: Request,
    spotify: Annotated[SpotifyManager, Depends(get_spotify_manager)],
    playlists: Annotated[PlaylistManager, Depends(get_playlist_manager)],
) -> Response:
    if not _require_auth(request):
        return RedirectResponse(url='/')
    logger.info('Generating cover image...')
    try:
        return spotify.generate_cover_image(request, playlists)
    except Exception as e:
        logger.error(f"Error generating image: {e}", exc_info=True)
        return templates.TemplateResponse(request, 'pages/error.html', {'message': str(e)})


@router.get('/actions/blacklist')
def blacklist_get(
    request: Request,
    blacklist: Annotated[BlacklistManager, Depends(get_blacklist_manager)],
) -> Response:
    if not _require_auth(request):
        return RedirectResponse(url='/')
    logger.info('Rendering blacklist editor.')
    tracks = blacklist.get_tracks()
    return templates.TemplateResponse(request, 'pages/actions_blacklist.html', {'data': {'tracks': tracks}})


@router.post('/actions/blacklist')
def blacklist_post(
    request: Request,
    blacklist: Annotated[BlacklistManager, Depends(get_blacklist_manager)],
    add_track: Annotated[str, Form()] = '',
    delete_track: Annotated[str, Form()] = '',
) -> Response:
    if not _require_auth(request):
        return RedirectResponse(url='/')
    if add_track:
        logger.info(f'Adding track to blacklist: {add_track}')
        blacklist.add_track(add_track)
    if delete_track:
        logger.info(f'Deleting track from blacklist: {delete_track}')
        blacklist.delete_track(delete_track)
    return RedirectResponse(url='/actions/blacklist', status_code=303)


@router.get('/actions/playlists')
def playlists_get(
    request: Request,
    playlists: Annotated[PlaylistManager, Depends(get_playlist_manager)],
) -> Response:
    if not _require_auth(request):
        return RedirectResponse(url='/')
    logger.info('Rendering playlists manager.')
    data = playlists.get_data()
    return templates.TemplateResponse(request, 'pages/actions_playlists.html', {'data': data})


@router.post('/actions/playlists')
def playlists_post(
    request: Request,
    playlists: Annotated[PlaylistManager, Depends(get_playlist_manager)],
    spotify: Annotated[SpotifyManager, Depends(get_spotify_manager)],
    add_source: Annotated[str, Form()] = '',
    delete_source: Annotated[str, Form()] = '',
    set_target: Annotated[str, Form()] = '',
) -> Response:
    if not _require_auth(request):
        return RedirectResponse(url='/')
    if add_source:
        playlist_id = extract_playlist_id(add_source)
        name = _fetch_playlist_name(request, spotify, playlist_id)
        logger.info(f'Adding source playlist: {playlist_id} ({name})')
        playlists.add_source(playlist_id, name)
    if delete_source:
        logger.info(f'Deleting source playlist: {delete_source}')
        playlists.delete_source(delete_source)
    if set_target:
        logger.info(f'Setting target playlist: {set_target}')
        playlists.set_target(set_target)
    return RedirectResponse(url='/actions/playlists', status_code=303)


def _fetch_playlist_name(request: Request, spotify: SpotifyManager, playlist_id: str) -> str:
    try:
        client = spotify.get_spotify_client(request)
        if client:
            return client.playlist(playlist_id, fields='name')['name']
    except Exception as e:
        logger.warning(f"Could not fetch playlist name for {playlist_id}: {e}")
    return playlist_id


@router.get('/actions')
@router.get('/actions/{action_type}')
def action_unknown(request: Request, action_type: Optional[str] = None) -> Response:
    if not _require_auth(request):
        return RedirectResponse(url='/')
    if not action_type:
        return templates.TemplateResponse(request, 'pages/actions_not-set.html', {})
    logger.warning(f'Unknown action_type: {action_type}')
    return templates.TemplateResponse(
        request,
        'pages/error.html',
        {'message': "If you don't know what you are doing, do it right!"},
        status_code=404,
    )
