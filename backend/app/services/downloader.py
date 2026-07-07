"""Downloads media (e.g. Instagram Reels/posts) using yt-dlp."""

import os
import uuid

import yt_dlp

from ..config import settings


class DownloadError(Exception):
    pass


def _find_output_file(base_no_ext: str) -> str | None:
    """Find the actual downloaded file by trying common video extensions."""
    for ext in (".mp4", ".mkv", ".webm", ".mov"):
        candidate = base_no_ext + ext
        if os.path.exists(candidate):
            return candidate
    return None


def download_media(url: str, media_dir: str) -> dict:
    """
    Downloads the video at `url` into media_dir.

    Returns dict with:
        video_path: absolute path to the downloaded video file
        title: title/caption extracted by yt-dlp (if any)
        description: description/caption text (if any)
    """
    os.makedirs(media_dir, exist_ok=True)
    item_id = uuid.uuid4().hex
    out_template = os.path.join(media_dir, f"{item_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": out_template,
        # Always prefer a combined video+audio stream; if the best video and
        # best audio are separate, merge them via ffmpeg. Picking a literal
        # "mp4" format first can select a video-only stream and silently
        # drop audio - so don't do that.
        "format": "bestvideo*+bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
    }

    # Instagram frequently requires a logged-in session to allow downloads.
    # If a cookies file is configured, use it (see config.py /
    # INSTAGRAM_COOKIES_FILE in .env).
    if settings.instagram_cookies_file:
        ydl_opts["cookiefile"] = settings.instagram_cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Instagram carousels / playlists return an "entries" list; use the
            # first downloadable video entry.
            if info and "entries" in info:
                entries = [e for e in (info.get("entries") or []) if e]
                if not entries:
                    raise DownloadError("No downloadable media found at this link.")
                info = entries[0]

            video_path = ydl.prepare_filename(info)
    except DownloadError:
        raise
    except Exception as e:
        raise DownloadError(str(e)) from e

    if not os.path.exists(video_path):
        base, _ = os.path.splitext(video_path)
        found = _find_output_file(base)
        if found is None:
            raise DownloadError("Downloaded file not found after yt-dlp finished.")
        video_path = found

    return {
        "video_path": video_path,
        "title": (info.get("title") or "") if info else "",
        "description": (info.get("description") or "") if info else "",
    }
