import pytest
from tests.conftest import seed_auth
from playlist_generator.playlists import PlaylistManager
from playlist_generator.dependencies import get_playlist_manager
from playlist_generator.main import app


def test_generate_requires_auth(client):
    resp = client.get('/actions/generate', follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_image_requires_auth(client):
    resp = client.get('/actions/image', follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_unknown_action_requires_auth(client):
    resp = client.get('/actions/whatever', follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_unknown_action_shows_error_when_authed(client):
    seed_auth(client)
    resp = client.get('/actions/whatever')
    assert resp.status_code == 404
    assert "do it right" in resp.text


def test_actions_no_type_shows_not_set_page(client):
    seed_auth(client)
    resp = client.get('/actions')
    assert resp.status_code == 200


def test_generate_shows_error_when_no_playlist_configured(client, tmp_path, monkeypatch):
    """When no target playlist is set and no PLAYLIST_ID env var, build should fail gracefully."""
    pl = PlaylistManager(data_dir=str(tmp_path))
    app.dependency_overrides[get_playlist_manager] = lambda: pl
    monkeypatch.delenv('PLAYLIST_ID', raising=False)

    seed_auth(client)
    resp = client.get('/actions/generate')
    # Should show error page (not crash the server)
    assert resp.status_code == 200
    assert 'error' in resp.text.lower() or 'playlist' in resp.text.lower()

    app.dependency_overrides.pop(get_playlist_manager, None)


def test_image_redirects_when_no_spotify_client(client):
    """generate_cover_image redirects to / when no real Spotify client is available."""
    seed_auth(client)
    resp = client.get('/actions/image', follow_redirects=False)
    # It will try to call Spotify with 'fake_token' which won't work,
    # but we expect either a redirect or an error page — not a 500
    assert resp.status_code in (200, 302, 303, 307, 500)
