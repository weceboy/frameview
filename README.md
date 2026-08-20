# frameview

Production-oriented video understanding based on transcript-aware frame selection.

## What it does

frameview combines:

- existing captions when available
- optional local speech-to-text with `faster-whisper`
- efficient keyframe extraction
- scene-change detection
- transcript-guided visual references such as “look here” / “as you can see”
- lightweight frame deduplication
- multimodal LLM analysis

The pipeline is local-first: video decoding and frame selection happen locally, while only the selected transcript and frames are sent to the configured model endpoint.

## Install

Core + API server + URL support:

```bash
pip install -e '.[server,url]'
```

For local STT too:

```bash
pip install -e '.[all]'
```

System requirement: FFmpeg (`ffmpeg` and `ffprobe`) must be on `PATH`.

## CLI

Local file:

```bash
frameview analyze ./video.mp4 --mode balanced --output analysis.json
```

Remote URL:

```bash
frameview understand 'https://example.com/video' --mode balanced --max-frames 80
```

The `understand` command needs `FRAMEVIEW_API_KEY` unless `--api-key` is supplied.

## HTTP API

Start locally:

```bash
uvicorn frameview.server:app --host 0.0.0.0 --port 8000
```

Optional API protection:

```bash
export FRAMEVIEW_SERVER_API_KEY='change-me'
export FRAMEVIEW_API_KEY='model-secret'
```

Create a job:

```bash
curl -X POST http://localhost:8000/v1/watch \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer change-me' \
  -d '{"source":"https://www.youtube.com/watch?v=...","mode":"balanced"}'
```

Poll it:

```bash
curl http://localhost:8000/v1/jobs/JOB_ID \
  -H 'Authorization: Bearer change-me'
```

The server uses SQLite for durable job metadata and a bounded local worker pool. It is intended for a single application instance. For multi-instance deployments, place the API behind a queue/worker system rather than relying on the in-process executor.

## Production configuration

Important environment variables:

```text
FRAMEVIEW_SERVER_API_KEY       API auth; unset disables API auth
FRAMEVIEW_API_KEY              model provider key
FRAMEVIEW_LLM_ENDPOINT         server-owned OpenAI-compatible endpoint
FRAMEVIEW_WORKERS              in-process concurrent jobs (default 2)
FRAMEVIEW_WORKDIR              job/video storage root
FRAMEVIEW_DB                   SQLite path
FRAMEVIEW_MAX_DURATION_SECONDS maximum remote video duration (default 10800)
FRAMEVIEW_MAX_DOWNLOAD_BYTES  maximum remote download size (default 4 GiB)
FRAMEVIEW_ALLOWED_HOSTS        optional comma-separated remote host allowlist
```

The LLM endpoint is deliberately server-configured rather than accepted from clients, so a caller cannot redirect the server-side model secret to an arbitrary endpoint.

Remote URL ingestion validates destination IPs and refuses loopback, private, link-local, multicast, reserved, and unspecified addresses. For a hardened deployment, use `FRAMEVIEW_ALLOWED_HOSTS` as an explicit allowlist.

## Docker

```bash
docker compose up --build
```

Persistent data lives in the `frameview-data` volume.

## Architecture

```text
URL / local file
      │
      ├── captions first
      │      └── STT fallback
      │
      └── video
            ├── keyframes
            ├── scene changes
            └── transcript visual references
                       ↓
                  merge + dedupe
                       ↓
                timestamp manifest
                       ↓
                selected JPEG frames
                       ↓
                 multimodal LLM
                       ↓
                    result
```

The current implementation intentionally keeps the LLM transport OpenAI-compatible. That makes the analysis layer usable with OpenAI and compatible gateways without coupling the frame-selection engine to one vendor.
