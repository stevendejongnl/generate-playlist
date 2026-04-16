"""Detect skipped tracks by analyzing actual play duration from Spotify history."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import spotipy

logger = logging.getLogger(__name__)

# A track played less than this percentage of its duration is considered skipped
SKIP_THRESHOLD_PCT = 0.40  # 40%
# Minimum play time to NOT be a skip (handles very short tracks)
MIN_PLAY_SECONDS = 30


@dataclass
class PlayedTrack:
    spotify_id: str
    name: str
    artist: str
    played_at: str
    duration_ms: int
    actual_play_ms: int | None  # None for the most recent track (no next track to compare)
    play_percentage: float | None
    was_skipped: bool


async def get_play_history_with_duration(
    spotify: spotipy.Spotify, limit: int = 50
) -> list[PlayedTrack]:
    """Fetch recently played tracks and calculate actual play duration.

    Play duration is inferred from the gap between consecutive played_at timestamps.
    If track A started at 14:00:00 and track B started at 14:01:15, track A was
    played for 1m15s regardless of its full duration.
    """
    results = await asyncio.to_thread(
        spotify.current_user_recently_played, limit=limit
    )
    items = results.get("items", [])
    if not items:
        return []

    # Parse into a list sorted by played_at (oldest first)
    raw: list[dict] = []
    for item in items:
        t = item.get("track")
        if not t or not t.get("id"):
            continue
        artists = t.get("artists", [])
        raw.append({
            "spotify_id": t["id"],
            "name": t.get("name", ""),
            "artist": ", ".join(a["name"] for a in artists) if artists else "",
            "played_at": item.get("played_at", ""),
            "duration_ms": t.get("duration_ms", 0),
        })

    # Spotify returns newest first, reverse to chronological order
    raw.reverse()

    tracks: list[PlayedTrack] = []
    for i, entry in enumerate(raw):
        actual_play_ms: int | None = None
        play_pct: float | None = None
        was_skipped = False

        if i < len(raw) - 1:
            # Calculate play duration from gap to next track
            try:
                current_time = datetime.fromisoformat(entry["played_at"].replace("Z", "+00:00"))
                next_time = datetime.fromisoformat(raw[i + 1]["played_at"].replace("Z", "+00:00"))
                gap_ms = int((next_time - current_time).total_seconds() * 1000)

                # Only use the gap if it's reasonable (< 2x the track duration)
                # Larger gaps likely mean the user stopped listening
                if 0 < gap_ms <= entry["duration_ms"] * 2:
                    actual_play_ms = gap_ms
                    if entry["duration_ms"] > 0:
                        play_pct = min(actual_play_ms / entry["duration_ms"], 1.0)
                        was_skipped = (
                            play_pct < SKIP_THRESHOLD_PCT
                            and actual_play_ms < MIN_PLAY_SECONDS * 1000
                        ) or (
                            play_pct < 0.15  # Very short listen = definite skip
                        )
            except (ValueError, TypeError):
                pass

        tracks.append(PlayedTrack(
            spotify_id=entry["spotify_id"],
            name=entry["name"],
            artist=entry["artist"],
            played_at=entry["played_at"],
            duration_ms=entry["duration_ms"],
            actual_play_ms=actual_play_ms,
            play_percentage=play_pct,
            was_skipped=was_skipped,
        ))

    # Return newest first for display
    tracks.reverse()
    return tracks


def get_skip_summary(tracks: list[PlayedTrack]) -> dict[str, dict]:
    """Aggregate skip data across play history.

    Returns a dict of spotify_id -> {name, artist, skip_count, play_count, avg_play_pct}
    sorted by most skipped.
    """
    summary: dict[str, dict] = {}
    for t in tracks:
        if t.actual_play_ms is None:
            continue  # Can't determine for the most recent track

        if t.spotify_id not in summary:
            summary[t.spotify_id] = {
                "name": t.name,
                "artist": t.artist,
                "skip_count": 0,
                "play_count": 0,
                "total_pct": 0.0,
                "duration_ms": t.duration_ms,
            }

        s = summary[t.spotify_id]
        s["play_count"] += 1
        if t.play_percentage is not None:
            s["total_pct"] += t.play_percentage
        if t.was_skipped:
            s["skip_count"] += 1

    # Calculate averages and sort
    result = {}
    for tid, s in summary.items():
        s["avg_play_pct"] = s["total_pct"] / s["play_count"] if s["play_count"] > 0 else 0
        result[tid] = s

    # Sort by skip_count desc, then by avg_play_pct asc
    return dict(sorted(
        result.items(),
        key=lambda x: (-x[1]["skip_count"], x[1]["avg_play_pct"]),
    ))
