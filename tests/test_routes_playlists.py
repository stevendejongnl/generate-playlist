import pytest
from tests.conftest import seed_auth
from playlist_generator.playlists import PlaylistManager
from playlist_generator.dependencies import get_playlist_manager
from playlist_generator.main import app


def _override_playlists(tmp_path):
    pl = PlaylistManager(data_dir=str(tmp_path))
    app.dependency_overrides[get_playlist_manager] = lambda: pl
    return pl


def test_playlists_get_requires_auth(client):
    resp = client.get('/actions/playlists', follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_playlists_get_renders_page(client):
    seed_auth(client)
    resp = client.get('/actions/playlists')
    assert resp.status_code == 200
    assert 'Manage Playlists' in resp.text


def test_playlists_get_shows_empty_message(client):
    seed_auth(client)
    resp = client.get('/actions/playlists')
    assert 'No playlists added yet' in resp.text


def test_playlists_post_add_raw_id(client, tmp_path):
    pl = _override_playlists(tmp_path)
    seed_auth(client)
    resp = client.post('/actions/playlists', data={'add_source': 'myplaylistid'}, follow_redirects=True)
    assert resp.status_code == 200
    sources = pl.get_sources()
    assert any(s['id'] == 'myplaylistid' for s in sources)
    app.dependency_overrides.pop(get_playlist_manager, None)


def test_playlists_post_add_from_url(client, tmp_path):
    pl = _override_playlists(tmp_path)
    seed_auth(client)
    url = 'https://open.spotify.com/playlist/2GEXzPeksIINQMTivWQ2el?si=abc'
    resp = client.post('/actions/playlists', data={'add_source': url}, follow_redirects=True)
    assert resp.status_code == 200
    sources = pl.get_sources()
    assert any(s['id'] == '2GEXzPeksIINQMTivWQ2el' for s in sources)
    app.dependency_overrides.pop(get_playlist_manager, None)


def test_playlists_post_delete_source(client, tmp_path):
    pl = _override_playlists(tmp_path)
    pl.add_source('to_delete', 'Delete Me')
    seed_auth(client)
    resp = client.post('/actions/playlists', data={'delete_source': 'to_delete'}, follow_redirects=True)
    assert resp.status_code == 200
    assert not any(s['id'] == 'to_delete' for s in pl.get_sources())
    app.dependency_overrides.pop(get_playlist_manager, None)


def test_playlists_post_set_target(client, tmp_path):
    pl = _override_playlists(tmp_path)
    pl.add_source('tid1', 'Target Playlist')
    seed_auth(client)
    resp = client.post('/actions/playlists', data={'set_target': 'tid1'}, follow_redirects=True)
    assert resp.status_code == 200
    assert pl.get_target() == 'tid1'
    app.dependency_overrides.pop(get_playlist_manager, None)


def test_playlists_get_shows_target_badge(client, tmp_path):
    pl = _override_playlists(tmp_path)
    pl.add_source('tid1', 'My Target')
    pl.set_target('tid1')
    seed_auth(client)
    resp = client.get('/actions/playlists')
    assert '★ Target' in resp.text
    app.dependency_overrides.pop(get_playlist_manager, None)


def test_playlists_get_shows_set_target_button_for_non_target(client, tmp_path):
    pl = _override_playlists(tmp_path)
    pl.add_source('id1', 'Playlist 1')
    pl.add_source('id2', 'Playlist 2')
    pl.set_target('id1')
    seed_auth(client)
    resp = client.get('/actions/playlists')
    assert 'Set target' in resp.text
    app.dependency_overrides.pop(get_playlist_manager, None)


def test_playlists_post_requires_auth(client):
    resp = client.post('/actions/playlists', data={'add_source': 'x'}, follow_redirects=False)
    assert resp.status_code in (302, 307)
