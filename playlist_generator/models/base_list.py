import uuid
import time

from sqlalchemy import String, Integer, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_generator.database import Base


class BaseTrack(Base):
    __tablename__ = "base_tracks"
    __table_args__ = (
        UniqueConstraint("user_id", "spotify_track_id", name="uq_base_track_user"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    spotify_track_id: Mapped[str] = mapped_column(String(50), nullable=False)
    track_name: Mapped[str | None] = mapped_column(String(500))
    artist_name: Mapped[str | None] = mapped_column(String(500))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    album_image_url: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User"] = relationship(back_populates="base_tracks")  # type: ignore[name-defined]  # noqa: F821


class BasePlaylist(Base):
    __tablename__ = "base_playlists"
    __table_args__ = (
        UniqueConstraint("user_id", "spotify_playlist_id", name="uq_base_playlist_user"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    spotify_playlist_id: Mapped[str] = mapped_column(String(50), nullable=False)
    playlist_name: Mapped[str | None] = mapped_column(String(500))
    track_count: Mapped[int | None] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User"] = relationship(back_populates="base_playlists")  # type: ignore[name-defined]  # noqa: F821
