import uuid
import time

from sqlalchemy import String, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_generator.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    spotify_user_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)

    # Encrypted Spotify tokens
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[float] = mapped_column(Float, nullable=False)
    token_scopes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time)

    # Relationships
    base_tracks: Mapped[list["BaseTrack"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    base_playlists: Mapped[list["BasePlaylist"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    blacklist_tracks: Mapped[list["BlacklistTrack"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    blacklist_playlists: Mapped[list["BlacklistPlaylist"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    target_playlists: Mapped[list["TargetPlaylist"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    cover_image_configs: Mapped[list["CoverImageConfig"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    generation_history: Mapped[list["GenerationHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
