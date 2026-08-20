from __future__ import annotations

from pathlib import Path

from .models import AnalysisManifest, AnalysisMode, TranscriptSegment
from .select import select_frames
from .source import resolve_source
from .stt import transcribe_with_faster_whisper
from .transcript import parse_transcript_file
from .video import duration, keyframes, scene_change_times


def analyze_video(
    video: str | Path,
    *,
    mode: AnalysisMode = AnalysisMode.BALANCED,
    transcript_path: str | Path | None = None,
    stt_model: str = "small",
    scene_threshold: float = 0.34,
    workdir: str | Path | None = None,
) -> AnalysisManifest:
    resolved, downloaded_caption, holder = resolve_source(str(video), workdir=workdir)
    try:
        transcript: list[TranscriptSegment] = []
        transcript_source = "none"
        effective_transcript = transcript_path or downloaded_caption
        if effective_transcript:
            transcript = parse_transcript_file(effective_transcript)
            transcript_source = str(effective_transcript)
        else:
            try:
                transcript = transcribe_with_faster_whisper(resolved, stt_model)
                transcript_source = f"faster-whisper:{stt_model}"
            except RuntimeError:
                transcript_source = "unavailable"

        if mode == AnalysisMode.TRANSCRIPT:
            frames = []
            keyframe_count = 0
            scene_count = 0
        else:
            key_times = keyframes(resolved)
            keyframe_count = len(key_times)
            scene_times: list[float] = []
            if mode in (AnalysisMode.BALANCED, AnalysisMode.TOKEN_BURNER):
                scene_times = scene_change_times(resolved, scene_threshold)
            scene_count = len(scene_times)
            frames = select_frames(mode, key_times, scene_times, transcript)

        return AnalysisManifest(
            source=str(video),
            duration=duration(resolved),
            mode=mode,
            transcript=transcript,
            frames=frames,
            metadata={
                "resolved_source": str(resolved),
                "transcript_source": transcript_source,
                "keyframe_count": keyframe_count,
                "scene_count": scene_count,
                "frame_count": len(frames),
                "scene_threshold": scene_threshold,
            },
        )
    finally:
        if holder is not None:
            holder.cleanup()
