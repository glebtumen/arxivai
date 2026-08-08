"""Generates title, summary and tags using an LLM via OpenRouter (OpenAI SDK)."""

import json
import logging

from openai import OpenAI

from ..config import settings
from ..tags import FIXED_TAGS

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )


def _fallback(title: str, description: str) -> dict:
    return {
        "title": title or "Untitled",
        "summary": (description[:280] if description else "No summary available."),
        "tags": [],
    }


def analyze_content(title: str, description: str, transcript: str = "") -> dict:
    """
    Calls the LLM with the video title/description (caption) and the spoken
    transcript, and returns:
        {"title": str, "summary": str, "tags": list[str]}
    Tags are constrained to FIXED_TAGS. Never raises: degrades gracefully.
    """
    if not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY missing; skipping AI analysis.")
        return _fallback(title, description)

    client = _get_client()
    tags_list_str = ", ".join(FIXED_TAGS)

    system_prompt = (
        "You are a content classification assistant for a personal media "
        "knowledge base. You are given a video's original title, its caption/"
        "description text, and a transcript of what is spoken in the video. "
        "Use all of them together to understand the content. Respond with "
        "STRICT JSON only, no markdown, no extra commentary, in this exact "
        "shape:\n"
        '{"title": "short catchy title (max 8 words)", '
        '"summary": "summary of what the content is about, if its recipie then do recipie, if its a tutorial then make full tutorial, make it understandable to know what the content is about", '
        '"tags": ["tag1", "tag2", "tag3"]}\n\n'
        f"Tags MUST be chosen only from this fixed list, pick 1 to 3 most "
        f"relevant tags: {tags_list_str}"
    )

    user_content = (
        f"Original title: {title or '(none)'}\n"
        f"Description/caption: {description or '(none)'}\n"
        f"Spoken transcript: {transcript or '(none)'}"
    )

    try:
        completion = client.chat.completions.create(
            model=settings.openrouter_model,
            stream=False,
            response_format={"type": "json_object"},
            extra_headers={
                "HTTP-Referer": settings.site_url,
                "X-Title": settings.site_title,
            },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
    except Exception as e:
        logger.exception("LLM request failed: %s", e)
        return _fallback(title, description)

    # Content can be None if the model returned nothing / only tool calls.
    message = completion.choices[0].message if completion.choices else None
    raw = (message.content if message else None) or ""
    raw = raw.strip()

    # Strip accidental markdown code fences if the model adds them.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON output: %r", raw[:200])
        data = _fallback(title, description)

    # Sanitize tags against the fixed list (dedupe, keep order).
    seen = set()
    tags = []
    for t in data.get("tags", []) or []:
        if t in FIXED_TAGS and t not in seen:
            seen.add(t)
            tags.append(t)

    return {
        "title": (data.get("title") or title or "Untitled").strip(),
        "summary": (data.get("summary") or "").strip(),
        "tags": tags,
    }
