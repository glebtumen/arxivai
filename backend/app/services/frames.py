"""Extracts 3 key frames (start / middle / end) from a video using ffmpeg."""

import os
import subprocess


class FrameExtractionError(Exception):
    pass


def _get_duration(video_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return float(out.decode().strip())
    except Exception as e:
        raise FrameExtractionError(f"Could not read video duration: {e}") from e


def _extract_frame_at(video_path: str, timestamp: float, out_path: str):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(timestamp),
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        out_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 or not os.path.exists(out_path):
        raise FrameExtractionError(
            f"ffmpeg failed extracting frame at {timestamp}s: {result.stderr.decode(errors='ignore')}"
        )


def extract_key_frames(video_path: str, media_dir: str, item_id: str) -> list[str]:
    """
    Extracts 3 frames: start (0.5s in), middle, and end (0.5s before end).
    Returns list of 3 absolute file paths (start, middle, end).
    """
    duration = _get_duration(video_path)

    start_ts = min(0.5, duration / 2)
    mid_ts = duration / 2
    end_ts = max(duration - 0.5, duration / 2)

    frame_paths = []
    for label, ts in (("start", start_ts), ("middle", mid_ts), ("end", end_ts)):
        out_path = os.path.join(media_dir, f"{item_id}_{label}.jpg")
        _extract_frame_at(video_path, ts, out_path)
        frame_paths.append(out_path)

    return frame_paths
