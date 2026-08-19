import asyncio
import html
import logging
import os
import re
from urllib.parse import urlparse

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    BufferedInputFile,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Raw env values --------------------------------------------------------
# Read everything with a safe default ("") so a missing var never raises
# AttributeError (os.getenv(...) returns None if unset, and None has no
# .rstrip()). validate_settings() below reports anything that's missing or
# malformed with a clear message instead of a stack trace.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "").strip().rstrip("/")
WEB_BASE_URL = os.getenv("BOT_WEB_BASE_URL", "").strip().rstrip("/")
# Optional: set this if Telegram's API is blocked/slow on your network, e.g.
# TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080  or  http://user:pass@host:port
TELEGRAM_PROXY_URL = os.getenv("TELEGRAM_PROXY_URL", "").strip() or None
# Seconds to wait for a response from Telegram before retrying.
_DEFAULT_TIMEOUT = 60.0
_raw_timeout = os.getenv("TELEGRAM_REQUEST_TIMEOUT", str(_DEFAULT_TIMEOUT)).strip()


def _is_valid_url(value: str) -> bool:
    """Return True if value is a non-empty, parseable http(s) URL."""
    if not value:
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _is_valid_proxy_url(value: str) -> bool:
    """Return True if value is a non-empty, parseable proxy URL."""
    if not value:
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("socks5", "socks5h", "http", "https") and bool(
        parsed.netloc
    )


def _parse_timeout(raw: str) -> tuple[float, list[tuple[str, str, str]]]:
    """Parse TELEGRAM_REQUEST_TIMEOUT, falling back to the default on error."""
    problems: list[tuple[str, str, str]] = []
    try:
        value = float(raw)
        if value <= 0:
            raise ValueError("must be positive")
        return value, problems
    except ValueError:
        problems.append(
            (
                "TELEGRAM_REQUEST_TIMEOUT",
                "warning",
                f"TELEGRAM_REQUEST_TIMEOUT {raw!r} is not a positive number. "
                f"Falling back to the default ({_DEFAULT_TIMEOUT}s).",
            )
        )
        return _DEFAULT_TIMEOUT, problems


TELEGRAM_REQUEST_TIMEOUT, _timeout_problems = _parse_timeout(_raw_timeout)


def validate_settings() -> list[tuple[str, str, str]]:
    """Run sanity checks on the loaded bot settings.

    Returns a list of (setting_name, level, message) tuples where level is
    "error" for settings that will break core functionality (the bot cannot
    run without them) and "warning" for settings that degrade optional
    features or fall back to a default.
    """
    problems: list[tuple[str, str, str]] = list(_timeout_problems)

    if not TELEGRAM_BOT_TOKEN:
        problems.append(
            (
                "TELEGRAM_BOT_TOKEN",
                "error",
                "TELEGRAM_BOT_TOKEN is not set. Copy bot/.env.example to "
                "bot/.env and fill it in.",
            )
        )

    if not API_BASE_URL:
        problems.append(
            (
                "API_BASE_URL",
                "error",
                "API_BASE_URL is not set. The bot cannot reach the backend "
                "without it. Set it in bot/.env.",
            )
        )
    elif not _is_valid_url(API_BASE_URL):
        problems.append(
            (
                "API_BASE_URL",
                "error",
                f"API_BASE_URL is not a valid http(s) URL: {API_BASE_URL!r}",
            )
        )

    if not WEB_BASE_URL:
        problems.append(
            (
                "BOT_WEB_BASE_URL",
                "error",
                "BOT_WEB_BASE_URL is not set. The bot cannot link users to "
                "the web library without it. Set it in bot/.env.",
            )
        )
    elif not _is_valid_url(WEB_BASE_URL):
        problems.append(
            (
                "BOT_WEB_BASE_URL",
                "error",
                f"BOT_WEB_BASE_URL is not a valid http(s) URL: {WEB_BASE_URL!r}",
            )
        )

    if TELEGRAM_PROXY_URL and not _is_valid_proxy_url(TELEGRAM_PROXY_URL):
        problems.append(
            (
                "TELEGRAM_PROXY_URL",
                "warning",
                f"TELEGRAM_PROXY_URL {TELEGRAM_PROXY_URL!r} does not look like "
                "a valid proxy URL (expected scheme socks5/socks5h/http/https). "
                "The bot may fail to connect to Telegram.",
            )
        )

    return problems


_problems = validate_settings()
if _problems:
    logger.info(
        "Bot settings sanity-check finished: %d issue(s) found "
        "(%d error(s), %d warning(s)).",
        len(_problems),
        sum(1 for _, lvl, _ in _problems if lvl == "error"),
        sum(1 for _, lvl, _ in _problems if lvl == "warning"),
    )
    for _name, _level, _message in _problems:
        if _level == "error":
            logger.error("[%s] %s", _name, _message)
        else:
            logger.warning("[%s] %s", _name, _message)
else:
    logger.info("Bot settings sanity-check passed: all settings look good.")

_errors = [p for p in _problems if p[1] == "error"]
if _errors:
    raise SystemExit(
        "Bot cannot start due to " + str(len(_errors)) + " configuration "
        "error(s) above. Copy bot/.env.example to bot/.env and fill it in."
    )

session = AiohttpSession(proxy=TELEGRAM_PROXY_URL, timeout=TELEGRAM_REQUEST_TIMEOUT)

bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

URL_RE = re.compile(r"https?://\S+")


@dp.message(CommandStart())
async def on_start(message: Message):
    await message.answer(
        "👋 Hi! Send me an Instagram link (Reel/post) and I'll analyze it: "
        "extract key frames, write a summary and tag it for your library."
    )


@dp.message(F.text)
async def on_link(message: Message):
    if message.from_user is None:
        return

    text = message.text or ""
    match = URL_RE.search(text)
    if not match:
        await message.answer("Please send a valid link (e.g. an Instagram Reel URL).")
        return

    url = match.group(0)
    telegram_user_id = message.from_user.id

    try:

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{API_BASE_URL}/items",
                json={"telegram_user_id": telegram_user_id, "url": url},
            )
            resp.raise_for_status()
            item = resp.json()
            item_id = item.get("id")

            status_msg = await message.answer("📥 Queued. Analyzing…")
            # poll every ~2s until status is done/failed, with an overall timeout
            STAGE_LABELS = {
                "queued": "⏳ Queued…",
                "downloading": "📥 Downloading…",
                "extracting_frames": "🖼 Extracting frames…",
                "transcribing": "🎙 Transcribing audio…",
                "summarizing": "🧠 Summarizing with AI…",
            }
            last_shown = None
            for _ in range(150):  # ~5 min max
                await asyncio.sleep(2)
                r = await client.get(f"{API_BASE_URL}/items/{item_id}")
                item = r.json()
                status = item["status"]
                if status in ("done", "failed"):
                    break
                label = STAGE_LABELS.get(status, f"⏳ {status}…")
                if label != last_shown:
                    await status_msg.edit_text(label)
                    last_shown = label
            else:
                await status_msg.edit_text("⌛ Still processing — this is taking a while.")
                return

            # Download frame bytes now (while the client is open) so we can
            # upload them directly to Telegram regardless of network topology.
            frame_files: list[BufferedInputFile] = []
            for i, frame_url in enumerate(item.get("frame_paths") or []):
                try:
                    fr = await client.get(frame_url)
                    fr.raise_for_status()
                    frame_files.append(
                        BufferedInputFile(fr.content, filename=f"frame_{i}.jpg")
                    )
                except Exception:
                    logger.warning("Could not fetch frame %s", frame_url)

    except Exception as e:
        logger.exception("Failed to process item")
        await status_msg.edit_text(
            f"❌ Something went wrong contacting the backend: {html.escape(str(e))}"
        )
        return

    if item.get("status") == "failed":
        error = item.get("error_message") or "Unknown error"
        await status_msg.edit_text(
            f"❌ Couldn't process this link.\n{html.escape(error)}"
        )
        return

    title = html.escape(item.get("title") or "Untitled")
    summary = html.escape(item.get("summary") or "No summary.")
    tags = item.get("tags") or []
    if tags:
        tags_str = ", ".join(f"#{html.escape(t.replace(' ', '_'))}" for t in tags)
    else:
        tags_str = "No tags"

    card_text = (
        f"✅ Done!\n\n"
        f"📌 <b>{title}</b>\n\n"
        f"📝 {summary}\n\n"
        f"🏷 {tags_str}"
    )

    web_url = f"{WEB_BASE_URL}/item/{item_id}"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📂 Open Library", url=web_url)]]
    )

    await status_msg.edit_text(card_text)

    # Send the 3 frames as a media group / album by uploading the bytes we
    # fetched from the backend earlier (robust for local dev where Telegram
    # cannot reach a localhost URL).
    if frame_files:
        media = [InputMediaPhoto(media=f) for f in frame_files]
        try:
            await bot.send_media_group(chat_id=message.chat.id, media=media)
        except Exception:
            logger.exception("Failed to send frame album")

    await message.answer(
        "Open your library to see the full card:", reply_markup=keyboard
    )


async def main():
    # Retry loop: if Telegram's API is unreachable (network blocked, DNS
    # issues, etc.) keep retrying with backoff instead of crashing the whole
    # process. Very common when running from networks where Telegram is
    # throttled - set TELEGRAM_PROXY_URL in bot/.env to fix it permanently.
    backoff = 5
    max_backoff = 60
    while True:
        try:
            logger.info("Starting bot polling...")
            await dp.start_polling(bot)
            break  # start_polling returned normally (e.g. shutdown signal)
        except TelegramNetworkError as e:
            logger.error(
                "Network error talking to Telegram (%s). Retrying in %ss. "
                "If this keeps happening, Telegram may be blocked on this "
                "network - set TELEGRAM_PROXY_URL in bot/.env.",
                e,
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
        except (asyncio.CancelledError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    asyncio.run(main())
