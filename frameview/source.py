from __future__ import annotations

import ipaddress
import os
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse


class SourceError(RuntimeError):
    pass


def is_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except ValueError:
        return False


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SourceError("Source must be a local file or an http(s) URL")
    host = parsed.hostname.lower().rstrip(".")
    allowed = {x.strip().lower() for x in os.getenv("FRAMEVIEW_ALLOWED_HOSTS", "").split(",") if x.strip()}
    if allowed and host not in allowed:
        raise SourceError(f"Host is not allowlisted: {host}")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise SourceError(f"Could not resolve source host: {host}") from exc
    for _, _, _, _, sockaddr in addresses:
        address = ipaddress.ip_address(sockaddr[0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved or address.is_unspecified:
            raise SourceError("Refusing to fetch a private or local network address")


def _limits() -> tuple[int, int]:
    max_duration = int(os.getenv("FRAMEVIEW_MAX_DURATION_SECONDS", str(3 * 60 * 60)))
    max_bytes = int(os.getenv("FRAMEVIEW_MAX_DOWNLOAD_BYTES", str(4 * 1024 * 1024 * 1024)))
    return max_duration, max_bytes


def download_source(url: str, workdir: str | Path, *, languages: tuple[str, ...] = ("en", "de")) -> tuple[Path, Path | None]:
    """Download one remote video with captions preferred and resource limits enforced."""
    _validate_url(url)
    try:
        import yt_dlp
    except ImportError as exc:
        raise SourceError("URL sources require yt-dlp; install with pip install -e '.[url]'") from exc

    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    output = root / "source.%(ext)s"
    max_duration, max_bytes = _limits()
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": str(output),
        "merge_output_format": "mp4",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": list(languages),
        "subtitlesformat": "vtt",
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 4,
        "overwrites": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise SourceError("yt-dlp returned no source metadata")
            duration = float(info.get("duration") or 0)
            approx_size = int(info.get("filesize") or info.get("filesize_approx") or 0)
            if duration and duration > max_duration:
                raise SourceError(f"Video duration {duration:.0f}s exceeds limit {max_duration}s")
            if approx_size and approx_size > max_bytes:
                raise SourceError(f"Estimated download size exceeds limit of {max_bytes} bytes")
            ydl.download([url])
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError(f"Could not download source: {exc}") from exc

    videos = [p for p in root.iterdir() if p.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"} and p.is_file()]
    if not videos:
        raise SourceError("yt-dlp downloaded no playable video")
    video = max(videos, key=lambda p: p.stat().st_size)
    if video.stat().st_size > max_bytes:
        raise SourceError(f"Downloaded file exceeds limit of {max_bytes} bytes")
    caption = next((p for p in root.glob("*.vtt") if p.is_file()), None)
    if caption is None:
        caption = next((p for p in root.glob("*.srt") if p.is_file()), None)
    return video, caption


def resolve_source(source: str, *, workdir: str | Path | None = None) -> tuple[Path, Path | None, tempfile.TemporaryDirectory[str] | None]:
    if not is_url(source):
        path = Path(source).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise SourceError(f"Video file does not exist: {source}")
        return path, None, None
    holder = None
    if workdir is None:
        holder = tempfile.TemporaryDirectory(prefix="frameview-")
        workdir = holder.name
    video, caption = download_source(source, workdir)
    return video, caption, holder
