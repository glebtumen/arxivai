import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Item, User
from ..schemas import ItemCreate, ItemOut
from ..services.downloader import download_media, DownloadError
from ..services.frames import extract_key_frames, FrameExtractionError
from ..services.ai import analyze_content
from ..services.transcribe import transcribe_video

router = APIRouter(prefix="/items", tags=["items"])


def _get_or_create_user(db: Session, telegram_user_id: int) -> User:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if user is None:
        user = User(telegram_user_id=telegram_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _to_relative(path: str) -> str:
    """
    Convert an absolute media path into a URL-safe path relative to the media
    dir. Always uses forward slashes so it works in URLs on any OS.
    """
    media_dir_abs = os.path.abspath(settings.media_dir)
    rel = os.path.relpath(os.path.abspath(path), media_dir_abs)
    return rel.replace(os.sep, "/")


@router.post("", response_model=ItemOut)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    user = _get_or_create_user(db, payload.telegram_user_id)

    item = Item(user_id=user.id, url=payload.url, status="processing")
    db.add(item)
    db.commit()
    db.refresh(item)

    media_dir = os.path.abspath(settings.media_dir)
    os.makedirs(media_dir, exist_ok=True)
    item_uid = uuid.uuid4().hex

    try:
        # 1. Download
        download_result = download_media(payload.url, media_dir)
        video_path = download_result["video_path"]

        # 2. Extract frames
        frame_paths = extract_key_frames(video_path, media_dir, item_uid)

        # 3. Transcribe audio (best-effort; empty string if no audio / fails)
        transcript = transcribe_video(video_path, media_dir, item_uid)

        # 4. AI analysis (uses caption + transcript together)
        ai_result = analyze_content(
            title=download_result.get("title", ""),
            description=download_result.get("description", ""),
            transcript=transcript,
        )

        item.title = ai_result["title"]
        item.summary = ai_result["summary"]
        item.transcript = transcript
        item.tags = ai_result["tags"]
        item.video_path = _to_relative(video_path)
        item.frame_paths = [_to_relative(p) for p in frame_paths]
        item.status = "done"
        item.error_message = None

    except DownloadError as e:
        item.status = "failed"
        item.error_message = f"Could not download this link: {e}"
    except FrameExtractionError as e:
        item.status = "failed"
        item.error_message = f"Could not extract frames: {e}"
    except Exception as e:
        item.status = "failed"
        item.error_message = f"Unexpected error: {e}"

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.get("", response_model=list[ItemOut])
def list_items(telegram_user_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Item)
    if telegram_user_id is not None:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if user is None:
            return []
        query = query.filter(Item.user_id == user.id)
    return query.order_by(Item.created_at.desc()).all()


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
