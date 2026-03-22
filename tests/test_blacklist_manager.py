import json
import os
import pytest

from playlist_generator.blacklist import BlacklistManager


def test_auto_creates_file_and_directory(tmp_path):
    bm = BlacklistManager(data_dir=str(tmp_path / 'new_dir'))
    assert os.path.exists(bm.filepath)
    assert json.load(open(bm.filepath)) == {'tracks': []}


def test_get_tracks_returns_empty_on_new_file(tmp_blacklist):
    assert tmp_blacklist.get_tracks() == []


def test_add_track(tmp_blacklist):
    result = tmp_blacklist.add_track('abc123')
    assert 'abc123' in result


def test_add_track_strips_whitespace(tmp_blacklist):
    result = tmp_blacklist.add_track('  abc123  ')
    assert 'abc123' in result


def test_add_track_deduplicates(tmp_blacklist):
    tmp_blacklist.add_track('abc123')
    result = tmp_blacklist.add_track('abc123')
    assert result.count('abc123') == 1


def test_add_empty_track_is_ignored(tmp_blacklist):
    result = tmp_blacklist.add_track('   ')
    assert result == []


def test_delete_track(tmp_blacklist):
    tmp_blacklist.add_track('abc123')
    result = tmp_blacklist.delete_track('abc123')
    assert 'abc123' not in result


def test_delete_nonexistent_track_is_safe(tmp_blacklist):
    result = tmp_blacklist.delete_track('does_not_exist')
    assert result == []


def test_add_multiple_tracks(tmp_blacklist):
    result = tmp_blacklist.add_tracks(['t1', 't2', 't3'])
    assert set(result) == {'t1', 't2', 't3'}


def test_add_tracks_deduplicates(tmp_blacklist):
    tmp_blacklist.add_track('t1')
    result = tmp_blacklist.add_tracks(['t1', 't2'])
    assert result.count('t1') == 1
    assert 't2' in result


def test_add_tracks_strips_empty_strings(tmp_blacklist):
    result = tmp_blacklist.add_tracks(['t1', '', '  ', 't2'])
    assert '' not in result
    assert '  ' not in result


def test_get_tracks_persists_across_instances(tmp_path):
    bm1 = BlacklistManager(data_dir=str(tmp_path))
    bm1.add_track('persistent')
    bm2 = BlacklistManager(data_dir=str(tmp_path))
    assert 'persistent' in bm2.get_tracks()
