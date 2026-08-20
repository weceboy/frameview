from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .llm import analyze_manifest
from .models import AnalysisMode
from .pipeline import analyze_video
from .video import extract_frames


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="frameview", description="Transcript-aware video analysis")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="analyze a video and write a JSON manifest")
    analyze.add_argument("video")
    analyze.add_argument("--mode", choices=[mode.value for mode in AnalysisMode], default="balanced")
    analyze.add_argument("--transcript", help="optional SRT/VTT transcript")
    analyze.add_argument("--stt-model", default="small")
    analyze.add_argument("--scene-threshold", type=float, default=0.34)
    analyze.add_argument("--output", "-o", default="-")

    extract = sub.add_parser("frames", help="extract the selected frames from an analysis manifest")
    extract.add_argument("video")
    extract.add_argument("--manifest", required=True)
    extract.add_argument("--output-dir", default="frames")

    understand = sub.add_parser("understand", help="analyze a video visually with an OpenAI-compatible multimodal endpoint")
    understand.add_argument("video")
    understand.add_argument("--mode", choices=[mode.value for mode in AnalysisMode], default="balanced")
    understand.add_argument("--transcript")
    understand.add_argument("--stt-model", default="small")
    understand.add_argument("--scene-threshold", type=float, default=0.34)
    understand.add_argument("--api-key")
    understand.add_argument("--endpoint", default="https://api.openai.com/v1/chat/completions")
    understand.add_argument("--model", default="gpt-4.1-mini")
    understand.add_argument("--max-frames", type=int)
    understand.add_argument("--frame-dir", default=".frameview/frames")
    understand.add_argument("--instruction", default="Create a precise analysis of the video. Explain the main ideas, important visual moments, and how the visuals relate to what is being said. Preserve timestamps when useful.")

    return parser


def _cmd_analyze(args: argparse.Namespace) -> int:
    manifest = analyze_video(
        args.video,
        mode=AnalysisMode(args.mode),
        transcript_path=args.transcript,
        stt_model=args.stt_model,
        scene_threshold=args.scene_threshold,
    )
    payload = json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    return 0


def _cmd_frames(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    from .models import FrameCandidate

    frames = [FrameCandidate(**frame) for frame in data.get("frames", [])]
    extract_frames(args.video, frames, args.output_dir)
    print(json.dumps([frame.to_dict() for frame in frames], ensure_ascii=False, indent=2))
    return 0


def _cmd_understand(args: argparse.Namespace) -> int:
    manifest = analyze_video(
        args.video,
        mode=AnalysisMode(args.mode),
        transcript_path=args.transcript,
        stt_model=args.stt_model,
        scene_threshold=args.scene_threshold,
    )
    output_dir = Path(args.frame_dir)
    extract_frames(args.video, manifest.frames, output_dir)
    result = analyze_manifest(
        manifest,
        api_key=args.api_key,
        endpoint=args.endpoint,
        model=args.model,
        max_frames=args.max_frames,
        instruction=args.instruction,
    )
    result["manifest"] = manifest.to_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.command == "analyze":
            return _cmd_analyze(args)
        if args.command == "frames":
            return _cmd_frames(args)
        return _cmd_understand(args)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"frameview: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
