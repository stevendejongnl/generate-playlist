import pytest
from fastapi.testclient import TestClient

from playlist_generator.blacklist import BlacklistManager
from playlist_generator.playlists import PlaylistManager
from playlist_generator.spotify_functions import SpotifyManager
from playlist_generator.dependencies import (
    get_blacklist_manager,
    get_playlist_manager,
    get_spotify_manager,
)
from playlist_generator.main import app
from playlist_generator.routers import actions


@pytest.fixture
def tmp_blacklist(tmp_path):
    return BlacklistManager(data_dir=str(tmp_path))


@pytest.fixture
def tmp_playlists(tmp_path):
    return PlaylistManager(data_dir=str(tmp_path))


@pytest.fixture
def client(tmp_path):
    bl = BlacklistManager(data_dir=str(tmp_path))
    pl = PlaylistManager(data_dir=str(tmp_path))
    app.dependency_overrides[get_blacklist_manager] = lambda: bl
    app.dependency_overrides[get_playlist_manager] = lambda: pl
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client(tmp_path):
    """Client with a fake token in session (simulates authenticated user)."""
    bl = BlacklistManager(data_dir=str(tmp_path))
    pl = PlaylistManager(data_dir=str(tmp_path))
    app.dependency_overrides[get_blacklist_manager] = lambda: bl
    app.dependency_overrides[get_playlist_manager] = lambda: pl
    with TestClient(app, raise_server_exceptions=True) as c:
        # Seed the session with a fake token
        c.get('/_test_seed_session')
        # We inject it by calling the internal session directly
        # Instead, use a helper route via app state trick:
        with c.session_transaction() if hasattr(c, 'session_transaction') else _noop() as sess:
            pass
        yield c, bl, pl
    app.dependency_overrides.clear()


class _noop:
    def __enter__(self): return {}
    def __exit__(self, *a): pass


def seed_auth(client: TestClient) -> None:
    """Seed a fake Spotify token into the session cookie."""
    # Hit an internal test endpoint that sets the session
    resp = client.get('/__test__/seed_auth')
    assert resp.status_code == 200


# Register a test-only route to seed session (only active during tests)
from fastapi import Request as _Request
from starlette.responses import JSONResponse as _JSONResponse

@app.get('/__test__/seed_auth', include_in_schema=False)
def _seed_auth(request: _Request) -> _JSONResponse:
    request.session['token_info'] = {'access_token': 'fake_token'}
    return _JSONResponse({'ok': True})
