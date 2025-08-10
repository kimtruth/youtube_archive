import types

from youtube_dump import watcher as W


def test_normalize_channel_live_url():
    assert (
        W.normalize_channel_live_url("https://www.youtube.com/@handle")
        == "https://www.youtube.com/@handle/live"
    )
    assert (
        W.normalize_channel_live_url("https://www.youtube.com/@handle/live")
        == "https://www.youtube.com/@handle/live"
    )
    assert (
        W.normalize_channel_live_url("https://www.youtube.com/channel/UCabc")
        == "https://www.youtube.com/channel/UCabc/live"
    )
    assert (
        W.normalize_channel_live_url("https://www.youtube.com/channel/UCabc/live")
        == "https://www.youtube.com/channel/UCabc/live"
    )


def test_get_live_video_url_when_live(monkeypatch):
    class _FakeYDL:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            assert url.endswith("/live")
            return {
                "id": "VID123",
                "is_live": True,
                "webpage_url": "https://www.youtube.com/watch?v=VID123",
            }

    monkeypatch.setattr(W, "yt_dlp", types.SimpleNamespace(YoutubeDL=_FakeYDL))

    live_url = W.get_live_video_url("https://www.youtube.com/@handle")
    assert live_url.endswith("VID123")


def test_get_live_video_url_none_when_not_live(monkeypatch):
    class _FakeYDL:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            return {"is_live": False}

    monkeypatch.setattr(W, "yt_dlp", types.SimpleNamespace(YoutubeDL=_FakeYDL))

    assert W.get_live_video_url("https://www.youtube.com/@handle") is None


def test_watch_triggers_restream_once(monkeypatch):
    calls = {"restream": 0}

    def fake_get_live_video_url(url):
        state = calls.get("state", 0)
        calls["state"] = state + 1
        return (
            None
            if state == 0
            else ("https://www.youtube.com/watch?v=LIVEID" if state == 1 else None)
        )

    def fake_restream_youtube(**kwargs):
        calls["restream"] += 1

    monkeypatch.setattr(W, "get_live_video_url", fake_get_live_video_url)
    monkeypatch.setattr(W, "restream_youtube", fake_restream_youtube)

    W.watch_channel_and_restream(
        channel_url="https://www.youtube.com/@handle",
        stream_key="key",
        ingest_url="rtmp://a.rtmp.youtube.com/live2",
        yt_dlp_format="best",
        copy_mode=False,
        video_bitrate="3000k",
        audio_bitrate="160k",
        x264_preset="veryfast",
        live_from_start=False,
        verbose=False,
        poll_interval_seconds=0.01,
        max_checks=3,
    )

    assert calls["restream"] == 1
