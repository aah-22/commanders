# One Python image serves the read-only API and runs the scheduled jobs (ingest, models) as Coolify tasks.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data TZ=America/New_York
WORKDIR /srv

RUN adduser --disabled-password --gecos "" --uid 10001 app && mkdir -p /data && chown app:app /data

COPY pyproject.toml alembic.ini ./
COPY api ./api
COPY ingest ./ingest
COPY models ./models
COPY db ./db
# Installing the package (not just requirements) registers the MLflow header-provider entry point.
RUN pip install --no-cache-dir ".[pipeline,models]"

USER app
VOLUME ["/data"]
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8081/health', timeout=2).status == 200 else 1)"

CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8081 --proxy-headers --forwarded-allow-ips=*"]
