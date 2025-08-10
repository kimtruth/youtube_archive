from click.testing import CliRunner

from youtube_dump import cli as C


def test_cli_missing_key():
    runner = CliRunner()
    result = runner.invoke(C.cli, ["restream", "https://youtube.com/watch?v=LIVE"])
    assert result.exit_code == 2
    assert "YOUTUBE_STREAM_KEY" in result.output


def test_cli_with_key_and_copy(monkeypatch):
    called = {}

    def _fake_restream_youtube(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(C, "restream_youtube", _fake_restream_youtube)

    runner = CliRunner()
    result = runner.invoke(
        C.cli,
        [
            "restream",
            "https://youtube.com/watch?v=LIVE",
            "--stream-key",
            "abcd",
            "--copy",
            "--video-bitrate",
            "3500k",
            "--audio-bitrate",
            "128k",
            "--preset",
            "ultrafast",
            "--verbose",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called["source_url"].endswith("LIVE")
    assert called["stream_key"] == "abcd"
    assert called["copy_mode"] is True
    assert called["video_bitrate"] == "3500k"
    assert called["audio_bitrate"] == "128k"
    assert called["x264_preset"] == "ultrafast"
    assert called["verbose"] is True


def test_cli_watch_invokes_watcher(monkeypatch):
    called = {}

    def _fake_watch_channel_and_restream(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(C.watcher, "watch_channel_and_restream", _fake_watch_channel_and_restream)

    runner = CliRunner()
    result = runner.invoke(
        C.cli,
        [
            "watch",
            "https://www.youtube.com/@handle",
            "--stream-key",
            "abcd",
            "--interval",
            "0.1",
            "--max-checks",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called["channel_url"].endswith("@handle")
    assert called["stream_key"] == "abcd"
    assert called["poll_interval_seconds"] == 0.1
    assert called["max_checks"] == 2
