from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.user import User
from playlist_generator.services import blacklist


@pytest.mark.asyncio
async def test_add_and_get_blacklist_track(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()

    with patch("playlist_generator.services.blacklist.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value={
            "name": "Bad Song", "artists": [{"name": "Bad Artist"}]
        })
        track = await blacklist.add_track(
            sample_user.id, "blocked_id", mock_spotify, db_session
        )

    assert track is not None
    assert track.track_name == "Bad Song"

    tracks = await blacklist.get_tracks(sample_user.id, db_session)
    assert len(tracks) == 1


@pytest.mark.asyncio
async def test_add_blacklist_track_duplicate(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()

    with patch("playlist_generator.services.blacklist.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value={
            "name": "Song", "artists": []
        })
        first = await blacklist.add_track(
            sample_user.id, "dup_track", mock_spotify, db_session
        )
        second = await blacklist.add_track(
            sample_user.id, "dup_track", mock_spotify, db_session
        )

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_delete_blacklist_track(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()

    with patch("playlist_generator.services.blacklist.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value={
            "name": "Song", "artists": []
        })
        track = await blacklist.add_track(
            sample_user.id, "to_delete", mock_spotify, db_session
        )

    assert track is not None
    deleted = await blacklist.delete_track(sample_user.id, track.id, db_session)
    assert deleted is True

    tracks = await blacklist.get_tracks(sample_user.id, db_session)
    assert len(tracks) == 0


@pytest.mark.asyncio
async def test_add_and_get_blacklist_playlist(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()

    with patch("playlist_generator.services.blacklist.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value={"name": "Bad Vibes"})
        playlist = await blacklist.add_playlist(
            sample_user.id, "blocked_pl", mock_spotify, db_session
        )

    assert playlist is not None
    assert playlist.playlist_name == "Bad Vibes"

    playlists = await blacklist.get_playlists(sample_user.id, db_session)
    assert len(playlists) == 1


@pytest.mark.asyncio
async def test_delete_blacklist_playlist(db_session: AsyncSession, sample_user: User):
    mock_spotify = MagicMock()

    with patch("playlist_generator.services.blacklist.asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock(return_value={"name": "Playlist"})
        playlist = await blacklist.add_playlist(
            sample_user.id, "pl_delete", mock_spotify, db_session
        )

    assert playlist is not None
    deleted = await blacklist.delete_playlist(sample_user.id, playlist.id, db_session)
    assert deleted is True

    playlists = await blacklist.get_playlists(sample_user.id, db_session)
    assert len(playlists) == 0
