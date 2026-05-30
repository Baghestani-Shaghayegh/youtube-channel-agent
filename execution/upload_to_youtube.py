"""
upload_to_youtube.py

Uploads a video to YouTube with metadata and optional scheduled publishing.
First run opens a browser for one-time OAuth authentication.
Token saved as token_upload.json for future runs.

Usage:
  python execution/upload_to_youtube.py \
    --video ".tmp/final_01.mp4" \
    --metadata ".tmp/metadata_01.json" \
    --schedule "2026-06-06T18:00:00"   # optional, UTC time

  python execution/upload_to_youtube.py \
    --video ".tmp/final_01.mp4" \
    --metadata ".tmp/metadata_01.json" \
    --publish-now                        # go live immediately
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token_upload.json"

# Upload scope — allows uploading and setting status/schedule
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

MUSIC_CATEGORY_ID = "10"   # Music


def get_youtube_client():
    """Authenticate and return YouTube API client.
    Opens browser for auth on first run, uses saved token after that."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE}\n"
                    "Download it from Google Cloud Console → APIs & Services → Credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        print(f"Auth token saved: {TOKEN_FILE}")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    publish_at: str = None,   # ISO datetime string in UTC, e.g. "2026-06-06T18:00:00"
    publish_now: bool = False,
) -> dict:
    """
    Upload video to YouTube.
    - publish_at: schedule for specific time (video stays private until then)
    - publish_now: make public immediately
    - neither: upload as private (you publish manually)
    Returns dict with video_id and url.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    youtube = get_youtube_client()

    # Build status
    if publish_now:
        status = {"privacyStatus": "public"}
    elif publish_at:
        status = {
            "privacyStatus": "private",
            "publishAt": publish_at if publish_at.endswith("Z") else publish_at + "Z",
        }
    else:
        status = {"privacyStatus": "private"}

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": MUSIC_CATEGORY_ID,
            "defaultLanguage": "en",
        },
        "status": status,
    }

    size_mb = video_path.stat().st_size / 1024 / 1024
    print(f"\nUploading: {video_path.name} ({size_mb:.0f} MB)")
    print(f"Title: {title}")
    if publish_at:
        print(f"Scheduled: {publish_at} UTC")
    elif publish_now:
        print("Publishing: immediately (public)")
    else:
        print("Status: private (publish manually)")

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=5 * 1024 * 1024,   # 5MB chunks
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status_obj, response = request.next_chunk()
        if status_obj:
            pct = int(status_obj.progress() * 100)
            print(f"  {pct}% uploaded...", end="\r")

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"

    print(f"\n✓ Upload complete!")
    print(f"  Video ID : {video_id}")
    print(f"  URL      : {url}")

    return {"video_id": video_id, "url": url, "title": title}


def main():
    parser = argparse.ArgumentParser(description="Upload video to YouTube")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--metadata", required=True, help="Path to metadata JSON file")
    parser.add_argument("--schedule", default="",
                        help="Schedule publish time in UTC (e.g. 2026-06-06T18:00:00)")
    parser.add_argument("--publish-now", action="store_true",
                        help="Make video public immediately")
    args = parser.parse_args()

    video_path = Path(args.video).expanduser().resolve()
    metadata_path = Path(args.metadata).expanduser().resolve()

    if not metadata_path.exists():
        print(f"ERROR: metadata file not found: {metadata_path}")
        sys.exit(1)

    metadata = json.loads(metadata_path.read_text())

    result = upload_video(
        video_path=video_path,
        title=metadata["title"],
        description=metadata["description"],
        tags=metadata["tags"],
        publish_at=args.schedule or None,
        publish_now=args.publish_now,
    )

    print(f"\nNext step: add your thumbnail in YouTube Studio")
    print(f"  https://studio.youtube.com/video/{result['video_id']}/edit")


if __name__ == "__main__":
    main()
