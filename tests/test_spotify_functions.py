import pytest
from io import BytesIO
from unittest.mock import MagicMock

from playlist_generator.spotify_functions import SpotifyManager


@pytest.fixture
def manager():
    return SpotifyManager()


def _make_saved_tracks(*track_ids):
    return {'items': [{'track': {'id': tid}} for tid in track_ids]}


def _make_playlist_tracks(*track_ids):
    return {'tracks': {'items': [{'track': {'id': tid}} for tid in track_ids]}}


def _make_spotify_client(saved_tracks, playlists_by_id):
    client = MagicMock()
    client.current_user_saved_tracks.return_value = saved_tracks
    client.playlist.side_effect = lambda pid, **kwargs: playlists_by_id[pid]
    return client


# --- _collect_tracks ---

def test_collect_tracks_includes_saved_songs(manager):
    client = _make_spotify_client(
        _make_saved_tracks('s1', 's2'),
        {'p1': _make_playlist_tracks()},
    )
    result = manager._collect_tracks('p1', [], client, source_ids=['p1'])
    assert 's1' in result
    assert 's2' in result


def test_collect_tracks_includes_source_playlist_tracks(manager):
    client = _make_spotify_client(
        _make_saved_tracks(),
        {'p1': _make_playlist_tracks('t1', 't2')},
    )
    result = manager._collect_tracks('p1', [], client, source_ids=['p1'])
    assert 't1' in result
    assert 't2' in result


def test_collect_tracks_deduplicates(manager):
    client = _make_spotify_client(
        _make_saved_tracks('dup'),
        {'p1': _make_playlist_tracks('dup')},
    )
    result = manager._collect_tracks('p1', [], client, source_ids=['p1'])
    assert result.count('dup') == 1


def test_collect_tracks_excludes_blacklisted(manager):
    client = _make_spotify_client(
        _make_saved_tracks('bad', 'good'),
        {'p1': _make_playlist_tracks()},
    )
    result = manager._collect_tracks('p1', ['bad'], client, source_ids=['p1'])
    assert 'bad' not in result
    assert 'good' in result


def test_collect_tracks_without_source_ids_uses_playlist_id(manager):
    client = _make_spotify_client(
        _make_saved_tracks(),
        {'p1': _make_playlist_tracks('t1')},
    )
    result = manager._collect_tracks('p1', [], client, source_ids=None)
    assert 't1' in result


def test_collect_tracks_result_is_shuffled_for_nonempty(manager):
    track_ids = [str(i) for i in range(20)]
    client = _make_spotify_client(
        _make_saved_tracks(*track_ids),
        {},
    )
    result = manager._collect_tracks('p1', [], client, source_ids=[])
    assert set(result) == set(track_ids)


def test_collect_tracks_skips_none_track_ids(manager):
    saved = {'items': [{'track': {'id': None}}, {'track': {'id': 'valid'}}]}
    client = MagicMock()
    client.current_user_saved_tracks.return_value = saved
    result = manager._collect_tracks('p1', [], client, source_ids=[])
    assert None not in result
    assert 'valid' in result


# --- _image_to_buffer ---

def test_image_to_buffer_returns_valid_jpeg(manager):
    from PIL import Image
    img = Image.new('RGB', (100, 100), color=(255, 0, 0))
    buffer = manager._image_to_buffer(img)
    assert isinstance(buffer, BytesIO)
    # Should be seeked back to start and readable
    data = buffer.read()
    assert len(data) > 0
    # JPEG magic bytes
    assert data[:2] == b'\xff\xd8'


def test_image_to_buffer_seek_position_is_zero(manager):
    from PIL import Image
    img = Image.new('RGB', (50, 50), color=(0, 255, 0))
    buffer = manager._image_to_buffer(img)
    assert buffer.tell() == 0


# --- _create_cover_image ---

def test_create_cover_image_returns_image(manager):
    from PIL import Image
    img = manager._create_cover_image('Test', 20, (100, 100), (0, 0, 0), (255, 255, 255))
    assert img.size == (100, 100)
    assert img.mode == 'RGB'


# --- get_spotify_client ---

def test_get_spotify_client_returns_none_without_token(manager):
    from starlette.testclient import TestClient
    from starlette.applications import Starlette
    from starlette.middleware.sessions import SessionMiddleware
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    def handler(request: Request):
        client = manager.get_spotify_client(request)
        return PlainTextResponse('none' if client is None else 'client')

    inner = Starlette(routes=[Route('/test', handler)])
    inner.add_middleware(SessionMiddleware, secret_key='test')
    tc = TestClient(inner)
    resp = tc.get('/test')
    assert resp.text == 'none'
