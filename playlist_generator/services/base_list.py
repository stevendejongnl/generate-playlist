import asyncio
import logging
import re

import spotipy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.base_list import BaseTrack, BasePlaylist

logger = logging.getLogger(__name__)

_SPOTIFY_TRACK_URL_RE = re.compile(
    r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)"
)
_SPOTIFY_PLAYLIST_URL_RE = re.compile(
    r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
)


def extract_track_id(value: str) -> str:
    """Extract a Spotify track ID from a URL or return the raw ID."""
    value = value.strip()
    match = _SPOTIFY_TRACK_URL_RE.match(value)
    return match.group(1) if match else value


def extract_playlist_id(value: str) -> str:
    """Extract a Spotify playlist ID from a URL or return the raw ID."""
    value = value.strip()
    match = _SPOTIFY_PLAYLIST_URL_RE.match(value)
    return match.group(1) if match else value


async def get_tracks(user_id: str, db: AsyncSession) -> list[BaseTrack]:
    result = await db.execute(
        select(BaseTrack)
        .where(BaseTrack.user_id == user_id)
        .order_by(BaseTrack.added_at.desc())
    )
    return list(result.scalars().all())


async def add_track(
    user_id: str, raw_input: str, spotify: spotipy.Spotify, db: AsyncSession
) -> BaseTrack | None:
    """Add a track to the user's base list. Returns None if duplicate."""
    track_id = extract_track_id(raw_input)
    if not track_id:
        return None

    # Check for duplicate
    existing = await db.execute(
        select(BaseTrack).where(
            BaseTrack.user_id == user_id,
            BaseTrack.spotify_track_id == track_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    # Fetch metadata from Spotify
    try:
        track_data = await asyncio.to_thread(spotify.track, track_id)
        track_name = track_data.get("name", "")
        artists = track_data.get("artists", [])
        artist_name = ", ".join(a["name"] for a in artists) if artists else ""
        duration_ms = track_data.get("duration_ms")
        images = track_data.get("album", {}).get("images", [])
        album_image_url = images[0]["url"] if images else None
    except Exception:
        logger.warning("Could not fetch track metadata for %s", track_id)
        track_name = None
        artist_name = None
        duration_ms = None
        album_image_url = None

    track = BaseTrack(
        user_id=user_id,
        spotify_track_id=track_id,
        track_name=track_name,
        artist_name=artist_name,
        duration_ms=duration_ms,
        album_image_url=album_image_url,
    )
    db.add(track)
    await db.commit()
    await db.refresh(track)
    return track


async def delete_track(user_id: str, track_db_id: str, db: AsyncSession) -> bool:
    track = await db.get(BaseTrack, track_db_id)
    if not track or track.user_id != user_id:
        return False
    await db.delete(track)
    await db.commit()
    return True


async def get_playlists(user_id: str, db: AsyncSession) -> list[BasePlaylist]:
    result = await db.execute(
        select(BasePlaylist)
        .where(BasePlaylist.user_id == user_id)
        .order_by(BasePlaylist.added_at.desc())
    )
    return list(result.scalars().all())


async def add_playlist(
    user_id: str, raw_input: str, spotify: spotipy.Spotify, db: AsyncSession
) -> BasePlaylist | None:
    """Add a playlist to the user's base list. Returns None if duplicate."""
    playlist_id = extract_playlist_id(raw_input)
    if not playlist_id:
        return None

    existing = await db.execute(
        select(BasePlaylist).where(
            BasePlaylist.user_id == user_id,
            BasePlaylist.spotify_playlist_id == playlist_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    try:
        pl_data = await asyncio.to_thread(
            spotify.playlist, playlist_id, fields="name,tracks.total,images"
        )
        playlist_name = pl_data.get("name", "")
        track_count = pl_data.get("tracks", {}).get("total")
        images = pl_data.get("images", [])
        image_url = images[0]["url"] if images else None
    except Exception:
        logger.warning("Could not fetch playlist metadata for %s", playlist_id)
        playlist_name = None
        track_count = None
        image_url = None

    playlist = BasePlaylist(
        user_id=user_id,
        spotify_playlist_id=playlist_id,
        playlist_name=playlist_name,
        track_count=track_count,
        image_url=image_url,
    )
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return playlist


async def delete_playlist(user_id: str, playlist_db_id: str, db: AsyncSession) -> bool:
    playlist = await db.get(BasePlaylist, playlist_db_id)
    if not playlist or playlist.user_id != user_id:
        return False
    await db.delete(playlist)
    await db.commit()
    return True
