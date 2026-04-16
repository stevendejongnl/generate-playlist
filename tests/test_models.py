import time

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.encryption import encrypt
from playlist_generator.models import (
    User,
    BaseTrack,
    BasePlaylist,
    BlacklistTrack,
    BlacklistPlaylist,
    TargetPlaylist,
    CoverImageConfig,
    GenerationHistory,
)


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    user = User(
        spotify_user_id="user123",
        display_name="Test",
        access_token=encrypt("tok"),
        refresh_token=encrypt("ref"),
        token_expires_at=time.time() + 3600,
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.spotify_user_id == "user123"))
    fetched = result.scalar_one()
    assert fetched.display_name == "Test"
    assert fetched.id is not None
    assert len(fetched.id) == 36  # UUID format


@pytest.mark.asyncio
async def test_user_spotify_id_unique(db_session: AsyncSession):
    for i in range(2):
        user = User(
            spotify_user_id="duplicate_user",
            access_token=encrypt("tok"),
            refresh_token=encrypt("ref"),
            token_expires_at=time.time(),
        )
        db_session.add(user)

    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_base_track(db_session: AsyncSession, sample_user: User):
    track = BaseTrack(
        user_id=sample_user.id,
        spotify_track_id="4iV5W9uYEdYUVa79Axb7Rh",
        track_name="Bohemian Rhapsody",
        artist_name="Queen",
        duration_ms=354000,
    )
    db_session.add(track)
    await db_session.commit()

    result = await db_session.execute(
        select(BaseTrack).where(BaseTrack.user_id == sample_user.id)
    )
    fetched = result.scalar_one()
    assert fetched.track_name == "Bohemian Rhapsody"
    assert fetched.duration_ms == 354000


@pytest.mark.asyncio
async def test_base_track_unique_per_user(db_session: AsyncSession, sample_user: User):
    for _ in range(2):
        db_session.add(
            BaseTrack(
                user_id=sample_user.id,
                spotify_track_id="same_track",
                track_name="Duplicate",
            )
        )
    with pytest.raises(Exception):
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_base_playlist(db_session: AsyncSession, sample_user: User):
    playlist = BasePlaylist(
        user_id=sample_user.id,
        spotify_playlist_id="37i9dQZF1DXcBWIGoYBM5M",
        playlist_name="Today's Top Hits",
        track_count=50,
    )
    db_session.add(playlist)
    await db_session.commit()

    result = await db_session.execute(
        select(BasePlaylist).where(BasePlaylist.user_id == sample_user.id)
    )
    assert result.scalar_one().playlist_name == "Today's Top Hits"


@pytest.mark.asyncio
async def test_create_blacklist_track(db_session: AsyncSession, sample_user: User):
    track = BlacklistTrack(
        user_id=sample_user.id,
        spotify_track_id="blocked_track_123",
        track_name="Annoying Song",
    )
    db_session.add(track)
    await db_session.commit()

    result = await db_session.execute(
        select(BlacklistTrack).where(BlacklistTrack.user_id == sample_user.id)
    )
    assert result.scalar_one().track_name == "Annoying Song"


@pytest.mark.asyncio
async def test_create_blacklist_playlist(db_session: AsyncSession, sample_user: User):
    playlist = BlacklistPlaylist(
        user_id=sample_user.id,
        spotify_playlist_id="blocked_playlist_456",
        playlist_name="Bad Vibes Playlist",
    )
    db_session.add(playlist)
    await db_session.commit()

    result = await db_session.execute(
        select(BlacklistPlaylist).where(BlacklistPlaylist.user_id == sample_user.id)
    )
    assert result.scalar_one().playlist_name == "Bad Vibes Playlist"


@pytest.mark.asyncio
async def test_create_target_playlist(db_session: AsyncSession, sample_user: User):
    target = TargetPlaylist(
        user_id=sample_user.id,
        spotify_playlist_id="target_pl_789",
        playlist_name="My Generated Playlist",
        is_default=1,
    )
    db_session.add(target)
    await db_session.commit()

    result = await db_session.execute(
        select(TargetPlaylist).where(TargetPlaylist.user_id == sample_user.id)
    )
    fetched = result.scalar_one()
    assert fetched.is_default == 1
    assert fetched.playlist_name == "My Generated Playlist"


@pytest.mark.asyncio
async def test_create_cover_image_config(db_session: AsyncSession, sample_user: User):
    config = CoverImageConfig(
        user_id=sample_user.id,
        name="Chill Vibes",
        text="Chill Vibes",
        bg_color="#1a1a2e",
        text_color="#e94560",
        font_size=100,
    )
    db_session.add(config)
    await db_session.commit()

    result = await db_session.execute(
        select(CoverImageConfig).where(CoverImageConfig.user_id == sample_user.id)
    )
    fetched = result.scalar_one()
    assert fetched.name == "Chill Vibes"
    assert fetched.bg_color == "#1a1a2e"


@pytest.mark.asyncio
async def test_create_generation_history(db_session: AsyncSession, sample_user: User):
    history = GenerationHistory(
        user_id=sample_user.id,
        target_playlist_id="target_123",
        target_playlist_name="My Playlist",
        track_count=85,
        total_duration_ms=18000000,
        discovery_count=15,
        max_tracks_param=100,
        max_minutes_param=300,
        discovery_mode="percentage",
        discovery_value=20.0,
    )
    db_session.add(history)
    await db_session.commit()

    result = await db_session.execute(
        select(GenerationHistory).where(GenerationHistory.user_id == sample_user.id)
    )
    fetched = result.scalar_one()
    assert fetched.track_count == 85
    assert fetched.discovery_mode == "percentage"
    assert fetched.discovery_value == 20.0


@pytest.mark.asyncio
async def test_cascade_delete_user(db_session: AsyncSession, sample_user: User):
    """Deleting a user should cascade delete all related records."""
    db_session.add(BaseTrack(
        user_id=sample_user.id,
        spotify_track_id="track1",
        track_name="Track 1",
    ))
    db_session.add(BlacklistTrack(
        user_id=sample_user.id,
        spotify_track_id="blocked1",
    ))
    db_session.add(TargetPlaylist(
        user_id=sample_user.id,
        spotify_playlist_id="target1",
    ))
    await db_session.commit()

    await db_session.delete(sample_user)
    await db_session.commit()

    for model in (BaseTrack, BlacklistTrack, TargetPlaylist):
        result = await db_session.execute(select(model))
        assert result.scalars().all() == []
