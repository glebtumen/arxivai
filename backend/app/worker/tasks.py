import logging
import os

from ..database import SessionLocal
from ..services.downloader import download_media, DownloadError
from ..services.frames import extract_key_frames, FrameExtractionError
from ..services.transcribe import transcribe_video
from ..services.ai import analyze_content
from ..services.s3 import upload_file, S3Error
from ..models import Item
from ..config import settings

logger = logging.getLogger(__name__)


def _cleanup_local_files(paths: list[str]) -> None:
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError as e:
            logger.warning("Could not remove local temp file %r: %s", path, e)


def process_item(item_id: int) -> None:
    db = SessionLocal()
    local_files_to_cleanup: list[str] = []
    try:
        item = db.query(Item).get(item_id)
        if item is None:
            return
        item.status = "downloading"; db.commit()

        download_result = download_media(item.url, settings.media_dir)
        video_path = download_result["video_path"]
        local_files_to_cleanup.append(video_path)

        item.status = "extracting_frames"; db.commit()
        frame_paths = extract_key_frames(video_path, settings.media_dir, str(item_id))
        local_files_to_cleanup.extend(frame_paths)

        item.status = "transcribing"; db.commit()
        transcript = transcribe_video(video_path, settings.media_dir, str(item_id))

        item.status = "summarizing"; db.commit()
        ai_result = analyze_content(
            title=download_result.get("title", ""),
            description=download_result.get("description", ""),
            transcript=transcript,
        )

        item.status = "uploading"; db.commit()
        _, video_ext = os.path.splitext(video_path)
        video_url = upload_file(video_path, f"videos/{item_id}{video_ext}")
        frame_urls = [
            upload_file(p, f"frames/{item_id}_{label}.jpg")
            for p, label in zip(frame_paths, ("start", "middle", "end"))
        ]

        item.title = ai_result["title"]
        item.summary = ai_result["summary"]
        item.transcript = transcript
        item.tags = ai_result["tags"]
        item.video_path = video_url
        item.frame_paths = frame_urls
        item.status = "done"
        item.error_message = None
    except (DownloadError, FrameExtractionError, S3Error) as e:
        item.status = "failed"; item.error_message = str(e)
    except Exception as e:
        item.status = "failed"; item.error_message = f"Unexpected error: {e}"
    finally:
        db.commit()
        db.close()
        _cleanup_local_files(local_files_to_cleanup)
