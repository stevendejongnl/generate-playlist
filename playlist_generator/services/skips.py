"""Detect skipped tracks by comparing generated playlists against play history."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import spotipy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.history import GenerationHistory, GenerationHistoryTrack

logger = logging.getLogger(__name__)


@dataclass
class PlayedTrack:
    spotify_id: str
    name: str
    artist: str
    played_at: str  # ISO timestamp
    duration_ms: int


@dataclass
class SkippedTrack:
    spotify_id: str
    name: str
    artist: str
    skip_count: int
    last_generated_at: str  # human-readable
    was_played: bool  # appeared in recent history at all


async def get_recently_played(
    spotify: spotipy.Spotify, limit: int = 50
) -> list[PlayedTrack]:
    """Fetch the user's recently played tracks from Spotify."""
    results = await asyncio.to_thread(
        spotify.current_user_recently_played, limit=limit
    )
    tracks: list[PlayedTrack] = []
    for item in results.get("items", []):
        t = item.get("track")
        if not t or not t.get("id"):
            continue
        artists = t.get("artists", [])
        tracks.append(PlayedTrack(
            spotify_id=t["id"],
            name=t.get("name", ""),
            artist=", ".join(a["name"] for a in artists) if artists else "",
            played_at=item.get("played_at", ""),
            duration_ms=t.get("duration_ms", 0),
        ))
    return tracks


async def detect_skipped_tracks(
    user_id: str,
    spotify: spotipy.Spotify,
    db: AsyncSession,
    generations_to_check: int = 5,
) -> list[SkippedTrack]:
    """Compare generated tracks against play history to find likely skips.

    A track is considered "skipped" if it was in a generated playlist but
    doesn't appear in the user's recent play history.
    """
    # Get recent play history (track IDs that were actually listened to)
    played = await get_recently_played(spotify, limit=50)
    played_ids = {t.spotify_id for t in played}

    # Get the most recent generations with their tracks
    result = await db.execute(
        select(GenerationHistory)
        .where(GenerationHistory.user_id == user_id)
        .order_by(GenerationHistory.created_at.desc())
        .limit(generations_to_check)
    )
    generations = list(result.scalars().all())

    if not generations:
        return []

    gen_ids = [g.id for g in generations]
    result = await db.execute(
        select(GenerationHistoryTrack)
        .where(GenerationHistoryTrack.generation_id.in_(gen_ids))
    )
    gen_tracks = list(result.scalars().all())

    # Count how many times each track was generated but not played
    skip_counts: dict[str, dict] = {}
    for gt in gen_tracks:
        tid = gt.spotify_track_id
        if tid not in skip_counts:
            skip_counts[tid] = {
                "name": gt.track_name or "",
                "artist": gt.artist_name or "",
                "count": 0,
                "was_played": tid in played_ids,
                "last_gen": 0.0,
            }
        if tid not in played_ids:
            skip_counts[tid]["count"] += 1
        # Track the most recent generation time
        gen = next((g for g in generations if g.id == gt.generation_id), None)
        if gen and gen.created_at > skip_counts[tid]["last_gen"]:
            skip_counts[tid]["last_gen"] = gen.created_at

    # Return tracks that were generated but never played, sorted by skip count
    skipped = [
        SkippedTrack(
            spotify_id=tid,
            name=info["name"],
            artist=info["artist"],
            skip_count=info["count"],
            last_generated_at=datetime.fromtimestamp(
                info["last_gen"], tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M") if info["last_gen"] else "",
            was_played=info["was_played"],
        )
        for tid, info in skip_counts.items()
        if info["count"] > 0  # Only tracks that were generated but not played
    ]
    skipped.sort(key=lambda s: s.skip_count, reverse=True)

    return skipped
