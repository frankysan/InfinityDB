# syntax=docker/dockerfile:1
FROM python:3.11-slim

ARG INFINITY_DB_DISPLAY_VERSION=""

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INFINITY_DB_DB_DIR=/app/data \
    INFINITY_DB_DISPLAY_VERSION=${INFINITY_DB_DISPLAY_VERSION}

WORKDIR /app

# The application has no runtime dependency beyond Gunicorn. Copy its package
# sources plus the maintained config, documentation, and curated data needed while building
# the installed wheel; source snapshots and development artifacts stay out. Runtime
# databases are copied separately as a validated, versioned runtime bundle.
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY docs/CHANGELOG.md /app/docs/CHANGELOG.md
COPY config/catalogs /app/config/catalogs
COPY config/identity /app/config/identity
COPY config/validation /app/config/validation
COPY data/curated/identities /app/data/curated/identities
COPY data/curated/peripherals /app/data/curated/peripherals
COPY data/manifests/symbol-publication.json /app/data/manifests/symbol-publication.json
RUN pip install --no-cache-dir ".[server]" \
    && rm -rf /app/config /app/data/curated /app/docs /app/data/manifests \
    && python -c "import shutil,sys; from pathlib import Path; p=Path(sys.prefix)/'share/infinity-db'; shutil.rmtree(p/'config',ignore_errors=True); shutil.rmtree(p/'data',ignore_errors=True)" \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

# Package exactly the committed complete runtime set; no assembly directory.
COPY --chown=appuser:appuser data/generated/army.db /app/data/army.db
COPY --chown=appuser:appuser data/generated/rules_n5.db /app/data/rules_n5.db

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/internal/health', timeout=3)"

CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--error-logfile", "-", "infinity_db.web.wsgi:app"]
