from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import AnalysisManifest, AnalysisMode, TranscriptSegment
from .select import select_frames
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
) -> AnalysisManifest:
    video = Path(video)
    if not video.exists():
        raise FileNotFoundError(video)

    transcript: list[TranscriptSegment] = []
    transcript_source = "none"
    if transcript_path:
        transcript = parse_transcript_file(transcript_path)
        transcript_source = str(transcript_path)
    elif mode != AnalysisMode.TRANSCRIPT or mode == AnalysisMode.TRANSCRIPT:
        # Captions are deliberately handled by the CLI/path when available. STT is an explicit fallback.
        try:
            transcript = transcribe_with_faster_whisper(video, stt_model)
            transcript_source = f"faster-whisper:{stt_model}"
        except RuntimeError:
            transcript_source = "unavailable"

    if mode == AnalysisMode.TRANSCRIPT:
        frames = []
        keyframe_count = 0
        scene_count = 0
    else:
        key_times = keyframes(video)
        keyframe_count = len(key_times)
        scene_times: list[float] = []
        if mode in (AnalysisMode.BALANCED, AnalysisMode.TOKEN_BURNER):
            scene_times = scene_change_times(video, scene_threshold)
        scene_count = len(scene_times)
        frames = select_frames(mode, key_times, scene_times, transcript)

    return AnalysisManifest(
        source=str(video),
        duration=duration(video),
        mode=mode,
        transcript=transcript,
        frames=frames,
        metadata={
            "transcript_source": transcript_source,
            "keyframe_count": keyframe_count,
            "scene_count": scene_count,
            "frame_count": len(frames),
            "scene_threshold": scene_threshold,
        },
    )
