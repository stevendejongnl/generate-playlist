import asyncio
import logging
import math
import random
from dataclasses import dataclass

import spotipy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.base_list import BaseTrack, BasePlaylist
from playlist_generator.models.blacklist import BlacklistTrack, BlacklistPlaylist
from playlist_generator.models.history import GenerationHistory

logger = logging.getLogger(__name__)


@dataclass
class TrackInfo:
    spotify_id: str
    name: str
    artist: str
    duration_ms: int
    is_discovery: bool = False


@dataclass
class GenerationResult:
    tracks: list[TrackInfo]
    total_duration_ms: int
    discovery_count: int


async def _fetch_playlist_tracks(
    playlist_id: str, spotify: spotipy.Spotify
) -> list[dict]:
    """Fetch all tracks from a Spotify playlist, handling pagination."""
    all_tracks: list[dict] = []
    results = await asyncio.to_thread(
        spotify.playlist_tracks, playlist_id, fields="items(track(id,name,artists,duration_ms)),next"
    )
    while results:
        for item in results.get("items", []):
            track = item.get("track")
            if track and track.get("id"):
                all_tracks.append(track)
        if results.get("next"):
            results = await asyncio.to_thread(spotify.next, results)
        else:
            break
    return all_tracks


async def _collect_base_tracks(
    user_id: str, spotify: spotipy.Spotify, db: AsyncSession
) -> list[TrackInfo]:
    """Collect all tracks from the user's base list (individual tracks + playlist tracks)."""
    pool: list[TrackInfo] = []
    seen: set[str] = set()

    # 1. Individual tracks from the database
    result = await db.execute(
        select(BaseTrack).where(BaseTrack.user_id == user_id)
    )
    for bt in result.scalars().all():
        if bt.spotify_track_id not in seen:
            seen.add(bt.spotify_track_id)
            pool.append(TrackInfo(
                spotify_id=bt.spotify_track_id,
                name=bt.track_name or "",
                artist=bt.artist_name or "",
                duration_ms=bt.duration_ms or 0,
            ))

    # 2. Tracks from base playlists
    result = await db.execute(
        select(BasePlaylist).where(BasePlaylist.user_id == user_id)
    )
    playlists = result.scalars().all()

    for bp in playlists:
        try:
            tracks = await _fetch_playlist_tracks(bp.spotify_playlist_id, spotify)
            for t in tracks:
                tid = t["id"]
                if tid not in seen:
                    seen.add(tid)
                    artists = t.get("artists", [])
                    pool.append(TrackInfo(
                        spotify_id=tid,
                        name=t.get("name", ""),
                        artist=", ".join(a["name"] for a in artists) if artists else "",
                        duration_ms=t.get("duration_ms", 0),
                    ))
        except Exception:
            logger.warning("Failed to fetch tracks from playlist %s", bp.spotify_playlist_id)

    return pool


async def _build_blacklist_set(
    user_id: str, spotify: spotipy.Spotify, db: AsyncSession
) -> set[str]:
    """Build a set of all blacklisted track IDs."""
    blocked: set[str] = set()

    # Individually blacklisted tracks
    result = await db.execute(
        select(BlacklistTrack.spotify_track_id).where(BlacklistTrack.user_id == user_id)
    )
    for (track_id,) in result.all():
        blocked.add(track_id)

    # Tracks from blacklisted playlists
    result = await db.execute(
        select(BlacklistPlaylist).where(BlacklistPlaylist.user_id == user_id)
    )
    for bp in result.scalars().all():
        try:
            tracks = await _fetch_playlist_tracks(bp.spotify_playlist_id, spotify)
            for t in tracks:
                if t.get("id"):
                    blocked.add(t["id"])
        except Exception:
            logger.warning("Failed to fetch blacklist playlist %s", bp.spotify_playlist_id)

    return blocked


async def _get_recommendations(
    seed_pool: list[TrackInfo],
    blacklist: set[str],
    count: int,
    spotify: spotipy.Spotify,
) -> list[TrackInfo]:
    """Get discovery tracks via Spotify's recommendations API."""
    if not seed_pool or count <= 0:
        return []

    discovery: list[TrackInfo] = []
    existing_ids = {t.spotify_id for t in seed_pool} | blacklist
    attempts = 0
    max_attempts = math.ceil(count / 20) + 2  # Extra attempts for filtered-out tracks

    while len(discovery) < count and attempts < max_attempts:
        attempts += 1
        # Sample up to 5 seed tracks (Spotify's limit)
        seeds = random.sample(seed_pool, min(5, len(seed_pool)))
        seed_ids = [s.spotify_id for s in seeds]
        remaining = count - len(discovery)

        try:
            result = await asyncio.to_thread(
                spotify.recommendations,
                seed_tracks=seed_ids,
                limit=min(remaining, 100),
            )
            for t in result.get("tracks", []):
                tid = t.get("id")
                if tid and tid not in existing_ids:
                    existing_ids.add(tid)
                    artists = t.get("artists", [])
                    discovery.append(TrackInfo(
                        spotify_id=tid,
                        name=t.get("name", ""),
                        artist=", ".join(a["name"] for a in artists) if artists else "",
                        duration_ms=t.get("duration_ms", 0),
                        is_discovery=True,
                    ))
                    if len(discovery) >= count:
                        break
        except Exception:
            logger.warning("Recommendations call failed (attempt %d)", attempts)
            break

    return discovery


def _apply_limits(
    tracks: list[TrackInfo],
    max_tracks: int | None,
    max_minutes: int | None,
) -> list[TrackInfo]:
    """Truncate the track list based on max_tracks and/or max_minutes."""
    result: list[TrackInfo] = []
    total_ms = 0
    max_ms = max_minutes * 60_000 if max_minutes else None

    for track in tracks:
        if max_tracks and len(result) >= max_tracks:
            break
        if max_ms and total_ms + track.duration_ms > max_ms:
            break
        result.append(track)
        total_ms += track.duration_ms

    return result


async def preview(
    user_id: str,
    spotify: spotipy.Spotify,
    db: AsyncSession,
    max_tracks: int | None = None,
    max_minutes: int | None = None,
    discovery_mode: str | None = None,
    discovery_value: float | None = None,
) -> GenerationResult:
    """Run the full generation pipeline without writing to Spotify."""
    # 1. Collect
    base_pool = await _collect_base_tracks(user_id, spotify, db)

    # 2. Blacklist
    blacklist = await _build_blacklist_set(user_id, spotify, db)

    # 3. Filter
    filtered = [t for t in base_pool if t.spotify_id not in blacklist]

    # 4. Discovery
    discovery_tracks: list[TrackInfo] = []
    if discovery_mode and discovery_value and discovery_value > 0:
        if discovery_mode == "percentage":
            discovery_count = max(1, int(len(filtered) * discovery_value / 100))
        else:  # fixed
            discovery_count = int(discovery_value)
        discovery_tracks = await _get_recommendations(
            filtered, blacklist, discovery_count, spotify
        )

    # 5. Combine and shuffle
    all_tracks = filtered + discovery_tracks
    random.shuffle(all_tracks)

    # 6. Apply limits
    all_tracks = _apply_limits(all_tracks, max_tracks, max_minutes)

    total_ms = sum(t.duration_ms for t in all_tracks)
    disc_count = sum(1 for t in all_tracks if t.is_discovery)

    return GenerationResult(
        tracks=all_tracks,
        total_duration_ms=total_ms,
        discovery_count=disc_count,
    )


async def execute(
    user_id: str,
    target_playlist_id: str,
    target_playlist_name: str | None,
    spotify: spotipy.Spotify,
    db: AsyncSession,
    max_tracks: int | None = None,
    max_minutes: int | None = None,
    discovery_mode: str | None = None,
    discovery_value: float | None = None,
) -> GenerationResult:
    """Run the full pipeline and write to the Spotify playlist."""
    result = await preview(
        user_id, spotify, db,
        max_tracks=max_tracks,
        max_minutes=max_minutes,
        discovery_mode=discovery_mode,
        discovery_value=discovery_value,
    )

    if not result.tracks:
        return result

    # Clear the target playlist
    track_uris = [f"spotify:track:{t.spotify_id}" for t in result.tracks]
    await asyncio.to_thread(
        spotify.playlist_replace_items, target_playlist_id, []
    )

    # Add in chunks of 100
    for i in range(0, len(track_uris), 100):
        chunk = track_uris[i : i + 100]
        await asyncio.to_thread(
            spotify.playlist_add_items, target_playlist_id, chunk
        )

    # Record history
    history = GenerationHistory(
        user_id=user_id,
        target_playlist_id=target_playlist_id,
        target_playlist_name=target_playlist_name,
        track_count=len(result.tracks),
        total_duration_ms=result.total_duration_ms,
        discovery_count=result.discovery_count,
        max_tracks_param=max_tracks,
        max_minutes_param=max_minutes,
        discovery_mode=discovery_mode,
        discovery_value=discovery_value,
    )
    db.add(history)
    await db.commit()

    return result
