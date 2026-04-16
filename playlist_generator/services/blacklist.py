import asyncio
import logging

import spotipy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.blacklist import BlacklistTrack, BlacklistPlaylist
from playlist_generator.services.base_list import extract_track_id, extract_playlist_id

logger = logging.getLogger(__name__)


async def get_tracks(user_id: str, db: AsyncSession) -> list[BlacklistTrack]:
    result = await db.execute(
        select(BlacklistTrack)
        .where(BlacklistTrack.user_id == user_id)
        .order_by(BlacklistTrack.added_at.desc())
    )
    return list(result.scalars().all())


async def add_track(
    user_id: str, raw_input: str, spotify: spotipy.Spotify, db: AsyncSession
) -> BlacklistTrack | None:
    track_id = extract_track_id(raw_input)
    if not track_id:
        return None

    existing = await db.execute(
        select(BlacklistTrack).where(
            BlacklistTrack.user_id == user_id,
            BlacklistTrack.spotify_track_id == track_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    try:
        track_data = await asyncio.to_thread(spotify.track, track_id)
        track_name = track_data.get("name", "")
        artists = track_data.get("artists", [])
        artist_name = ", ".join(a["name"] for a in artists) if artists else ""
    except Exception:
        logger.warning("Could not fetch track metadata for %s", track_id)
        track_name = None
        artist_name = None

    track = BlacklistTrack(
        user_id=user_id,
        spotify_track_id=track_id,
        track_name=track_name,
        artist_name=artist_name,
    )
    db.add(track)
    await db.commit()
    await db.refresh(track)
    return track


async def delete_track(user_id: str, track_db_id: str, db: AsyncSession) -> bool:
    track = await db.get(BlacklistTrack, track_db_id)
    if not track or track.user_id != user_id:
        return False
    await db.delete(track)
    await db.commit()
    return True


async def get_playlists(user_id: str, db: AsyncSession) -> list[BlacklistPlaylist]:
    result = await db.execute(
        select(BlacklistPlaylist)
        .where(BlacklistPlaylist.user_id == user_id)
        .order_by(BlacklistPlaylist.added_at.desc())
    )
    return list(result.scalars().all())


async def add_playlist(
    user_id: str, raw_input: str, spotify: spotipy.Spotify, db: AsyncSession
) -> BlacklistPlaylist | None:
    playlist_id = extract_playlist_id(raw_input)
    if not playlist_id:
        return None

    existing = await db.execute(
        select(BlacklistPlaylist).where(
            BlacklistPlaylist.user_id == user_id,
            BlacklistPlaylist.spotify_playlist_id == playlist_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    try:
        pl_data = await asyncio.to_thread(
            spotify.playlist, playlist_id, fields="name"
        )
        playlist_name = pl_data.get("name", "")
    except Exception:
        logger.warning("Could not fetch playlist metadata for %s", playlist_id)
        playlist_name = None

    playlist = BlacklistPlaylist(
        user_id=user_id,
        spotify_playlist_id=playlist_id,
        playlist_name=playlist_name,
    )
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return playlist


async def delete_playlist(user_id: str, playlist_db_id: str, db: AsyncSession) -> bool:
    playlist = await db.get(BlacklistPlaylist, playlist_db_id)
    if not playlist or playlist.user_id != user_id:
        return False
    await db.delete(playlist)
    await db.commit()
    return True
