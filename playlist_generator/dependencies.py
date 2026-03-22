from playlist_generator.blacklist import BlacklistManager
from playlist_generator.playlists import PlaylistManager
from playlist_generator.spotify_functions import SpotifyManager


def get_blacklist_manager() -> BlacklistManager:
    return BlacklistManager()


def get_playlist_manager() -> PlaylistManager:
    return PlaylistManager()


def get_spotify_manager() -> SpotifyManager:
    return SpotifyManager()
