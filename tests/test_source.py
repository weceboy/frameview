from frameview.source import SourceError, is_url


def test_is_url():
    assert is_url("https://example.com/video")
    assert not is_url("/tmp/video.mp4")


def test_private_source_is_rejected(monkeypatch):
    monkeypatch.delenv("FRAMEVIEW_ALLOWED_HOSTS", raising=False)
    import frameview.source as source
    import socket

    original = socket.getaddrinfo
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))])
    try:
        source._validate_url("https://example.com/video")
    except SourceError as exc:
        assert "private" in str(exc).lower()
    else:
        raise AssertionError("private destination should be rejected")
    finally:
        monkeypatch.setattr(socket, "getaddrinfo", original)
