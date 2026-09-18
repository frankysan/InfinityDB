# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INFINITY_DB_DATABASE=/app/data/infinity.db \
    INFINITY_DB_RULES_DATABASE=/app/data/rules.db

WORKDIR /app

# The application has no runtime dependency beyond Gunicorn. Copy only its
# runtime inputs; source snapshots and development artifacts stay out of the
# image. Runtime databases are copied separately as versioned release data.
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --no-cache-dir ".[server]" \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser data/generated/infinity.db /app/data/infinity.db
COPY --chown=appuser:appuser data/generated/rules.db /app/data/rules.db

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/armies', timeout=3)"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "infinity_db.web.wsgi:app"]
