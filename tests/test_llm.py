from __future__ import annotations

import json

from frameview.llm import analyze_manifest
from frameview.models import AnalysisManifest, AnalysisMode, FrameCandidate, TranscriptSegment


def test_analyze_manifest_sends_timestamped_transcript_and_image(monkeypatch, tmp_path):
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"fake-jpeg")
    manifest = AnalysisManifest(
        source="video.mp4",
        duration=10.0,
        mode=AnalysisMode.BALANCED,
        transcript=[TranscriptSegment(1.0, 2.0, "Look here")],
        frames=[FrameCandidate(1.5, ["visual_reference"], 0.85, str(image))],
    )
    captured = {}

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

    def fake_urlopen(request, timeout=0):
        captured["payload"] = json.loads(request.data.decode())
        return Response()

    monkeypatch.setattr("frameview.llm.urllib.request.urlopen", fake_urlopen)
    result = analyze_manifest(manifest, api_key="test", model="demo")

    assert result["analysis"] == "ok"
    parts = captured["payload"]["messages"][0]["content"]
    assert any("Look here" in item.get("text", "") for item in parts)
    assert any(item.get("type") == "image_url" for item in parts)
