from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable

from .models import FrameCandidate


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(args, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required executable not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.strip() or "Command failed") from exc
    return result.stdout


def probe(path: str | Path) -> dict:
    output = _run([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)
    ])
    return json.loads(output)


def duration(path: str | Path) -> float:
    data = probe(path)
    return float(data.get("format", {}).get("duration", 0.0))


def keyframes(path: str | Path) -> list[float]:
    output = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey",
        "-show_frames", "-show_entries", "frame=best_effort_timestamp_time",
        "-of", "csv=p=0", str(path)
    ])
    frames: list[float] = []
    for line in output.splitlines():
        line = line.strip()
        if line:
            try:
                frames.append(float(line.split(",", 1)[0]))
            except ValueError:
                continue
    return frames


def scene_change_times(path: str | Path, threshold: float = 0.34) -> list[float]:
    # FFmpeg's scene score is metadata produced by the `select` filter.
    # We sample only frames that cross the configured threshold and retain timestamps.
    output = _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"
    ])
    times: list[float] = []
    for line in output.splitlines():
        marker = "pts_time:"
        if marker in line:
            raw = line.split(marker, 1)[1].split()[0]
            try:
                times.append(float(raw))
            except ValueError:
                pass
    return times


def extract_frame(path: str | Path, timestamp: float, output: str | Path) -> None:
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}",
        "-i", str(path), "-frames:v", "1", "-q:v", "2", "-y", str(output)
    ])


def extract_frames(path: str | Path, frames: Iterable[FrameCandidate], output_dir: str | Path) -> None:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    for frame in frames:
        filename = directory / f"frame-{frame.timestamp:010.3f}.jpg"
        extract_frame(path, frame.timestamp, filename)
        frame.path = str(filename)
