# frameview

A local-first video understanding pipeline inspired by the architecture described in the accompanying transcript: transcript extraction, efficient keyframe sampling, scene-aware frame selection, transcript-guided visual references, and frame deduplication.

## Status

This repository starts as an intentionally provider-agnostic MVP. It does the expensive video work locally and produces a timestamp-aligned analysis manifest that can be consumed by any multimodal LLM.

## Features

- `transcript`: transcript-only analysis input.
- `efficient`: extract existing keyframes (I-frames) for fast, cheap visual coverage.
- `balanced`: combine keyframes, scene changes, transcript visual references, and deduplication.
- `token-burner`: retain all strong visual candidates with no hard frame cap.
- Timestamp-aware transcript ingestion from SRT/VTT.
- Optional speech-to-text via `faster-whisper`.
- Low-resolution perceptual hashing for cheap frame deduplication.
- JSON manifest output suitable for downstream multimodal models.

## Requirements

- Python 3.11+
- FFmpeg (`ffmpeg` and `ffprobe`) on `PATH`

Optional:

- `pip install -e '.[stt]'` for local speech-to-text with faster-whisper.

## Quick start

```bash
pip install -e .
frameview analyze ./video.mp4 --mode balanced --output analysis.json
```

With a transcript:

```bash
frameview analyze ./video.mp4 --transcript ./video.vtt --mode balanced
```

Extract only the frames selected by the pipeline:

```bash
frameview frames ./video.mp4 --manifest analysis.json --output-dir ./frames
```

## Design

The core pipeline is:

```text
video
  ├─> transcript (captions first, optional STT fallback)
  └─> frame candidates
        ├─ keyframes
        ├─ scene changes
        └─ transcript visual references
               ↓
          deduplication
               ↓
        timestamp alignment
               ↓
        JSON manifest
```

The project deliberately keeps model inference outside the core package. That makes frame selection deterministic, testable, and independent of a single AI vendor.
