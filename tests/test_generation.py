from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.base_list import BaseTrack, BasePlaylist
from playlist_generator.models.blacklist import BlacklistTrack, BlacklistPlaylist
from playlist_generator.models.user import User
from playlist_generator.services import generation as gen
from playlist_generator.services.generation import TrackInfo, _apply_limits


# ── Unit tests for _apply_limits ─────────────────────

def test_apply_limits_no_limits():
    tracks = [TrackInfo(f"t{i}", f"Track {i}", "Artist", 180_000) for i in range(10)]
    result = _apply_limits(tracks, None, None)
    assert len(result) == 10


def test_apply_limits_max_tracks():
    tracks = [TrackInfo(f"t{i}", f"Track {i}", "Artist", 180_000) for i in range(10)]
    result = _apply_limits(tracks, 5, None)
    assert len(result) == 5


def test_apply_limits_max_minutes():
    tracks = [TrackInfo(f"t{i}", f"Track {i}", "Artist", 180_000) for i in range(10)]
    # 3 minutes each, max 10 minutes = 3 tracks (9 min), 4th would exceed
    result = _apply_limits(tracks, None, 10)
    assert len(result) == 3


def test_apply_limits_both_limits_tracks_first():
    tracks = [TrackInfo(f"t{i}", f"Track {i}", "Artist", 60_000) for i in range(100)]
    # max 5 tracks (5 min) or 60 min — tracks limit hit first
    result = _apply_limits(tracks, 5, 60)
    assert len(result) == 5


def test_apply_limits_both_limits_minutes_first():
    tracks = [TrackInfo(f"t{i}", f"Track {i}", "Artist", 300_000) for i in range(100)]
    # 5 min each, max 100 tracks or 12 min — minutes limit hit first (2 tracks = 10 min)
    result = _apply_limits(tracks, 100, 12)
    assert len(result) == 2


def test_apply_limits_empty():
    result = _apply_limits([], 10, 60)
    assert result == []


# ── Integration tests for the generation pipeline ────

@pytest.mark.asyncio
async def test_preview_basic(db_session: AsyncSession, sample_user: User):
    """Preview with base tracks, no discovery, no limits."""
    # Add base tracks to DB
    for i in range(5):
        db_session.add(BaseTrack(
            user_id=sample_user.id,
            spotify_track_id=f"track_{i}",
            track_name=f"Track {i}",
            artist_name="Artist",
            duration_ms=200_000,
        ))
    await db_session.commit()

    mock_spotify = MagicMock()

    with patch.object(gen, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock()

        result = await gen.preview(
            user_id=sample_user.id,
            spotify=mock_spotify,
            db=db_session,
        )

    assert len(result.tracks) == 5
    assert result.discovery_count == 0
    assert result.total_duration_ms == 1_000_000


@pytest.mark.asyncio
async def test_preview_filters_blacklisted(db_session: AsyncSession, sample_user: User):
    """Blacklisted tracks should be excluded from the result."""
    for i in range(5):
        db_session.add(BaseTrack(
            user_id=sample_user.id,
            spotify_track_id=f"track_{i}",
            track_name=f"Track {i}",
            duration_ms=180_000,
        ))
    # Blacklist 2 of them
    db_session.add(BlacklistTrack(
        user_id=sample_user.id, spotify_track_id="track_1"
    ))
    db_session.add(BlacklistTrack(
        user_id=sample_user.id, spotify_track_id="track_3"
    ))
    await db_session.commit()

    mock_spotify = MagicMock()

    with patch.object(gen, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock()

        result = await gen.preview(
            user_id=sample_user.id,
            spotify=mock_spotify,
            db=db_session,
        )

    assert len(result.tracks) == 3
    track_ids = {t.spotify_id for t in result.tracks}
    assert "track_1" not in track_ids
    assert "track_3" not in track_ids


@pytest.mark.asyncio
async def test_preview_with_max_tracks(db_session: AsyncSession, sample_user: User):
    for i in range(10):
        db_session.add(BaseTrack(
            user_id=sample_user.id,
            spotify_track_id=f"track_{i}",
            duration_ms=200_000,
        ))
    await db_session.commit()

    mock_spotify = MagicMock()

    with patch.object(gen, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock()

        result = await gen.preview(
            user_id=sample_user.id,
            spotify=mock_spotify,
            db=db_session,
            max_tracks=3,
        )

    assert len(result.tracks) == 3


@pytest.mark.asyncio
async def test_preview_with_discovery(db_session: AsyncSession, sample_user: User):
    """Discovery should add recommended tracks."""
    for i in range(5):
        db_session.add(BaseTrack(
            user_id=sample_user.id,
            spotify_track_id=f"track_{i}",
            track_name=f"Track {i}",
            duration_ms=200_000,
        ))
    await db_session.commit()

    mock_spotify = MagicMock()
    recommendation_result = {
        "tracks": [
            {"id": f"rec_{i}", "name": f"Rec {i}", "artists": [{"name": "DJ"}], "duration_ms": 180_000}
            for i in range(3)
        ]
    }

    call_count = 0

    async def mock_to_thread(fn, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if fn == mock_spotify.recommendations:
            return recommendation_result
        # For _fetch_playlist_tracks calls — not applicable here
        return {"items": [], "next": None}

    with patch.object(gen, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = mock_to_thread

        result = await gen.preview(
            user_id=sample_user.id,
            spotify=mock_spotify,
            db=db_session,
            discovery_mode="fixed",
            discovery_value=3,
        )

    # Should have base (5) + discovery (3) = 8 tracks
    assert len(result.tracks) == 8
    assert result.discovery_count == 3


@pytest.mark.asyncio
async def test_preview_deduplicates(db_session: AsyncSession, sample_user: User):
    """Same track in base list and playlist should only appear once."""
    # Add a track directly
    db_session.add(BaseTrack(
        user_id=sample_user.id,
        spotify_track_id="shared_track",
        track_name="Shared",
        duration_ms=180_000,
    ))
    # Add a playlist that also contains "shared_track"
    db_session.add(BasePlaylist(
        user_id=sample_user.id,
        spotify_playlist_id="pl_with_shared",
        playlist_name="Has Shared",
    ))
    await db_session.commit()

    mock_spotify = MagicMock()

    async def mock_to_thread(fn, *args, **kwargs):
        # Return playlist_tracks response with the same track
        return {
            "items": [
                {"track": {"id": "shared_track", "name": "Shared", "artists": [], "duration_ms": 180_000}},
                {"track": {"id": "unique_track", "name": "Unique", "artists": [], "duration_ms": 200_000}},
            ],
            "next": None,
        }

    with patch.object(gen, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = mock_to_thread

        result = await gen.preview(
            user_id=sample_user.id,
            spotify=mock_spotify,
            db=db_session,
        )

    # shared_track appears once (from base), unique_track from playlist
    assert len(result.tracks) == 2
    track_ids = {t.spotify_id for t in result.tracks}
    assert "shared_track" in track_ids
    assert "unique_track" in track_ids


@pytest.mark.asyncio
async def test_preview_empty_base_list(db_session: AsyncSession, sample_user: User):
    """Empty base list should produce empty result."""
    mock_spotify = MagicMock()

    with patch.object(gen, "asyncio") as mock_asyncio:
        mock_asyncio.to_thread = AsyncMock()
        result = await gen.preview(
            user_id=sample_user.id,
            spotify=mock_spotify,
            db=db_session,
        )

    assert len(result.tracks) == 0
    assert result.total_duration_ms == 0
