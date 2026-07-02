"""
update_video_metadata.py

Update title/description/tags of an EXISTING (uploaded/scheduled) YouTube video.
Uses the youtube.force-ssl scope (broader than upload) — first run opens a browser
and saves token_manage.json for future runs.

Usage:
  python execution/update_video_metadata.py --video-id VIDEO_ID --metadata path/to/metadata.json
  (metadata.json needs: title, description, tags — same shape generate_metadata.py saves)
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token_manage.json"  # broader scope than token_upload.json
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def get_client():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def main():
    ap = argparse.ArgumentParser(description="Update metadata on an existing YouTube video")
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--metadata", required=True, help="JSON file with title/description/tags")
    args = ap.parse_args()

    meta = json.loads(Path(args.metadata).read_text())
    yt = get_client()

    # Fetch the existing snippet so we don't wipe fields we aren't changing
    resp = yt.videos().list(id=args.video_id, part="snippet").execute()
    if not resp.get("items"):
        print(f"ERROR: video {args.video_id} not found (wrong account or deleted).")
        sys.exit(1)
    snippet = resp["items"][0]["snippet"]

    old_title = snippet["title"]
    snippet["title"] = meta["title"]
    snippet["description"] = meta["description"]
    if meta.get("tags"):
        snippet["tags"] = meta["tags"]

    yt.videos().update(part="snippet", body={"id": args.video_id, "snippet": snippet}).execute()
    print(f"Updated {args.video_id}")
    print(f"  old: {old_title}")
    print(f"  new: {meta['title']}")


if __name__ == "__main__":
    main()
