# ArchiveBot — AI Content Archiver (MVP v1)

Send an Instagram link to a Telegram bot. It downloads the video, extracts 3
key frames (start/middle/end) with ffmpeg, asks an LLM (via OpenRouter) for a
title, summary, and tags, and saves it to your personal library — viewable in
a simple Next.js web app.

## Stack
Python, FastAPI, aiogram, PostgreSQL, ffmpeg, yt-dlp, OpenRouter (OpenAI SDK), Next.js + Tailwind.

## Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for Postgres) — or your own local Postgres instance
- `ffmpeg` installed and on PATH
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- OpenRouter API key from [openrouter.ai](https://openrouter.ai)

## 1. Start Postgres
```bash
cd archivebot
docker compose up -d
```

## 2. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000
```

## 3. Telegram bot
```bash
cd bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN
python bot.py
```

## 4. Web app
```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev
```
Open http://localhost:3000

## How it works
1. Send an Instagram link to the bot in Telegram.
2. Bot replies "Received" → "Analyzing" → "Done".
3. Backend downloads the video (yt-dlp), extracts 3 frames (ffmpeg),
   transcribes the audio with Whisper (`openai/whisper-large-v3` via
   OpenRouter), and calls the LLM for title/summary/tags using the caption +
   transcript together (tags from a fixed 16-tag list).
4. Bot sends the card + 3 frames + "Open Library" button.
5. Web app lists all saved items; click a card to see the full board.

## Notes / limitations (v1)
- Instagram may block some downloads (private accounts, rate limits) — the
  bot will report a friendly error in that case. See "Instagram login
  required" below for the fix.

- Processing is synchronous (no queue yet) — a link may take ~10-30s.
- Tags are a fixed list; users cannot add custom tags in this iteration.
- Media is stored locally in `storage/media/` (no S3 yet).
- No login/auth yet — the web app is open, single-tenant for now.

## Database schema changes

There are no migrations (Alembic) yet — tables are auto-created on startup via
`Base.metadata.create_all`, which only creates *missing* tables, it does not
alter existing ones. So when a new column is added (e.g. `transcript`), you
need to recreate the DB. Since this is local test data:

```bash
docker compose down -v   # wipes the Postgres volume
docker compose up -d     # fresh DB, new schema created on next backend start
```

## Troubleshooting

**`aiogram.exceptions.TelegramNetworkError: Request timeout error` on startup**
This means the bot process can't reach `api.telegram.org` — it's a network
issue, not a code bug. Telegram is blocked/throttled on some networks/ISPs
(common in certain countries). Fixes:
1. Try a VPN, or
2. Set a proxy in `bot/.env`:
   ```
   TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
   ```
   (for a SOCKS5 proxy, also run `pip install aiohttp-socks`), or
   ```
   TELEGRAM_PROXY_URL=http://user:pass@host:port
   ```
   for an HTTP proxy.
3. The bot now automatically retries with backoff instead of crashing, so it
   will keep trying to reconnect once the network/proxy is fixed.

**Instagram login required / "Requested content is not available, rate-limit
reached or login required"**
Instagram now frequently blocks anonymous (not-logged-in) downloads. Fix it
by giving yt-dlp your own logged-in session via a cookies file:

1. Install a browser extension like "Get cookies.txt LOCALLY" and, while
   logged into instagram.com, export cookies in **Netscape format**.
2. Save the exported file as `backend/instagram_cookies.txt` (this path is
   already git-ignored, so it won't be committed).
3. Set `INSTAGRAM_COOKIES_FILE=instagram_cookies.txt` in `backend/.env`
   (already set by default if you copied `.env.example`).
4. Restart the backend (`uvicorn app.main:app --reload --port 8000`).

Notes:
- The cookies file contains your session token — never commit it or share
  it. Treat it like a password.
- Sessions expire periodically; if downloads start failing again later,
  re-export a fresh cookies file the same way.
- You can quickly test the downloader in isolation with
  `python test/testdownload.py <url> --cookies backend/instagram_cookies.txt`.
