FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRAMEVIEW_WORKDIR=/data/jobs \
    FRAMEVIEW_DB=/data/jobs/jobs.sqlite3

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY frameview ./frameview

RUN pip install --no-cache-dir -e '.[server,url]'

RUN useradd --create-home --uid 10001 frameview \
    && mkdir -p /data/jobs \
    && chown -R frameview:frameview /data/jobs /app
USER frameview

EXPOSE 8000
CMD ["uvicorn", "frameview.server:app", "--host", "0.0.0.0", "--port", "8000"]
