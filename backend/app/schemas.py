from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ItemCreate(BaseModel):
    telegram_user_id: int
    url: str


class ItemOut(BaseModel):
    id: int
    url: str
    status: str
    error_message: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    tags: list[str] = []
    frame_paths: list[str] = []
    video_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
