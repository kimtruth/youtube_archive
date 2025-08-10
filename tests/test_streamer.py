import sys

import pytest

from youtube_dump import streamer as S


def test_ensure_binaries_ok(monkeypatch):
    monkeypatch.setattr(S.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    S.ensure_binaries()


def test_ensure_binaries_fail(monkeypatch):
    monkeypatch.setattr(S.shutil, "which", lambda name: None)
    with pytest.raises(S.MissingBinaryError):
        S.ensure_binaries()


def test_build_ffmpeg_cmd_copy_mode():
    cmd = S.build_ffmpeg_cmd(
        ingest_url="rtmp://a.rtmp.youtube.com/live2",
        stream_key="key123",
        copy_mode=True,
        video_bitrate="3000k",
        audio_bitrate="160k",
        x264_preset="veryfast",
        verbose=False,
    )
    assert "-c:v" in cmd and "copy" in cmd
    assert "-c:a" in cmd and "copy" in cmd
    assert cmd[-1].endswith("/key123")
    assert "warning" in cmd


def test_build_ffmpeg_cmd_reencode():
    cmd = S.build_ffmpeg_cmd(
        ingest_url="rtmp://a.rtmp.youtube.com/live2/",
        stream_key="key123",
        copy_mode=False,
        video_bitrate="3000k",
        audio_bitrate="160k",
        x264_preset="veryfast",
        verbose=True,
    )
    assert "libx264" in cmd
    assert "-bufsize" in cmd
    bufsize_index = cmd.index("-bufsize") + 1
    assert cmd[bufsize_index] == "6000k"
    assert "info" in cmd
    assert cmd[-1] == "rtmp://a.rtmp.youtube.com/live2/key123"


def test_build_ytdlp_cmd():
    cmd = S.build_ytdlp_cmd(
        source_url="https://www.youtube.com/watch?v=LIVE",
        yt_dlp_format="best",
        live_from_start=True,
        verbose=False,
    )
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "yt_dlp"]
    assert "-o" in cmd and "-" in cmd
    assert "--live-from-start" in cmd


class _FakePopen:
    def __init__(self, args, stdout=None, stdin=None, stderr=None, bufsize=0):
        self.args = args
        self._rc = 0
        self._terminated = False
        self._killed = False
        self.stdout = object() if stdout is not None else None
        self.stdin = stdin

    def poll(self):
        return self._rc

    def wait(self):
        return self._rc

    def terminate(self):
        self._terminated = True

    def kill(self):
        self._killed = True


def test_restream_success(monkeypatch):
    monkeypatch.setattr(S, "ensure_binaries", lambda verbose=False: None)
    monkeypatch.setattr(S, "build_ytdlp_cmd", lambda **k: ["yt-dlp"])
    monkeypatch.setattr(S, "build_ffmpeg_cmd", lambda **k: ["ffmpeg"])

    popen_calls = []

    def _fake_popen(*args, **kwargs):
        pop = _FakePopen(*args, **kwargs)
        popen_calls.append(pop)
        return pop

    monkeypatch.setattr(S.subprocess, "Popen", _fake_popen)

    S.restream_youtube(
        source_url="https://youtube.com/watch?v=LIVE",
        stream_key="abc",
        ingest_url="rtmp://a.rtmp.youtube.com/live2",
        yt_dlp_format="best",
        copy_mode=False,
        video_bitrate="3000k",
        audio_bitrate="160k",
        x264_preset="veryfast",
        live_from_start=False,
        verbose=False,
    )

    assert len(popen_calls) == 2


def test_restream_failure_raises(monkeypatch):
    monkeypatch.setattr(S, "ensure_binaries", lambda verbose=False: None)
    monkeypatch.setattr(S, "build_ytdlp_cmd", lambda **k: ["yt-dlp"])
    monkeypatch.setattr(S, "build_ffmpeg_cmd", lambda **k: ["ffmpeg"])

    class _BadPopen(_FakePopen):
        def wait(self):
            self._rc = 1
            return self._rc

    def _fake_popen(*args, **kwargs):
        return _BadPopen(*args, **kwargs)

    monkeypatch.setattr(S.subprocess, "Popen", _fake_popen)

    with pytest.raises(RuntimeError):
        S.restream_youtube(
            source_url="https://youtube.com/watch?v=LIVE",
            stream_key="abc",
            ingest_url="rtmp://a.rtmp.youtube.com/live2",
            yt_dlp_format="best",
            copy_mode=False,
            video_bitrate="3000k",
            audio_bitrate="160k",
            x264_preset="veryfast",
            live_from_start=False,
            verbose=False,
        )
