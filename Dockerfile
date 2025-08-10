# syntax=docker/dockerfile:1
FROM python:3.11-slim

# 시스템 패키지: ffmpeg, curl, ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv 설치
ENV UV_INSTALL_DIR=/root/.local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="${UV_INSTALL_DIR}:$PATH"

WORKDIR /app

# 소스 및 메타 복사 (프로젝트 포함)
COPY pyproject.toml README.md ./
COPY youtube_dump ./youtube_dump

# 가상환경 및 종속성/프로젝트 설치 (이미지 내부에서 lock 생성)
RUN uv venv && uv lock && uv sync

ENV PATH="/app/.venv/bin:${PATH}"

ENTRYPOINT ["youtube-dump"]
CMD ["--help"]
