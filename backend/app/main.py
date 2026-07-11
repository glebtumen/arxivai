import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
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

media_dir = os.path.abspath(settings.media_dir)
os.makedirs(media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")

app.include_router(items.router)


@app.on_event("startup")
def _startup_checks():
    if not settings.openrouter_api_key:
        logger.warning(
            "OPENROUTER_API_KEY is not set. AI analysis will fail until you "
            "set it in backend/.env"
        )
    logger.info("Media directory: %s", media_dir)


@app.get("/health")
def health():
    return {"status": "ok"}
