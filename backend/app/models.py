from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    items = relationship("Item", back_populates="user")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    url = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | processing | done | failed
    error_message = Column(Text, nullable=True)

    title = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)  # spoken transcript (Whisper)
    tags = Column(JSON, default=list)  # list[str]

    frame_paths = Column(JSON, default=list)  # list[str] - relative paths under /media
    video_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="items")
