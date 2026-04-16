import uuid
import time

from sqlalchemy import String, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_generator.database import Base


class BlacklistTrack(Base):
    __tablename__ = "blacklist_tracks"
    __table_args__ = (
        UniqueConstraint("user_id", "spotify_track_id", name="uq_blacklist_track_user"),
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
    added_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User"] = relationship(back_populates="blacklist_tracks")  # type: ignore[name-defined]  # noqa: F821


class BlacklistPlaylist(Base):
    __tablename__ = "blacklist_playlists"
    __table_args__ = (
        UniqueConstraint("user_id", "spotify_playlist_id", name="uq_blacklist_playlist_user"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    spotify_playlist_id: Mapped[str] = mapped_column(String(50), nullable=False)
    playlist_name: Mapped[str | None] = mapped_column(String(500))
    added_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User"] = relationship(back_populates="blacklist_playlists")  # type: ignore[name-defined]  # noqa: F821
