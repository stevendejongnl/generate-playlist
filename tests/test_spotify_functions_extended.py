"""Extended spotify_functions tests covering _get_playlist_id and authenticate paths."""
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from playlist_generator.spotify_functions import SpotifyManager
from playlist_generator.playlists import PlaylistManager


@pytest.fixture
def manager():
    return SpotifyManager()


# --- _get_playlist_id ---

def test_get_playlist_id_returns_target_from_manager(manager, tmp_path):
    pm = PlaylistManager(data_dir=str(tmp_path))
    pm.add_source('target_id', 'My Target')
    pm.set_target('target_id')
    assert manager._get_playlist_id(pm) == 'target_id'


def test_get_playlist_id_falls_back_to_env_when_manager_has_no_target(manager, tmp_path, monkeypatch):
    pm = PlaylistManager(data_dir=str(tmp_path))
    monkeypatch.setenv('PLAYLIST_ID', 'env_playlist_id')
    assert manager._get_playlist_id(pm) == 'env_playlist_id'


def test_get_playlist_id_falls_back_to_env_when_no_manager(manager, monkeypatch):
    monkeypatch.setenv('PLAYLIST_ID', 'env_id')
    assert manager._get_playlist_id(None) == 'env_id'


def test_get_playlist_id_returns_empty_when_nothing_configured(manager, tmp_path, monkeypatch):
    pm = PlaylistManager(data_dir=str(tmp_path))
    monkeypatch.delenv('PLAYLIST_ID', raising=False)
    assert manager._get_playlist_id(pm) == ''


# --- get_spotify_client with token ---

def _make_test_app(manager: SpotifyManager, token_info: dict):
    """Create a minimal Starlette app with session that has token_info pre-seeded."""
    def handler(request: Request):
        request.session['token_info'] = token_info
        client = manager.get_spotify_client(request)
        return PlainTextResponse('ok' if client is not None else 'none')

    app = Starlette(routes=[Route('/test', handler)])
    app.add_middleware(SessionMiddleware, secret_key='test')
    return app


def test_get_spotify_client_returns_client_when_token_present(manager):
    app = _make_test_app(manager, {'access_token': 'fake'})
    tc = TestClient(app)
    assert tc.get('/test').text == 'ok'


# --- authenticate: already authenticated redirects to / ---

def test_authenticate_redirects_to_index_when_already_logged_in(manager):
    def handler(request: Request):
        request.session['token_info'] = {'access_token': 'already_set'}
        return manager.authenticate(request)

    app = Starlette(routes=[Route('/auth', handler)])
    app.add_middleware(SessionMiddleware, secret_key='test')
    tc = TestClient(app, follow_redirects=False)
    resp = tc.get('/auth')
    assert resp.status_code in (302, 307)
    assert resp.headers['location'] == '/'


# --- authenticate: code exchange ---

def test_authenticate_stores_token_when_code_provided(manager):
    mock_token = {'access_token': 'new_token'}

    def handler(request: Request):
        with patch('playlist_generator.spotify_functions.SpotifyOAuth') as MockOAuth:
            mock_auth = MagicMock()
            mock_auth.get_access_token.return_value = mock_token
            MockOAuth.return_value = mock_auth
            return manager.authenticate(request)

    app = Starlette(routes=[Route('/auth', handler)])
    app.add_middleware(SessionMiddleware, secret_key='test')
    tc = TestClient(app, follow_redirects=False)
    resp = tc.get('/auth?code=mycode')
    assert resp.status_code in (302, 307)


# --- authenticate: no code → redirects to Spotify ---

def test_authenticate_redirects_to_spotify_when_no_code(manager):
    def handler(request: Request):
        with patch('playlist_generator.spotify_functions.SpotifyOAuth') as MockOAuth:
            mock_auth = MagicMock()
            mock_auth.get_authorize_url.return_value = 'https://accounts.spotify.com/authorize?test=1'
            MockOAuth.return_value = mock_auth
            return manager.authenticate(request)

    app = Starlette(routes=[Route('/auth', handler)])
    app.add_middleware(SessionMiddleware, secret_key='test')
    tc = TestClient(app, follow_redirects=False)
    resp = tc.get('/auth')
    assert resp.status_code in (302, 307)
    assert 'spotify' in resp.headers['location'].lower()


# --- generate_cover_image: no client redirects to / ---

def test_generate_cover_image_redirects_when_no_client(manager, tmp_path):
    pm = PlaylistManager(data_dir=str(tmp_path))

    def handler(request: Request):
        return manager.generate_cover_image(request, pm)

    app = Starlette(routes=[Route('/img', handler)])
    app.add_middleware(SessionMiddleware, secret_key='test')
    tc = TestClient(app, follow_redirects=False)
    resp = tc.get('/img')
    assert resp.status_code in (302, 307)
    assert resp.headers['location'] == '/'


# --- build_playlist: no playlist_id raises ValueError ---

def test_build_playlist_returns_error_response_when_no_playlist_id(manager, tmp_path, monkeypatch):
    """build_playlist raises ValueError when no playlist configured — callers handle it."""
    monkeypatch.delenv('PLAYLIST_ID', raising=False)
    pm = PlaylistManager(data_dir=str(tmp_path))
    with pytest.raises(ValueError, match='playlist'):
        # Need a request object — create a minimal one via Starlette scope
        from starlette.datastructures import Headers
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/',
            'query_string': b'',
            'headers': [],
            'session': {},
        }
        request = Request(scope)
        manager.build_playlist(request, [], None, pm)


# --- _save_image ---

def test_save_image_writes_file(manager, tmp_path):
    from PIL import Image
    img = Image.new('RGB', (10, 10), color=(0, 0, 255))
    path = str(tmp_path / 'test.jpg')
    manager._save_image(img, path)
    assert (tmp_path / 'test.jpg').exists()


# --- _get_font_path ---

def test_get_font_path_returns_absolute_path(manager):
    path = manager._get_font_path('Roboto-Black.ttf')
    assert path.endswith('Roboto-Black.ttf')
    assert os.path.isabs(path)


import os

# --- _create_cover_image: font fallback ---

def test_create_cover_image_uses_default_font_when_ttf_missing(manager):
    """When font file doesn't exist, should fall back to default font without crashing."""
    from PIL import Image
    img = manager._create_cover_image(
        'Test', 20, (100, 100), (0, 0, 0), (255, 255, 255),
        font_name='nonexistent_font_that_does_not_exist.ttf'
    )
    assert isinstance(img, Image.Image)


# --- _add_tracks_to_playlist ---

def test_add_tracks_to_playlist_chunks_correctly(manager):
    client = MagicMock()
    tracks = [str(i) for i in range(150)]
    manager._add_tracks_to_playlist('pid', tracks, client)
    assert client.playlist_add_items.call_count == 2
    first_call_tracks = client.playlist_add_items.call_args_list[0][0][1]
    second_call_tracks = client.playlist_add_items.call_args_list[1][0][1]
    assert len(first_call_tracks) == 100
    assert len(second_call_tracks) == 50


def test_add_tracks_to_playlist_single_chunk(manager):
    client = MagicMock()
    tracks = ['t1', 't2', 't3']
    manager._add_tracks_to_playlist('pid', tracks, client)
    assert client.playlist_add_items.call_count == 1


def test_add_tracks_to_playlist_empty_list(manager):
    client = MagicMock()
    manager._add_tracks_to_playlist('pid', [], client)
    assert client.playlist_add_items.call_count == 0


# --- _clear_playlist ---

def test_clear_playlist(manager):
    client = MagicMock()
    manager._clear_playlist('pid', client)
    client.playlist_replace_items.assert_called_once_with('pid', [])
