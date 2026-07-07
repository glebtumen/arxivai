"""
Extracts audio from a video and transcribes it via OpenRouter's Whisper model
(openai/whisper-large-v3) using the OpenAI SDK's audio.transcriptions API.

Everything here is best-effort: if the video has no audio, ffmpeg fails, or the
API errors out, we return an empty transcript instead of raising, so the rest
of the pipeline keeps working.
"""

import logging
import os
import subprocess

from openai import OpenAI

from ..config import settings

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )


def _has_audio_stream(video_path: str) -> bool:
    """Return True if the video contains at least one audio stream."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        video_path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return bool(out.decode().strip())
    except Exception as e:
        logger.warning("ffprobe audio-check failed: %s", e)
        return False


def extract_audio(video_path: str, media_dir: str, item_id: str) -> str | None:
    """
    Extract mono 16kHz WAV audio (ideal for Whisper) from the video.
    Returns the audio path, or None if the video has no audio / extraction fails.
    """
    if not _has_audio_stream(video_path):
        logger.info("No audio stream found in %s; skipping transcription.", video_path)
        return None

    audio_path = os.path.join(media_dir, f"{item_id}_audio.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",  # drop video
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",  # 16 kHz
        "-ac",
        "1",  # mono
        audio_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 or not os.path.exists(audio_path):
        logger.warning(
            "ffmpeg audio extraction failed: %s",
            result.stderr.decode(errors="ignore")[:300],
        )
        return None
    return audio_path


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe the given audio file using OpenRouter's Whisper model.
    Returns the transcript text, or "" on any failure.
    """
    if not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY missing; skipping transcription.")
        return ""

    client = _get_client()
    try:
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model=settings.openrouter_whisper_model,
                file=f,
                extra_headers={
                    "HTTP-Referer": settings.site_url,
                    "X-Title": settings.site_title,
                },
            )
    except Exception as e:
        logger.exception("Transcription request failed: %s", e)
        return ""

    # The SDK returns an object with a `.text` attribute (or a plain string).
    text = getattr(result, "text", None)
    if text is None and isinstance(result, str):
        text = result
    return (text or "").strip()


def transcribe_video(video_path: str, media_dir: str, item_id: str) -> str:
    """
    Convenience wrapper: extract audio -> transcribe -> clean up the temp WAV.
    Returns the transcript text, or "" if there's no audio / anything fails.
    """
    audio_path = extract_audio(video_path, media_dir, item_id)
    if not audio_path:
        return ""

    try:
        return transcribe_audio(audio_path)
    finally:
        # We don't need to keep the extracted audio around.
        try:
            os.remove(audio_path)
        except OSError:
            pass
