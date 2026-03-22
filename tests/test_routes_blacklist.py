import pytest
from tests.conftest import seed_auth


def test_blacklist_get_requires_auth(client):
    resp = client.get('/actions/blacklist', follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_blacklist_get_renders_page(client):
    seed_auth(client)
    resp = client.get('/actions/blacklist')
    assert resp.status_code == 200
    assert 'Edit Blacklist' in resp.text


def test_blacklist_get_shows_no_tracks_message_when_empty(client):
    seed_auth(client)
    resp = client.get('/actions/blacklist')
    assert 'No tracks in blacklist' in resp.text


def test_blacklist_post_add_track(client, tmp_path):
    from playlist_generator.blacklist import BlacklistManager
    from playlist_generator.dependencies import get_blacklist_manager
    from playlist_generator.main import app

    bl = BlacklistManager(data_dir=str(tmp_path))
    app.dependency_overrides[get_blacklist_manager] = lambda: bl

    seed_auth(client)
    resp = client.post('/actions/blacklist', data={'add_track': 'track_id_999'}, follow_redirects=True)
    assert resp.status_code == 200
    assert 'track_id_999' in resp.text
    assert 'track_id_999' in bl.get_tracks()

    app.dependency_overrides.pop(get_blacklist_manager, None)


def test_blacklist_post_delete_track(client, tmp_path):
    from playlist_generator.blacklist import BlacklistManager
    from playlist_generator.dependencies import get_blacklist_manager
    from playlist_generator.main import app

    bl = BlacklistManager(data_dir=str(tmp_path))
    bl.add_track('to_delete')
    app.dependency_overrides[get_blacklist_manager] = lambda: bl

    seed_auth(client)
    resp = client.post('/actions/blacklist', data={'delete_track': 'to_delete'}, follow_redirects=True)
    assert resp.status_code == 200
    assert 'to_delete' not in bl.get_tracks()

    app.dependency_overrides.pop(get_blacklist_manager, None)


def test_blacklist_post_empty_add_is_ignored(client):
    seed_auth(client)
    resp = client.post('/actions/blacklist', data={'add_track': ''}, follow_redirects=True)
    # Form has required attribute; if it gets past it, should still work
    assert resp.status_code in (200, 422)
