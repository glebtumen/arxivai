import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, validate_settings
from .database import Base, engine
from .routes import items

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="ArchiveBot API")

# NOTE: with allow_origins=["*"] the CORS spec forbids credentials, so we keep
# allow_credentials=False. We don't use cookies/sessions in this MVP anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)


@app.on_event("startup")
def _startup_checks():
    try:
        problems = validate_settings()
        if problems:
            logger.info(
                "Settings sanity-check finished: %d issue(s) found "
                "(%d error(s), %d warning(s)).",
                len(problems),
                sum(1 for _, lvl, _ in problems if lvl == "error"),
                sum(1 for _, lvl, _ in problems if lvl == "warning"),
            )
            for name, level, message in problems:
                if level == "error":
                    logger.error("[%s] %s", name, message)
                else:
                    logger.warning("[%s] %s", name, message)

            errors = [p for p in problems if p[1] == "error"]
            if errors and settings.fail_fast:
                raise SystemExit(
                    f"Backend cannot start due to {len(errors)} configuration "
                    "error(s) above (FAIL_FAST is enabled). Fix backend/.env "
                    "and restart."
                )
        else:
            logger.info("Settings sanity-check passed: all settings look good.")
    except SystemExit:
        raise
    except Exception as e:
        logger.error("Settings sanity-check failed: %s", e)

    logger.info("Media scratch directory: %s", os.path.abspath(settings.media_dir))


@app.get("/health")
def health():
    problems = validate_settings()
    problem_status = {
        name: "error" if level == "error" else "warning"
        for name, level, _ in problems
    }
    all_setting_names = (
        "DATABASE_URL",
        "MEDIA_DIR",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_WHISPER_MODEL",
        "SITE_URL",
        "WEB_BASE_URL",
        "API_BASE_URL",
        "INSTAGRAM_COOKIES_FILE",
        "S3_YANDEX_ENDPOINT",
        "S3_YANDEX_REGION",
        "S3_YANDEX_IDENT_KEY",
        "S3_YANDEX_SECRET_KEY",
        "S3_YANDEX_BUCKET",
    )
    settings_status = {
        name: problem_status.get(name, "ok") for name in all_setting_names
    }
    has_errors = any(status == "error" for status in settings_status.values())
    return {
        "status": "degraded" if has_errors else "ok",
        "settings": settings_status,
    }
