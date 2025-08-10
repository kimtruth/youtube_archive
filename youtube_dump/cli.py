from __future__ import annotations

import sys

import click
from dotenv import load_dotenv

from . import watcher
from .streamer import restream_youtube


def _load_env() -> None:
    load_dotenv(override=False)


@click.group()
def cli() -> None:
    _load_env()


@cli.command(help="다른 유튜브 라이브를 내 채널로 재송출합니다.")
@click.argument("source_url", type=str)
@click.option(
    "--stream-key", envvar="YOUTUBE_STREAM_KEY", help="유튜브 송출 키(환경변수 사용 가능)"
)
@click.option(
    "--ingest-url",
    default="rtmp://a.rtmp.youtube.com/live2",
    show_default=True,
    help="RTMP 인제스트 URL",
)
@click.option(
    "--format",
    "fmt",
    default="bestvideo+bestaudio/best",
    show_default=True,
    help="yt-dlp 포맷 표현식",
)
@click.option(
    "--copy/--reencode",
    "copy_mode",
    default=False,
    show_default=True,
    help="코덱 복사 시도 여부 (기본: 재인코딩)",
)
@click.option("--video-bitrate", default="3000k", show_default=True)
@click.option("--audio-bitrate", default="160k", show_default=True)
@click.option("--preset", default="veryfast", show_default=True, help="x264 preset")
@click.option(
    "--live-from-start/--live-edge",
    default=False,
    show_default=True,
    help="라이브 시작 시점부터 재생",
)
@click.option("--verbose/--quiet", default=False, show_default=True)
def restream(
    source_url: str,
    stream_key: str | None,
    ingest_url: str,
    fmt: str,
    copy_mode: bool,
    video_bitrate: str,
    audio_bitrate: str,
    preset: str,
    live_from_start: bool,
    verbose: bool,
) -> None:
    if not stream_key:
        click.echo("환경변수 YOUTUBE_STREAM_KEY 또는 --stream-key 옵션이 필요합니다.", err=True)
        sys.exit(2)

    try:
        restream_youtube(
            source_url=source_url,
            stream_key=stream_key,
            ingest_url=ingest_url,
            yt_dlp_format=fmt,
            copy_mode=copy_mode,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate,
            x264_preset=preset,
            live_from_start=live_from_start,
            verbose=verbose,
        )
    except KeyboardInterrupt:
        click.echo("중단됨")
    except Exception as exc:  # noqa: BLE001
        if verbose:
            raise
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@cli.command(help="채널에서 라이브 발생을 감지하여 자동으로 재송출합니다.")
@click.argument("channel_url", type=str)
@click.option(
    "--stream-key", envvar="YOUTUBE_STREAM_KEY", help="유튜브 송출 키(환경변수 사용 가능)"
)
@click.option("--ingest-url", default="rtmp://a.rtmp.youtube.com/live2", show_default=True)
@click.option("--format", "fmt", default="bestvideo+bestaudio/best", show_default=True)
@click.option("--copy/--reencode", "copy_mode", default=False, show_default=True)
@click.option("--video-bitrate", default="3000k", show_default=True)
@click.option("--audio-bitrate", default="160k", show_default=True)
@click.option("--preset", default="veryfast", show_default=True)
@click.option("--live-from-start/--live-edge", default=False, show_default=True)
@click.option("--verbose/--quiet", default=False, show_default=True)
@click.option("--interval", "poll_interval", default=15.0, show_default=True, help="폴링 간격(초)")
@click.option("--max-checks", default=None, type=int, help="테스트/디버깅용 최대 폴링 횟수")
def watch(
    channel_url: str,
    stream_key: str | None,
    ingest_url: str,
    fmt: str,
    copy_mode: bool,
    video_bitrate: str,
    audio_bitrate: str,
    preset: str,
    live_from_start: bool,
    verbose: bool,
    poll_interval: float,
    max_checks: int | None,
) -> None:
    if not stream_key:
        click.echo("환경변수 YOUTUBE_STREAM_KEY 또는 --stream-key 옵션이 필요합니다.", err=True)
        sys.exit(2)

    try:
        watcher.watch_channel_and_restream(
            channel_url=channel_url,
            stream_key=stream_key,
            ingest_url=ingest_url,
            yt_dlp_format=fmt,
            copy_mode=copy_mode,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate,
            x264_preset=preset,
            live_from_start=live_from_start,
            verbose=verbose,
            poll_interval_seconds=poll_interval,
            max_checks=max_checks,
        )
    except KeyboardInterrupt:
        click.echo("중단됨")
    except Exception as exc:  # noqa: BLE001
        if verbose:
            raise
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


def main() -> None:
    cli(prog_name="youtube-dump")
