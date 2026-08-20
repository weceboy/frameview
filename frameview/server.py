from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .llm import analyze_manifest
from .models import AnalysisMode
from .pipeline import analyze_video
from .source import SourceError, resolve_source, is_url
from .video import extract_frames


DB_PATH = Path(os.getenv("FRAMEVIEW_DB", ".frameview/jobs.sqlite3"))
MAX_FRAMES = int(os.getenv("FRAMEVIEW_DEFAULT_MAX_FRAMES", "80"))
SERVER_KEY = os.getenv("FRAMEVIEW_SERVER_API_KEY")
WORK_ROOT = Path(os.getenv("FRAMEVIEW_WORKDIR", ".frameview/jobs"))

app = FastAPI(title="frameview", version="0.2.0")
_executor = ThreadPoolExecutor(max_workers=max(1, int(os.getenv("FRAMEVIEW_WORKERS", "2"))))
_db_lock = threading.Lock()


class WatchRequest(BaseModel):
    source: str = Field(min_length=1)
    mode: AnalysisMode = AnalysisMode.BALANCED
    transcript: str | None = None
    model: str = "gpt-4.1-mini"
    endpoint: str = "https://api.openai.com/v1/chat/completions"
    api_key: str | None = None
    max_frames: int = Field(default=MAX_FRAMES, ge=1, le=500)
    instruction: str = "Create a precise analysis of the video. Explain the main ideas, important visual moments, and how the visuals relate to what is being said. Preserve timestamps when useful."


class JobResponse(BaseModel):
    id: str
    status: str


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL, result TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_job(job_id: str, *, status: str | None = None, result: str | None = None, error: str | None = None) -> None:
    with _db_lock, sqlite3.connect(DB_PATH) as db:
        fields, values = ["updated_at = ?"], [_now()]
        if status is not None:
            fields.append("status = ?"); values.append(status)
        if result is not None:
            fields.append("result = ?"); values.append(result)
        if error is not None:
            fields.append("error = ?"); values.append(error)
        values.append(job_id)
        db.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()


def _get_job(job_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT id,status,payload,result,error,created_at,updated_at FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        return None
    return dict(zip(("id", "status", "payload", "result", "error", "created_at", "updated_at"), row))


def _authorize(authorization: str | None) -> None:
    if not SERVER_KEY:
        return
    expected = f"Bearer {SERVER_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _run_job(job_id: str, request: WatchRequest) -> None:
    _set_job(job_id, status="running")
    holder = None
    try:
        job_dir = WORK_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        video, caption, holder = resolve_source(request.source, workdir=job_dir / "source")
        transcript_path = request.transcript or (str(caption) if caption else None)
        manifest = analyze_video(video, mode=request.mode, transcript_path=transcript_path)
        frames_dir = job_dir / "frames"
        extract_frames(video, manifest.frames, frames_dir)
        result = analyze_manifest(
            manifest,
            api_key=request.api_key,
            endpoint=request.endpoint,
            model=request.model,
            max_frames=request.max_frames,
            instruction=request.instruction,
        )
        result["manifest"] = manifest.to_dict()
        with _db_lock, sqlite3.connect(DB_PATH) as db:
            db.execute("UPDATE jobs SET status = ?, result = ?, updated_at = ? WHERE id = ?", ("completed", __import__("json").dumps(result, ensure_ascii=False), _now(), job_id))
            db.commit()
    except Exception as exc:
        _set_job(job_id, status="failed", error=str(exc))
    finally:
        if holder is not None:
            holder.cleanup()


@app.on_event("startup")
def startup() -> None:
    _init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/watch", response_model=JobResponse, status_code=202)
def create_watch(request: WatchRequest, authorization: str | None = Header(default=None)) -> JobResponse:
    _authorize(authorization)
    if not is_url(request.source) and not Path(request.source).expanduser().exists():
        raise HTTPException(status_code=400, detail="Source file does not exist")
    job_id = uuid.uuid4().hex
    payload = request.model_dump_json()
    now = _now()
    with _db_lock, sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO jobs (id,status,payload,created_at,updated_at) VALUES (?, 'queued', ?, ?, ?)", (job_id, payload, now, now))
        db.commit()
    _executor.submit(_run_job, job_id, request)
    return JobResponse(id=job_id, status="queued")


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str, authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    response = {"id": job["id"], "status": job["status"], "created_at": job["created_at"], "updated_at": job["updated_at"]}
    if job["status"] == "completed":
        import json
        response["result"] = json.loads(job["result"])
    if job["status"] == "failed":
        response["error"] = job["error"]
    return response
