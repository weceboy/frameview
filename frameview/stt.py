from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import TranscriptSegment


def transcribe_with_faster_whisper(path: str | Path, model_size: str = "small") -> list[TranscriptSegment]:
    """Optional local STT fallback; imported lazily so the core package stays lightweight."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Speech-to-text fallback requires the optional dependency: pip install -e '.[stt]'"
        ) from exc

    model = WhisperModel(model_size, compute_type="int8")
    segments, _info = model.transcribe(str(path), vad_filter=True)
    return [
        TranscriptSegment(float(segment.start), float(segment.end), str(segment.text).strip())
        for segment in segments
        if str(segment.text).strip()
    ]
