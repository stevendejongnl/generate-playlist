import uuid
import time

from sqlalchemy import String, Integer, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_generator.database import Base


class CoverImageConfig(Base):
    __tablename__ = "cover_image_configs"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_cover_config_user_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    font_size: Mapped[int] = mapped_column(Integer, default=120)
    width: Mapped[int] = mapped_column(Integer, default=1500)
    height: Mapped[int] = mapped_column(Integer, default=1500)
    bg_color: Mapped[str] = mapped_column(String(7), default="#496D89")
    text_color: Mapped[str] = mapped_column(String(7), default="#FFFF00")
    font_name: Mapped[str] = mapped_column(String(100), default="Roboto-Black.ttf")
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User"] = relationship(back_populates="cover_image_configs")  # type: ignore[name-defined]  # noqa: F821
