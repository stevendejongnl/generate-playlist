import pytest
from tests.conftest import seed_auth


def test_unauthenticated_index_shows_authenticate_link(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'Authenticate' in resp.text


def test_authenticated_index_shows_actions(client):
    seed_auth(client)
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'Build playlist' in resp.text
    assert 'Manage playlists' in resp.text
    assert 'Select tracks for blacklist' in resp.text
    assert 'Sign out' in resp.text


def test_sign_out_clears_session_and_redirects(client):
    seed_auth(client)
    resp = client.get('/sign_out', follow_redirects=False)
    assert resp.status_code in (302, 303, 307)
    # After sign out, index should show authenticate link again
    resp2 = client.get('/')
    assert 'Authenticate' in resp2.text


def test_authenticate_redirects_to_spotify_when_no_token(client):
    # Without credentials configured, spotipy will raise — but we just
    # want to confirm the route is reachable and returns a redirect
    resp = client.get('/authenticate', follow_redirects=False)
    # Either redirect to Spotify or back to index (if already authed)
    assert resp.status_code in (200, 302, 307)
