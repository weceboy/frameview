from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class AnalysisMode(str, Enum):
    TRANSCRIPT = "transcript"
    EFFICIENT = "efficient"
    BALANCED = "balanced"
    TOKEN_BURNER = "token-burner"


@dataclass(slots=True, frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass(slots=True)
class FrameCandidate:
    timestamp: float
    reason: list[str] = field(default_factory=list)
    score: float = 0.0
    path: str | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalysisManifest:
    source: str
    duration: float
    mode: AnalysisMode
    transcript: list[TranscriptSegment] = field(default_factory=list)
    frames: list[FrameCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "duration": self.duration,
            "mode": self.mode.value,
            "transcript": [asdict(s) for s in self.transcript],
            "frames": [frame.to_dict() for frame in self.frames],
            "metadata": self.metadata,
        }

    def write_json(self, path: str | Path) -> None:
        import json

        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
