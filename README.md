# frameview

A local-first video understanding pipeline inspired by the architecture described in the accompanying transcript: transcript extraction, efficient keyframe sampling, scene-aware frame selection, transcript-guided visual references, frame deduplication, and multimodal analysis.

## Status

This repository is an MVP. Expensive video work happens locally and is turned into a timestamp-aligned analysis manifest. The `understand` command can then send that bundle to an OpenAI-compatible multimodal chat endpoint.

## Features

- `transcript`: transcript-only analysis input.
- `efficient`: extract existing keyframes (I-frames) for fast, cheap visual coverage.
- `balanced`: combine keyframes, scene changes, and transcript visual references.
- `token-burner`: retain all strong visual candidates with no hard frame cap.
- Timestamp-aware transcript ingestion from SRT/VTT.
- Optional speech-to-text via `faster-whisper`.
- Low-resolution average hashing for cheap frame deduplication.
- JSON manifest output suitable for downstream multimodal models.
- OpenAI-compatible multimodal inference via `frameview understand`.

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

### Multimodal understanding

Set an API key and run the end-to-end pipeline:

```bash
export FRAMEVIEW_API_KEY="..."
frameview understand ./video.mp4 \
  --mode balanced \
  --model gpt-4.1-mini \
  --max-frames 80
```

The default endpoint is an OpenAI-compatible `/v1/chat/completions` endpoint. For another compatible provider, override it with `--endpoint` and pass the provider's model name with `--model`.

For a transcript already available locally:

```bash
frameview understand ./video.mp4 \
  --transcript ./video.vtt \
  --mode balanced
```

The command extracts selected frames, deduplicates them, aligns them with the transcript, and sends text plus images to the multimodal model. It returns both the model analysis and the final manifest as JSON.

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
          frame extraction
               ↓
          deduplication
               ↓
        timestamp alignment
               ↓
        multimodal model
```

Inference is kept behind a small provider-agnostic HTTP adapter, so the deterministic video selection logic remains independent of one AI vendor.
