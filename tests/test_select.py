from frameview.models import AnalysisMode, TranscriptSegment
from frameview.select import merge_candidates, select_frames
from frameview.models import FrameCandidate


def test_merge_candidates_combines_reasons():
    frames = merge_candidates(
        [FrameCandidate(1.0, ["keyframe"], 0.3)],
        [FrameCandidate(1.1, ["scene_change"], 0.9)],
    )
    assert len(frames) == 1
    assert set(frames[0].reason) == {"keyframe", "scene_change"}
    assert frames[0].score == 0.9


def test_balanced_includes_transcript_visual_reference():
    transcript = [TranscriptSegment(10.0, 12.0, "As you can see here, this is the UI.")]
    frames = select_frames(AnalysisMode.BALANCED, [0.0], [20.0], transcript)
    assert any("visual_reference" in frame.reason for frame in frames)


def test_transcript_mode_has_no_frames():
    assert select_frames(AnalysisMode.TRANSCRIPT, [0.0], [1.0], []) == []
