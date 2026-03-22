import json
import os
import pytest

from playlist_generator.playlists import PlaylistManager, extract_playlist_id


# --- extract_playlist_id ---

def test_extract_from_full_url():
    url = 'https://open.spotify.com/playlist/2GEXzPeksIINQMTivWQ2el?si=abc123'
    assert extract_playlist_id(url) == '2GEXzPeksIINQMTivWQ2el'


def test_extract_from_url_without_query():
    url = 'https://open.spotify.com/playlist/2GEXzPeksIINQMTivWQ2el'
    assert extract_playlist_id(url) == '2GEXzPeksIINQMTivWQ2el'


def test_extract_raw_id_passthrough():
    assert extract_playlist_id('2GEXzPeksIINQMTivWQ2el') == '2GEXzPeksIINQMTivWQ2el'


def test_extract_strips_whitespace():
    assert extract_playlist_id('  abc123  ') == 'abc123'


# --- PlaylistManager ---

def test_auto_creates_file_and_directory(tmp_path):
    pm = PlaylistManager(data_dir=str(tmp_path / 'new_dir'))
    assert os.path.exists(pm.filepath)
    data = json.load(open(pm.filepath))
    assert data == {'target': '', 'sources': []}


def test_get_data_returns_defaults(tmp_playlists):
    data = tmp_playlists.get_data()
    assert data['target'] == ''
    assert data['sources'] == []


def test_get_target_empty_by_default(tmp_playlists):
    assert tmp_playlists.get_target() == ''


def test_get_sources_empty_by_default(tmp_playlists):
    assert tmp_playlists.get_sources() == []


def test_add_source(tmp_playlists):
    data = tmp_playlists.add_source('abc123', 'My Playlist')
    sources = data['sources']
    assert len(sources) == 1
    assert sources[0] == {'id': 'abc123', 'name': 'My Playlist'}


def test_add_source_deduplicates(tmp_playlists):
    tmp_playlists.add_source('abc123', 'My Playlist')
    data = tmp_playlists.add_source('abc123', 'Duplicate')
    assert len(data['sources']) == 1


def test_add_source_uses_id_when_name_empty(tmp_playlists):
    data = tmp_playlists.add_source('abc123', '')
    assert data['sources'][0]['name'] == 'abc123'


def test_delete_source(tmp_playlists):
    tmp_playlists.add_source('abc123', 'My Playlist')
    data = tmp_playlists.delete_source('abc123')
    assert data['sources'] == []


def test_delete_source_clears_target_if_was_target(tmp_playlists):
    tmp_playlists.add_source('abc123', 'My Playlist')
    tmp_playlists.set_target('abc123')
    data = tmp_playlists.delete_source('abc123')
    assert data['target'] == ''


def test_delete_nonexistent_source_is_safe(tmp_playlists):
    data = tmp_playlists.delete_source('does_not_exist')
    assert data['sources'] == []


def test_set_target(tmp_playlists):
    tmp_playlists.add_source('abc123', 'My Playlist')
    data = tmp_playlists.set_target('abc123')
    assert data['target'] == 'abc123'


def test_set_target_persists(tmp_path):
    pm1 = PlaylistManager(data_dir=str(tmp_path))
    pm1.add_source('abc123', 'P')
    pm1.set_target('abc123')
    pm2 = PlaylistManager(data_dir=str(tmp_path))
    assert pm2.get_target() == 'abc123'


def test_multiple_sources(tmp_playlists):
    tmp_playlists.add_source('id1', 'Playlist 1')
    tmp_playlists.add_source('id2', 'Playlist 2')
    sources = tmp_playlists.get_sources()
    assert len(sources) == 2
    assert sources[0]['id'] == 'id1'
    assert sources[1]['id'] == 'id2'
