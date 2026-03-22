from playlist_generator.dependencies import get_blacklist_manager, get_playlist_manager, get_spotify_manager
from playlist_generator.blacklist import BlacklistManager
from playlist_generator.playlists import PlaylistManager
from playlist_generator.spotify_functions import SpotifyManager


def test_get_blacklist_manager_returns_instance():
    assert isinstance(get_blacklist_manager(), BlacklistManager)


def test_get_playlist_manager_returns_instance():
    assert isinstance(get_playlist_manager(), PlaylistManager)


def test_get_spotify_manager_returns_instance():
    assert isinstance(get_spotify_manager(), SpotifyManager)
