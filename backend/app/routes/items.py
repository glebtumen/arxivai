from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Item, User
from ..schemas import ItemCreate, ItemOut
from ..services.downloader import download_media, DownloadError
from ..services.frames import extract_key_frames, FrameExtractionError
from ..services.ai import analyze_content
from ..services.transcribe import transcribe_video
from ..queue import item_queue
from rq import Retry

router = APIRouter(prefix="/items", tags=["items"])


def _get_or_create_user(db: Session, telegram_user_id: int) -> User:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if user is None:
        user = User(telegram_user_id=telegram_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("", response_model=ItemOut)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    user = _get_or_create_user(db, payload.telegram_user_id)
    item = Item(user_id=user.id, url=payload.url, status="queued")
    db.add(item)
    db.commit()
    db.refresh(item)

    item_queue.enqueue("app.worker.tasks.process_item", item.id, job_timeout=600, retry=Retry(max=3, interval=[10, 30, 60]))

    return item  # status="queued" — comes back near-instantly


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
