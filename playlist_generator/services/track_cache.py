"""Track metadata cache — stores every track we see to avoid repeat API calls."""
import asyncio
import logging
import time

import spotipy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.track_cache import TrackCache

logger = logging.getLogger(__name__)

# Cache entries older than this are refreshed on next access
CACHE_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


async def get_cached(
    spotify_track_id: str, db: AsyncSession
) -> TrackCache | None:
    """Get a track from cache if it exists and is fresh."""
    result = await db.execute(
        select(TrackCache).where(TrackCache.spotify_track_id == spotify_track_id)
    )
    cached = result.scalar_one_or_none()
    if cached and (time.time() - cached.fetched_at) < CACHE_TTL_SECONDS:
        return cached
    return None


async def get_or_fetch(
    spotify_track_id: str, spotify: spotipy.Spotify, db: AsyncSession
) -> TrackCache:
    """Get track metadata from cache, or fetch from Spotify and cache it."""
    cached = await get_cached(spotify_track_id, db)
    if cached:
        return cached

    # Fetch from Spotify
    try:
        data = await asyncio.to_thread(spotify.track, spotify_track_id)
        artists = data.get("artists", [])
        images = data.get("album", {}).get("images", [])

        track = TrackCache(
            spotify_track_id=spotify_track_id,
            track_name=data.get("name"),
            artist_name=", ".join(a["name"] for a in artists) if artists else None,
            duration_ms=data.get("duration_ms"),
            album_image_url=images[0]["url"] if images else None,
        )
    except Exception:
        logger.warning("Failed to fetch track %s from Spotify", spotify_track_id)
        track = TrackCache(spotify_track_id=spotify_track_id)

    # Upsert
    result = await db.execute(
        select(TrackCache).where(TrackCache.spotify_track_id == spotify_track_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.track_name = track.track_name
        existing.artist_name = track.artist_name
        existing.duration_ms = track.duration_ms
        existing.album_image_url = track.album_image_url
        existing.fetched_at = time.time()
        await db.commit()
        return existing

    db.add(track)
    await db.commit()
    await db.refresh(track)
    return track


async def bulk_cache_from_api_response(
    tracks: list[dict], db: AsyncSession
) -> None:
    """Cache track metadata from a Spotify API response (e.g., recently_played items).
    This avoids individual API calls later."""
    for t in tracks:
        if not t.get("id"):
            continue

        result = await db.execute(
            select(TrackCache).where(TrackCache.spotify_track_id == t["id"])
        )
        existing = result.scalar_one_or_none()

        artists = t.get("artists", [])
        images = t.get("album", {}).get("images", [])

        if existing:
            existing.track_name = t.get("name")
            existing.artist_name = ", ".join(a["name"] for a in artists) if artists else None
            existing.duration_ms = t.get("duration_ms")
            existing.album_image_url = images[0]["url"] if images else None
            existing.fetched_at = time.time()
        else:
            db.add(TrackCache(
                spotify_track_id=t["id"],
                track_name=t.get("name"),
                artist_name=", ".join(a["name"] for a in artists) if artists else None,
                duration_ms=t.get("duration_ms"),
                album_image_url=images[0]["url"] if images else None,
            ))

    await db.commit()
