from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import TranscriptSegment

_TIME = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})(?:[,.](?P<ms>\d{3}))?")
_VISUAL_PATTERNS = (
    re.compile(r"\blook\s+(?:here|at|over here)\b", re.I),
    re.compile(r"\bas you can see\b", re.I),
    re.compile(r"\bwatch (?:this|that)\b", re.I),
    re.compile(r"\bright here\b", re.I),
    re.compile(r"\bon (?:the|your) screen\b", re.I),
    re.compile(r"\bsee (?:this|that|here)\b", re.I),
    re.compile(r"\bwhat happens\b", re.I),
)


def _timecode(value: str) -> float:
    match = _TIME.search(value)
    if not match:
        raise ValueError(f"Invalid timestamp: {value}")
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    millis = int(match.group("ms") or 0)
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def parse_srt(text: str) -> list[TranscriptSegment]:
    blocks = re.split(r"\n\s*\n", text.strip())
    segments: list[TranscriptSegment] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        timing_index = 0 if "-->" in lines[0] else 1 if len(lines) > 1 and "-->" in lines[1] else -1
        if timing_index < 0:
            continue
        start_raw, end_raw = [part.strip() for part in lines[timing_index].split("-->", 1)]
        text_lines = lines[timing_index + 1 :]
        if not text_lines:
            continue
        segments.append(
            TranscriptSegment(_timecode(start_raw), _timecode(end_raw), " ".join(text_lines))
        )
    return segments


def parse_vtt(text: str) -> list[TranscriptSegment]:
    clean = re.sub(r"^WEBVTT.*?(?:\n\n|\Z)", "", text, flags=re.I | re.S)
    return parse_srt(clean)


def parse_transcript_file(path: str | Path) -> list[TranscriptSegment]:
    raw = Path(path).read_text(encoding="utf-8-sig")
    return parse_vtt(raw) if Path(path).suffix.lower() == ".vtt" else parse_srt(raw)


def contains_visual_reference(text: str) -> bool:
    return any(pattern.search(text) for pattern in _VISUAL_PATTERNS)


def visual_reference_segments(segments: Iterable[TranscriptSegment]) -> list[TranscriptSegment]:
    return [segment for segment in segments if contains_visual_reference(segment.text)]
