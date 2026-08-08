# ---------- build stage ----------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements.txt .

RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /bot

COPY --from=builder /opt/venv /opt/venv
COPY bot.py /bot/

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /bot /opt/venv
USER appuser

CMD ["python", "bot.py"]