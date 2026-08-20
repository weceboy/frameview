from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable

from PIL import Image

from .models import AnalysisMode, FrameCandidate, TranscriptSegment
from .transcript import visual_reference_segments


def merge_candidates(*groups: Iterable[FrameCandidate], tolerance: float = 0.35) -> list[FrameCandidate]:
    merged: list[FrameCandidate] = []
    for candidate in sorted((c for group in groups for c in group), key=lambda c: c.timestamp):
        existing = next((item for item in reversed(merged) if abs(item.timestamp - candidate.timestamp) <= tolerance), None)
        if existing:
            for reason in candidate.reason:
                if reason not in existing.reason:
                    existing.reason.append(reason)
            existing.score = max(existing.score, candidate.score)
        else:
            merged.append(candidate)
    return merged


def candidates_from_times(times: Iterable[float], reason: str, score: float) -> list[FrameCandidate]:
    return [FrameCandidate(float(t), [reason], score) for t in times]


def transcript_visual_candidates(segments: Iterable[TranscriptSegment]) -> list[FrameCandidate]:
    return [
        FrameCandidate(
            timestamp=(segment.start + segment.end) / 2,
            reason=["visual_reference"],
            score=0.85,
        )
        for segment in visual_reference_segments(segments)
    ]


def _ahash(path: str | Path, size: int = 16) -> int:
    image = Image.open(path).convert("L").resize((size, size))
    pixels = list(image.getdata())
    avg = sum(pixels) / len(pixels)
    value = 0
    for pixel in pixels:
        value = (value << 1) | int(pixel >= avg)
    return value


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def deduplicate_frames(frames: list[FrameCandidate], *, max_distance: int = 12) -> list[FrameCandidate]:
    """Deduplicate already-extracted frames using a lightweight average hash.

    Frames without a local path cannot be image-compared and are retained.
    """
    kept: list[FrameCandidate] = []
    hashes: list[int] = []
    for frame in sorted(frames, key=lambda item: (-item.score, item.timestamp)):
        if not frame.path or not Path(frame.path).exists():
            kept.append(frame)
            continue
        digest = _ahash(frame.path)
        if any(_hamming(digest, previous) <= max_distance for previous in hashes):
            continue
        frame.content_hash = format(digest, "x")
        hashes.append(digest)
        kept.append(frame)
    return sorted(kept, key=lambda item: item.timestamp)


def select_frames(
    mode: AnalysisMode,
    keyframe_times: Iterable[float],
    scene_times: Iterable[float] = (),
    transcript: Iterable[TranscriptSegment] = (),
) -> list[FrameCandidate]:
    keyframes = candidates_from_times(keyframe_times, "keyframe", 0.35)
    if mode == AnalysisMode.TRANSCRIPT:
        return []
    if mode == AnalysisMode.EFFICIENT:
        return keyframes

    scenes = candidates_from_times(scene_times, "scene_change", 0.9)
    visual = transcript_visual_candidates(transcript)
    if mode == AnalysisMode.BALANCED:
        return merge_candidates(keyframes, scenes, visual)
    return merge_candidates(keyframes, scenes, visual, tolerance=0.10)
