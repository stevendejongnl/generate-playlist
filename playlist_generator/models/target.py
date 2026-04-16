import uuid
import time

from sqlalchemy import String, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_generator.database import Base


class TargetPlaylist(Base):
    __tablename__ = "target_playlists"
    __table_args__ = (
        UniqueConstraint("user_id", "spotify_playlist_id", name="uq_target_playlist_user"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    spotify_playlist_id: Mapped[str] = mapped_column(String(50), nullable=False)
    playlist_name: Mapped[str | None] = mapped_column(String(500))
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User"] = relationship(back_populates="target_playlists")  # type: ignore[name-defined]  # noqa: F821
