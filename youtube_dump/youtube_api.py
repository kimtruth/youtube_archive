from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
]

DEFAULT_CLIENT_SECRETS = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secret.json")
DEFAULT_TOKEN_FILE = os.environ.get("YOUTUBE_TOKEN_FILE", "token.json")


def _load_credentials(
    client_secrets_path: str | os.PathLike = DEFAULT_CLIENT_SECRETS,
    token_path: str | os.PathLike = DEFAULT_TOKEN_FILE,
) -> Credentials:
    token = Path(token_path)
    creds: Credentials | None = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(request=None)  # type: ignore[arg-type]
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def login(
    client_secrets_path: str | os.PathLike = DEFAULT_CLIENT_SECRETS,
    token_path: str | os.PathLike = DEFAULT_TOKEN_FILE,
) -> None:
    _load_credentials(client_secrets_path, token_path)


def logout(token_path: str | os.PathLike = DEFAULT_TOKEN_FILE) -> None:
    Path(token_path).unlink(missing_ok=True)


def build_service(creds: Credentials | None = None) -> Any:
    if creds is None:
        creds = _load_credentials()
    return build("youtube", "v3", credentials=creds)


def create_stream_and_broadcast(
    title: str,
    privacy_status: str = "private",
) -> tuple[str, str]:
    service = build_service()

    # 1) Create liveStream (returns ingestion info)
    stream_body = {
        "snippet": {
            "title": title,
        },
        "cdn": {
            "frameRate": "variable",
            "ingestionType": "rtmp",
            "resolution": "variable",
        },
    }
    stream_resp = (
        service.liveStreams()
        .insert(part="snippet,cdn,contentDetails", body=stream_body)
        .execute()
    )
    ingestion = stream_resp["cdn"]["ingestionInfo"]
    ingestion_address: str = ingestion["ingestionAddress"]
    stream_name: str = ingestion["streamName"]
    stream_id: str = stream_resp["id"]

    # 2) Create liveBroadcast
    start_time = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    broadcast_body = {
        "snippet": {
            "title": title,
            "scheduledStartTime": start_time,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
        "contentDetails": {
            "enableAutoStart": True,
            "enableAutoStop": True,
        },
    }
    broadcast_resp = (
        service.liveBroadcasts()
        .insert(part="snippet,status,contentDetails", body=broadcast_body)
        .execute()
    )
    broadcast_id: str = broadcast_resp["id"]

    # 3) Bind broadcast to stream
    service.liveBroadcasts().bind(part="id,contentDetails", id=broadcast_id, streamId=stream_id).execute()

    # Return ingestion endpoint + stream key
    return ingestion_address, stream_name
