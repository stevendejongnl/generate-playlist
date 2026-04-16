"""Detect skipped tracks by analyzing actual play duration from Spotify history.

Play history is persisted to the database and grows over time. Each sync
fetches new plays from Spotify and appends them. Skip detection runs against
the full accumulated history, not just the last 50 tracks.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import spotipy
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from playlist_generator.models.track_cache import PlayHistory
from playlist_generator.services import track_cache as cache_service

logger = logging.getLogger(__name__)

SKIP_THRESHOLD_PCT = 0.40
MIN_PLAY_SECONDS = 30


@dataclass
class PlayedTrack:
    spotify_id: str
    name: str
    artist: str
    played_at: str
    duration_ms: int
    actual_play_ms: int | None
    play_percentage: float | None
    was_skipped: bool


def _calculate_play_durations(raw: list[dict]) -> list[dict]:
    """Given a chronologically sorted list of plays, calculate actual play time."""
    for i, entry in enumerate(raw):
        entry["actual_play_ms"] = None
        entry["play_percentage"] = None
        entry["was_skipped"] = False

        if i < len(raw) - 1:
            try:
                current_time = datetime.fromisoformat(entry["played_at"].replace("Z", "+00:00"))
                next_time = datetime.fromisoformat(raw[i + 1]["played_at"].replace("Z", "+00:00"))
                gap_ms = int((next_time - current_time).total_seconds() * 1000)

                if 0 < gap_ms <= entry["duration_ms"] * 2:
                    entry["actual_play_ms"] = gap_ms
                    if entry["duration_ms"] > 0:
                        entry["play_percentage"] = min(gap_ms / entry["duration_ms"], 1.0)
                        entry["was_skipped"] = (
                            entry["play_percentage"] < SKIP_THRESHOLD_PCT
                            and gap_ms < MIN_PLAY_SECONDS * 1000
                        ) or (
                            entry["play_percentage"] < 0.15
                        )
            except (ValueError, TypeError):
                pass

    return raw


async def sync_play_history(
    user_id: str,
    spotify: spotipy.Spotify,
    db: AsyncSession,
    pages: int = 1,
) -> int:
    """Fetch recent plays from Spotify and persist new ones to the database.

    Paginates backwards through history using the oldest played_at timestamp
    from each batch. Returns the number of new plays added.
    """
    new_count = 0
    before_ms: int | None = None

    for page in range(pages):
        try:
            if before_ms:
                results = await asyncio.to_thread(
                    spotify.current_user_recently_played, limit=50, before=before_ms
                )
            else:
                results = await asyncio.to_thread(
                    spotify.current_user_recently_played, limit=50
                )
        except Exception:
            logger.warning("Failed to fetch play history page %d", page)
            break

        items = results.get("items", [])
        if not items:
            break

        # Cache track metadata from this response
        track_data = [item["track"] for item in items if item.get("track")]
        await cache_service.bulk_cache_from_api_response(track_data, db)

        # Build chronological list for duration calculation
        raw = []
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

        if not raw:
            break

        # Reverse to chronological for duration calculation
        raw.reverse()
        raw = _calculate_play_durations(raw)

        # Persist new entries
        page_new = 0
        for entry in raw:
            existing = await db.execute(
                select(PlayHistory).where(
                    PlayHistory.user_id == user_id,
                    PlayHistory.spotify_track_id == entry["spotify_id"],
                    PlayHistory.played_at == entry["played_at"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            db.add(PlayHistory(
                user_id=user_id,
                spotify_track_id=entry["spotify_id"],
                played_at=entry["played_at"],
                actual_play_ms=entry["actual_play_ms"],
                play_percentage=entry["play_percentage"],
                was_skipped=1 if entry["was_skipped"] else 0,
            ))
            page_new += 1

        new_count += page_new
        await db.commit()

        # Use the oldest played_at from this batch as the cursor for the next page
        # raw is chronological (oldest first), so raw[0] is the oldest
        oldest_played_at = raw[0]["played_at"]
        try:
            oldest_dt = datetime.fromisoformat(oldest_played_at.replace("Z", "+00:00"))
            before_ms = int(oldest_dt.timestamp() * 1000)
        except (ValueError, TypeError):
            break

        # If this page had no new entries and we're past page 1, we've caught up
        if page_new == 0 and page > 0:
            logger.info("No new plays on page %d, stopping", page)
            break

    logger.info("Synced %d new plays for user %s across %d pages", new_count, user_id, page + 1)
    return new_count


async def get_play_history(
    user_id: str,
    db: AsyncSession,
    limit: int = 100,
) -> list[PlayedTrack]:
    """Get persisted play history from the database (accumulated over time)."""
    result = await db.execute(
        select(PlayHistory)
        .where(PlayHistory.user_id == user_id)
        .order_by(desc(PlayHistory.played_at))
        .limit(limit)
    )
    rows = result.scalars().all()

    tracks: list[PlayedTrack] = []
    for row in rows:
        # Get name/artist from track cache
        cached = await cache_service.get_cached(row.spotify_track_id, db)
        tracks.append(PlayedTrack(
            spotify_id=row.spotify_track_id,
            name=cached.track_name if cached else row.spotify_track_id,
            artist=cached.artist_name if cached else "",
            played_at=row.played_at,
            duration_ms=cached.duration_ms if cached else 0,
            actual_play_ms=row.actual_play_ms,
            play_percentage=row.play_percentage,
            was_skipped=bool(row.was_skipped),
        ))

    return tracks


async def get_skip_summary(
    user_id: str, db: AsyncSession
) -> dict[str, dict]:
    """Aggregate skip data from ALL persisted play history.

    Returns dict of spotify_id -> {name, artist, skip_count, play_count, avg_play_pct}
    """
    # Get all plays with skip data
    result = await db.execute(
        select(PlayHistory)
        .where(
            PlayHistory.user_id == user_id,
            PlayHistory.actual_play_ms.is_not(None),
        )
    )
    rows = result.scalars().all()

    summary: dict[str, dict] = {}
    for row in rows:
        tid = row.spotify_track_id
        if tid not in summary:
            cached = await cache_service.get_cached(tid, db)
            summary[tid] = {
                "name": cached.track_name if cached else tid,
                "artist": cached.artist_name if cached else "",
                "skip_count": 0,
                "play_count": 0,
                "total_pct": 0.0,
            }
        s = summary[tid]
        s["play_count"] += 1
        if row.play_percentage is not None:
            s["total_pct"] += row.play_percentage
        if row.was_skipped:
            s["skip_count"] += 1

    for s in summary.values():
        s["avg_play_pct"] = s["total_pct"] / s["play_count"] if s["play_count"] > 0 else 0

    # Only tracks with at least one skip, sorted by most skipped
    return dict(sorted(
        ((tid, s) for tid, s in summary.items() if s["skip_count"] > 0),
        key=lambda x: (-x[1]["skip_count"], x[1]["avg_play_pct"]),
    ))


async def get_history_stats(user_id: str, db: AsyncSession) -> dict:
    """Get stats about accumulated play history."""
    total = await db.scalar(
        select(func.count(PlayHistory.id)).where(PlayHistory.user_id == user_id)
    )
    skipped = await db.scalar(
        select(func.count(PlayHistory.id)).where(
            PlayHistory.user_id == user_id,
            PlayHistory.was_skipped == 1,
        )
    )
    return {"total_plays": total or 0, "total_skips": skipped or 0}
