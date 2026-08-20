from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

from .models import AnalysisManifest, FrameCandidate

DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4.1-mini"


def _image_data_url(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _frame_context(frames: Iterable[FrameCandidate]) -> list[dict]:
    result: list[dict] = []
    for frame in frames:
        item = {"timestamp": frame.timestamp, "reasons": frame.reason}
        if frame.path:
            item["image"] = _image_data_url(frame.path)
        result.append(item)
    return result


def analyze_manifest(
    manifest: AnalysisManifest,
    *,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    max_frames: int | None = None,
    instruction: str = "Create a precise analysis of the video. Explain the main ideas, important visual moments, and how the visuals relate to what is being said. Preserve timestamps when useful.",
) -> dict:
    key = api_key or os.getenv("FRAMEVIEW_API_KEY")
    if not key:
        raise RuntimeError("Missing API key. Set FRAMEVIEW_API_KEY or pass --api-key.")

    selected = list(manifest.frames)
    if max_frames is not None:
        if max_frames < 1:
            raise ValueError("max_frames must be positive")
        selected = selected[:max_frames]

    content: list[dict] = [{"type": "text", "text": instruction}]
    transcript_text = "\n".join(
        f"[{segment.start:.3f}-{segment.end:.3f}] {segment.text}" for segment in manifest.transcript
    )
    content.append({
        "type": "text",
        "text": f"Video duration: {manifest.duration:.3f}s\nMode: {manifest.mode.value}\n\nTranscript:\n{transcript_text}",
    })

    for frame in _frame_context(selected):
        content.append({
            "type": "text",
            "text": f"Frame at {frame['timestamp']:.3f}s; reasons: {', '.join(frame['reasons']) or 'selected'}",
        })
        if "image" in frame:
            content.append({"type": "image_url", "image_url": {"url": frame["image"]}})

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": content}],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model endpoint returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach model endpoint: {exc.reason}") from exc

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Unexpected model response: missing choices[0].message.content") from exc

    return {
        "model": model,
        "endpoint": endpoint,
        "analysis": text,
        "frame_count": len(selected),
    }
