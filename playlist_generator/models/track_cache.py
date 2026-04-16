import uuid
import time

from sqlalchemy import String, Integer, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_generator.database import Base


class TrackCache(Base):
    """Local cache of Spotify track metadata. Avoids repeat API calls."""
    __tablename__ = "track_cache"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    spotify_track_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    track_name: Mapped[str | None] = mapped_column(String(500))
    artist_name: Mapped[str | None] = mapped_column(String(500))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    album_image_url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[float] = mapped_column(Float, default=time.time)


class PlayHistory(Base):
    """Persistent record of every play we observe from Spotify. Grows over time."""
    __tablename__ = "play_history"
    __table_args__ = (
        UniqueConstraint("user_id", "spotify_track_id", "played_at", name="uq_play_history"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    spotify_track_id: Mapped[str] = mapped_column(String(50), nullable=False)
    played_at: Mapped[str] = mapped_column(String(30), nullable=False)  # ISO timestamp
    actual_play_ms: Mapped[int | None] = mapped_column(Integer)
    play_percentage: Mapped[float | None] = mapped_column(Float)
    was_skipped: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[float] = mapped_column(Float, default=time.time)
