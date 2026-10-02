# Production image for the FastAPI backend.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install dependencies first so Docker can cache this layer between code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Don't run as root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# --proxy-headers: trust the host's X-Forwarded-For so rate limits see the real client IP.
# Shell form so ${PORT} (set by the host) is expanded.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips="*"
