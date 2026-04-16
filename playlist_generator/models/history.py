import uuid
import time

from sqlalchemy import String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_generator.database import Base


class GenerationHistory(Base):
    __tablename__ = "generation_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_playlist_id: Mapped[str] = mapped_column(String(50), nullable=False)
    target_playlist_name: Mapped[str | None] = mapped_column(String(500))
    track_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_duration_ms: Mapped[int | None] = mapped_column(Integer)
    discovery_count: Mapped[int] = mapped_column(Integer, default=0)
    max_tracks_param: Mapped[int | None] = mapped_column(Integer)
    max_minutes_param: Mapped[int | None] = mapped_column(Integer)
    discovery_mode: Mapped[str | None] = mapped_column(String(20))
    discovery_value: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User"] = relationship(back_populates="generation_history")  # type: ignore[name-defined]  # noqa: F821
    tracks: Mapped[list["GenerationHistoryTrack"]] = relationship(
        back_populates="generation", cascade="all, delete-orphan"
    )


class GenerationHistoryTrack(Base):
    __tablename__ = "generation_history_tracks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    generation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_history.id", ondelete="CASCADE"), nullable=False
    )
    spotify_track_id: Mapped[str] = mapped_column(String(50), nullable=False)
    track_name: Mapped[str | None] = mapped_column(String(500))
    artist_name: Mapped[str | None] = mapped_column(String(500))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    is_discovery: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    generation: Mapped["GenerationHistory"] = relationship(back_populates="tracks")
