from __future__ import annotations

import time

import yt_dlp

from .streamer import restream_youtube


def normalize_channel_live_url(channel_url: str) -> str:
    url = channel_url.rstrip("/")
    if url.endswith("/live"):
        return url
    if "/channel/" in url or url.startswith("https://www.youtube.com/@"):
        return url + "/live"
    return url + "/live"


def get_live_video_url(channel_url: str) -> str | None:
    live_url = normalize_channel_live_url(channel_url)

    ydl_opts = {
        "quiet": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "skip_download": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(live_url, download=False)
        except Exception:
            return None

    if not isinstance(info, dict):
        return None

    is_live = info.get("is_live")
    if is_live:
        video_url = info.get("webpage_url") or info.get("original_url") or info.get("url")
        return str(video_url) if video_url else None

    return None


def watch_channel_and_restream(
    channel_url: str,
    stream_key: str,
    ingest_url: str,
    yt_dlp_format: str,
    copy_mode: bool,
    video_bitrate: str,
    audio_bitrate: str,
    x264_preset: str,
    live_from_start: bool,
    verbose: bool,
    poll_interval_seconds: float = 15.0,
    max_checks: int | None = None,
) -> None:
    checks = 0
    while True:
        live_video_url = get_live_video_url(channel_url)
        if live_video_url:
            restream_youtube(
                source_url=live_video_url,
                stream_key=stream_key,
                ingest_url=ingest_url,
                yt_dlp_format=yt_dlp_format,
                copy_mode=copy_mode,
                video_bitrate=video_bitrate,
                audio_bitrate=audio_bitrate,
                x264_preset=x264_preset,
                live_from_start=live_from_start,
                verbose=verbose,
            )
        checks += 1
        if max_checks is not None and checks >= max_checks:
            break
        time.sleep(poll_interval_seconds)
