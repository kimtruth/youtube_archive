from __future__ import annotations

import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass


class ProcessPair:
    def __init__(self, producer: subprocess.Popen, consumer: subprocess.Popen) -> None:
        self.producer = producer
        self.consumer = consumer

    def terminate(self) -> None:
        for p in (self.producer, self.consumer):
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass

    def kill(self) -> None:
        for p in (self.producer, self.consumer):
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass


class MissingBinaryError(RuntimeError):
    pass


def ensure_binaries(verbose: bool = False) -> None:
    if shutil.which("ffmpeg") is None:
        raise MissingBinaryError(
            "ffmpeg이 필요합니다. macOS: 'brew install ffmpeg', Docker: 이미 포함됨"
        )


@dataclass
class StreamConfig:
    ingest_url: str
    stream_key: str
    copy_mode: bool
    video_bitrate: str
    audio_bitrate: str
    x264_preset: str
    live_from_start: bool
    verbose: bool

    @property
    def output_url(self) -> str:
        return f"{self.ingest_url.rstrip('/')}/{self.stream_key}"

    @staticmethod
    def _bufsize_from_bitrate(video_bitrate: str) -> str:
        if video_bitrate.endswith("k"):
            try:
                value = int(video_bitrate[:-1])
                return f"{value * 2}k"
            except ValueError:
                return video_bitrate
        return video_bitrate

    def build_ffmpeg_cmd(self) -> list[str]:
        base = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "info" if self.verbose else "warning",
            "-re",
            "-i",
            "pipe:0",
        ]
        if self.copy_mode:
            codec = ["-c:v", "copy", "-c:a", "copy"]
        else:
            codec = [
                "-c:v",
                "libx264",
                "-preset",
                self.x264_preset,
                "-b:v",
                self.video_bitrate,
                "-maxrate",
                self.video_bitrate,
                "-bufsize",
                self._bufsize_from_bitrate(self.video_bitrate),
                "-c:a",
                "aac",
                "-b:a",
                self.audio_bitrate,
                "-ar",
                "48000",
                "-ac",
                "2",
            ]
        tail = ["-f", "flv", self.output_url]
        return base + codec + tail


def build_ffmpeg_cmd(
    ingest_url: str,
    stream_key: str,
    copy_mode: bool,
    video_bitrate: str,
    audio_bitrate: str,
    x264_preset: str,
    verbose: bool,
) -> list[str]:
    cfg = StreamConfig(
        ingest_url=ingest_url,
        stream_key=stream_key,
        copy_mode=copy_mode,
        video_bitrate=video_bitrate,
        audio_bitrate=audio_bitrate,
        x264_preset=x264_preset,
        live_from_start=False,
        verbose=verbose,
    )
    return cfg.build_ffmpeg_cmd()


def build_ytdlp_cmd(
    source_url: str,
    yt_dlp_format: str,
    live_from_start: bool,
    verbose: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        yt_dlp_format,
        "-o",
        "-",
        "--no-warnings",
        "--newline",
    ]
    if live_from_start:
        cmd.append("--live-from-start")
    cmd.append(source_url)

    if verbose:
        print("yt-dlp:", " ".join(cmd), file=sys.stderr)

    return cmd


def _forward_stream(src, dst) -> None:
    # 필요 시 로깅/중계 스레드 사용 가능 (현재는 직접 파이프 연결)
    for chunk in iter(lambda: src.read(64 * 1024), b""):
        dst.write(chunk)
        dst.flush()


def restream_youtube(
    source_url: str,
    stream_key: str,
    ingest_url: str,
    yt_dlp_format: str,
    copy_mode: bool,
    video_bitrate: str,
    audio_bitrate: str,
    x264_preset: str,
    live_from_start: bool,
    verbose: bool,
) -> None:
    ensure_binaries(verbose=verbose)

    cfg = StreamConfig(
        ingest_url=ingest_url,
        stream_key=stream_key,
        copy_mode=copy_mode,
        video_bitrate=video_bitrate,
        audio_bitrate=audio_bitrate,
        x264_preset=x264_preset,
        live_from_start=live_from_start,
        verbose=verbose,
    )

    ytdlp_cmd = build_ytdlp_cmd(
        source_url=source_url,
        yt_dlp_format=yt_dlp_format,
        live_from_start=live_from_start,
        verbose=verbose,
    )
    ffmpeg_cmd = cfg.build_ffmpeg_cmd()

    producer = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=sys.stderr if verbose else subprocess.DEVNULL,
        bufsize=0,
    )
    if producer.stdout is None:
        raise RuntimeError("yt-dlp 파이프 생성 실패")

    consumer = subprocess.Popen(
        ffmpeg_cmd,
        stdin=producer.stdout,
        stdout=sys.stdout if verbose else subprocess.DEVNULL,
        stderr=sys.stderr if verbose else subprocess.DEVNULL,
        bufsize=0,
    )

    pair = ProcessPair(producer, consumer)

    def _handle_signal(signum, frame):  # type: ignore[no-untyped-def]
        pair.terminate()

    previous_int = signal.signal(signal.SIGINT, _handle_signal)
    previous_term = signal.signal(signal.SIGTERM, _handle_signal)

    try:
        rc_consumer = consumer.wait()
        if producer.poll() is None:
            try:
                producer.terminate()
            except Exception:
                pass
        rc_producer = producer.wait()

        if rc_consumer != 0 or rc_producer != 0:
            raise RuntimeError(f"프로세스 종료 코드: yt-dlp={rc_producer}, ffmpeg={rc_consumer}")
    finally:
        try:
            signal.signal(signal.SIGINT, previous_int)
            signal.signal(signal.SIGTERM, previous_term)
        except Exception:
            pass
