from frameview.transcript import contains_visual_reference, parse_srt, visual_reference_segments


def test_parse_srt():
    text = """1\n00:00:01,000 --> 00:00:03,500\nHello world.\n\n2\n00:00:04,000 --> 00:00:06,000\nLook here at the screen.\n"""
    segments = parse_srt(text)
    assert len(segments) == 2
    assert segments[0].start == 1.0
    assert segments[0].end == 3.5


def test_visual_reference_detection():
    assert contains_visual_reference("As you can see, this changes here.")
    assert not contains_visual_reference("The next chapter is about pricing.")

    segments = parse_srt("1\n00:00:04,000 --> 00:00:06,000\nLook here at the screen.\n")
    assert len(visual_reference_segments(segments)) == 1
