"""Frameview: transcript-aware video frame selection and understanding."""

from .models import AnalysisManifest, AnalysisMode, FrameCandidate, TranscriptSegment
from .pipeline import analyze_video

__all__ = [
    "AnalysisManifest",
    "AnalysisMode",
    "FrameCandidate",
    "TranscriptSegment",
    "analyze_video",
]

__version__ = "0.2.0"
