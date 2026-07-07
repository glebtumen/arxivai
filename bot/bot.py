import asyncio
import html
import logging
import os
import re

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

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
WEB_BASE_URL = os.getenv("WEB_BASE_URL", "http://localhost:3000").rstrip("/")
# Optional: set this if Telegram's API is blocked/slow on your network, e.g.
# TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080  or  http://user:pass@host:port
TELEGRAM_PROXY_URL = os.getenv("TELEGRAM_PROXY_URL", "").strip() or None
# Seconds to wait for a response from Telegram before retrying.
TELEGRAM_REQUEST_TIMEOUT = float(os.getenv("TELEGRAM_REQUEST_TIMEOUT", "60"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit(
        "TELEGRAM_BOT_TOKEN is not set. Copy bot/.env.example to bot/.env and "
        "fill it in."
    )

session = AiohttpSession(proxy=TELEGRAM_PROXY_URL, timeout=TELEGRAM_REQUEST_TIMEOUT)

bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

URL_RE = re.compile(r"https?://\S+")


def _media_url(rel_path: str) -> str:
    return f"{API_BASE_URL}/media/{rel_path}"


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

    status_msg = await message.answer("📥 Received. Starting analysis...")

    try:
        await status_msg.edit_text(
            "🔎 Analyzing (downloading, extracting frames, asking AI)..."
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{API_BASE_URL}/items",
                json={"telegram_user_id": telegram_user_id, "url": url},
            )
            resp.raise_for_status()
            item = resp.json()

            # Download frame bytes now (while the client is open) so we can
            # upload them directly to Telegram regardless of network topology.
            frame_files: list[BufferedInputFile] = []
            for i, rel_path in enumerate(item.get("frame_paths") or []):
                try:
                    fr = await client.get(_media_url(rel_path))
                    fr.raise_for_status()
                    frame_files.append(
                        BufferedInputFile(fr.content, filename=f"frame_{i}.jpg")
                    )
                except Exception:
                    logger.warning("Could not fetch frame %s", rel_path)

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

    item_id = item.get("id")
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
