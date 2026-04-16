from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.user import User
from playlist_generator.services import base_list


def test_extract_track_id_from_url():
    url = "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh?si=abc123"
    assert base_list.extract_track_id(url) == "4iV5W9uYEdYUVa79Axb7Rh"


def test_extract_track_id_raw():
    assert base_list.extract_track_id("  4iV5W9uYEdYUVa79Axb7Rh  ") == "4iV5W9uYEdYUVa79Axb7Rh"


def test_extract_playlist_id_from_url():
    url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=xyz"
    assert base_list.extract_playlist_id(url) == "37i9dQZF1DXcBWIGoYBM5M"


def test_extract_playlist_id_raw():
    assert base_list.extract_playlist_id("37i9dQZF1DXcBWIGoYBM5M") == "37i9dQZF1DXcBWIGoYBM5M"


@pytest.mark.asyncio
async def test_add_track(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()
    mock_spotify.track.return_value = {
        "name": "Bohemian Rhapsody",
        "artists": [{"name": "Queen"}],
        "duration_ms": 354000,
        "album": {"images": [{"url": "https://img.spotify.com/album.jpg"}]},
    }

    with patch("playlist_generator.services.base_list.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value=mock_spotify.track.return_value)

        track = await base_list.add_track(
            sample_user.id, "4iV5W9uYEdYUVa79Axb7Rh", mock_spotify, db_session
        )

    assert track is not None
    assert track.track_name == "Bohemian Rhapsody"
    assert track.artist_name == "Queen"
    assert track.duration_ms == 354000


@pytest.mark.asyncio
async def test_add_track_duplicate(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()
    mock_spotify.track.return_value = {"name": "Track", "artists": [], "album": {}}

    with patch("playlist_generator.services.base_list.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value=mock_spotify.track.return_value)

        first = await base_list.add_track(
            sample_user.id, "same_track", mock_spotify, db_session
        )
        second = await base_list.add_track(
            sample_user.id, "same_track", mock_spotify, db_session
        )

    assert first is not None
    assert second is None  # Duplicate


@pytest.mark.asyncio
async def test_delete_track(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()
    mock_spotify.track.return_value = {"name": "Track", "artists": [], "album": {}}

    with patch("playlist_generator.services.base_list.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value=mock_spotify.track.return_value)
        track = await base_list.add_track(
            sample_user.id, "track_to_delete", mock_spotify, db_session
        )

    assert track is not None
    deleted = await base_list.delete_track(sample_user.id, track.id, db_session)
    assert deleted is True

    tracks = await base_list.get_tracks(sample_user.id, db_session)
    assert len(tracks) == 0


@pytest.mark.asyncio
async def test_delete_track_wrong_user(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()
    mock_spotify.track.return_value = {"name": "Track", "artists": [], "album": {}}

    with patch("playlist_generator.services.base_list.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value=mock_spotify.track.return_value)
        track = await base_list.add_track(
            sample_user.id, "track123", mock_spotify, db_session
        )

    assert track is not None
    deleted = await base_list.delete_track("other_user_id", track.id, db_session)
    assert deleted is False


@pytest.mark.asyncio
async def test_add_and_get_playlists(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()

    with patch("playlist_generator.services.base_list.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value={
            "name": "Top Hits", "tracks": {"total": 50}, "images": []
        })
        playlist = await base_list.add_playlist(
            sample_user.id, "37i9dQZF1DXcBWIGoYBM5M", mock_spotify, db_session
        )

    assert playlist is not None
    assert playlist.playlist_name == "Top Hits"
    assert playlist.track_count == 50

    playlists = await base_list.get_playlists(sample_user.id, db_session)
    assert len(playlists) == 1
