import os
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Values are read from environment variables / .env automatically by
    # pydantic-settings using the (case-insensitive) field names below.
    database_url: str = "postgresql://archivebot:archivebot@localhost:5432/archivebot"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-5.4-nano"
    openrouter_whisper_model: str = "openai/whisper-large-v3"
    site_url: str = "http://localhost:3000"
    site_title: str = "ArchiveBot"
    media_dir: str = "/storage/media"
    web_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    redis_url: str = "redis://redis:6379/0"
    # Optional: path to a Netscape-format cookies.txt exported from a
    # logged-in Instagram browser session. Instagram frequently requires
    # this now for downloads to work. Leave empty to download without auth
    # (works for some public content, fails for a lot of it).
    instagram_cookies_file: str = ""
    s3_yandex_endpoint: str = ""
    s3_yandex_region: str = ""
    s3_yandex_ident_key: str = ""
    s3_yandex_secret_key: str = ""
    s3_yandex_bucket: str = ""
    # Optional: if enabled, the backend will refuse to start (raise
    # SystemExit) when validate_settings() finds any error-level problem
    # (e.g. an invalid DATABASE_URL or an unwritable MEDIA_DIR). Off by
    # default so local/dev setups keep degrading gracefully with warnings.
    fail_fast: bool = False
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def _is_valid_url(value: str) -> bool:
    """Return True if value is a non-empty, parseable http(s) URL."""
    if not value:
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def validate_settings() -> list[tuple[str, str, str]]:
    """Run sanity checks on the loaded settings.

    Returns a list of (setting_name, level, message) tuples where level is
    "error" for settings that will break core functionality and "warning"
    for settings that degrade optional features.
    """
    problems: list[tuple[str, str, str]] = []

    # --- Required / core settings -------------------------------------
    if not settings.database_url:
        problems.append(
            (
                "DATABASE_URL",
                "error",
                "DATABASE_URL is not set. The backend cannot start without a database.",
            )
        )
    else:
        try:
            parsed = urlparse(settings.database_url)
            if not parsed.scheme or not parsed.netloc:
                problems.append(
                    (
                        "DATABASE_URL",
                        "error",
                        f"DATABASE_URL is not a valid URL: {settings.database_url!r}",
                    )
                )
        except ValueError:
            problems.append(
                (
                    "DATABASE_URL",
                    "error",
                    f"DATABASE_URL is not a valid URL: {settings.database_url!r}",
                )
            )

    if not settings.media_dir:
        problems.append(
            (
                "MEDIA_DIR",
                "error",
                "MEDIA_DIR is not set. The backend cannot store media without it.",
            )
        )
    else:
        media_dir_abs = os.path.abspath(settings.media_dir)
        if not os.path.exists(media_dir_abs):
            try:
                os.makedirs(media_dir_abs, exist_ok=True)
            except OSError as e:
                problems.append(
                    (
                        "MEDIA_DIR",
                        "error",
                        f"MEDIA_DIR {media_dir_abs!r} cannot be created: {e}",
                    )
                )
        if os.path.exists(media_dir_abs) and not os.access(media_dir_abs, os.W_OK):
            problems.append(
                (
                    "MEDIA_DIR",
                    "error",
                    f"MEDIA_DIR {media_dir_abs!r} is not writable.",
                )
            )

    # --- Optional / feature-degrading settings -------------------------
    if not settings.openrouter_api_key:
        problems.append(
            (
                "OPENROUTER_API_KEY",
                "warning",
                "OPENROUTER_API_KEY is not set. AI analysis and transcription "
                "will be skipped until you set it in backend/.env.",
            )
        )
    if not settings.openrouter_model:
        problems.append(
            (
                "OPENROUTER_MODEL",
                "warning",
                "OPENROUTER_MODEL is not set. Falling back to the default model.",
            )
        )
    if not settings.openrouter_whisper_model:
        problems.append(
            (
                "OPENROUTER_WHISPER_MODEL",
                "warning",
                "OPENROUTER_WHISPER_MODEL is not set. Falling back to the "
                "default whisper model.",
            )
        )

    for name, value in (
        ("SITE_URL", settings.site_url),
        ("WEB_BASE_URL", settings.web_base_url),
        ("API_BASE_URL", settings.api_base_url),
    ):
        if not _is_valid_url(value):
            problems.append(
                (
                    name,
                    "warning",
                    f"{name} is not a valid http(s) URL: {value!r}",
                )
            )

    for name, value in (
        ("S3_YANDEX_ENDPOINT", settings.s3_yandex_endpoint),
        ("S3_YANDEX_REGION", settings.s3_yandex_region),
        ("S3_YANDEX_IDENT_KEY", settings.s3_yandex_ident_key),
        ("S3_YANDEX_SECRET_KEY", settings.s3_yandex_secret_key),
        ("S3_YANDEX_BUCKET", settings.s3_yandex_bucket),
    ):
        if not value:
            problems.append(
                (
                    name,
                    "error",
                    f"{name} is not set. Media files cannot be uploaded to "
                    "Yandex Object Storage without it.",
                )
            )

    if settings.s3_yandex_endpoint and not _is_valid_url(settings.s3_yandex_endpoint):
        problems.append(
            (
                "S3_YANDEX_ENDPOINT",
                "error",
                f"S3_YANDEX_ENDPOINT is not a valid http(s) URL: "
                f"{settings.s3_yandex_endpoint!r}",
            )
        )

    if settings.instagram_cookies_file:
        if not os.path.isfile(settings.instagram_cookies_file):
            problems.append(
                (
                    "INSTAGRAM_COOKIES_FILE",
                    "warning",
                    f"INSTAGRAM_COOKIES_FILE {settings.instagram_cookies_file!r} "
                    "does not exist or is not a file.",
                )
            )
        elif not os.access(settings.instagram_cookies_file, os.R_OK):
            problems.append(
                (
                    "INSTAGRAM_COOKIES_FILE",
                    "warning",
                    f"INSTAGRAM_COOKIES_FILE {settings.instagram_cookies_file!r} "
                    "is not readable.",
                )
            )

    return problems
