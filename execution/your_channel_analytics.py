"""
your_channel_analytics.py

Fetches stats for YOUR channel (Astronaut Girl) and compares against
top competitors. Outputs a performance summary Nova can use.

Inputs:  credentials.json + token.json (OAuth), YOUTUBE_API_KEY in .env
Outputs: prints summary + saves to memory/your_channel_latest.md

OAuth scopes needed:
  - https://www.googleapis.com/auth/youtube.readonly
  - https://www.googleapis.com/auth/yt-analytics.readonly
"""

import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

YOUR_CHANNEL_ID = "UCZJe8Esgl8BWJv_XpAC1FBA"
DATA_FILE = Path(__file__).parent.parent / ".tmp" / "channel_research_master.csv"
MEMORY_DIR = Path(__file__).parent.parent / "memory"
TOKEN_PATH = Path(__file__).parent.parent / "token_yt.json"
CREDS_PATH = Path(__file__).parent.parent / "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_oauth_creds():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def get_channel_stats(yt) -> dict:
    resp = yt.channels().list(
        id=YOUR_CHANNEL_ID,
        part="snippet,statistics,contentDetails"
    ).execute()
    items = resp.get("items", [])
    if not items:
        return {}
    item = items[0]
    return {
        "name": item["snippet"]["title"],
        "description": item["snippet"].get("description", ""),
        "created": item["snippet"]["publishedAt"][:10],
        "subscribers": int(item["statistics"].get("subscriberCount", 0)),
        "total_views": int(item["statistics"].get("viewCount", 0)),
        "video_count": int(item["statistics"].get("videoCount", 0)),
    }


def get_recent_videos(yt, max_results=10) -> list:
    resp = yt.search().list(
        channelId=YOUR_CHANNEL_ID,
        type="video",
        order="date",
        part="id,snippet",
        maxResults=max_results
    ).execute()

    videos = []
    for item in resp.get("items", []):
        vid_id = item["id"]["videoId"]
        # get view stats
        stats_resp = yt.videos().list(id=vid_id, part="statistics,contentDetails").execute()
        stats = stats_resp["items"][0]["statistics"] if stats_resp["items"] else {}
        duration = stats_resp["items"][0]["contentDetails"].get("duration", "") if stats_resp["items"] else ""
        videos.append({
            "title": item["snippet"]["title"],
            "published": item["snippet"]["publishedAt"][:10],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "duration": duration,
            "video_id": vid_id,
        })
    return videos


def get_analytics(analytics, days=28) -> dict:
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        resp = analytics.reports().query(
            ids=f"channel=={YOUR_CHANNEL_ID}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost",
            dimensions="day",
            sort="day"
        ).execute()
        rows = resp.get("rows", [])
        if not rows:
            return {}
        total_views = sum(int(r[1]) for r in rows)
        total_watch_min = sum(float(r[2]) for r in rows)
        avg_view_dur = sum(float(r[3]) for r in rows) / len(rows)
        subs_gained = sum(int(r[4]) for r in rows)
        return {
            "period_days": days,
            "total_views": total_views,
            "watch_hours": round(total_watch_min / 60, 1),
            "avg_view_duration_sec": round(avg_view_dur),
            "subscribers_gained": subs_gained,
        }
    except Exception as e:
        return {"error": str(e)}


def load_competitor_benchmarks() -> dict:
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    space = [r for r in rows if r.get("Theme") == "Space ✓" and r["Subscribers"].isdigit()]
    space.sort(key=lambda x: int(x["Subscribers"]), reverse=True)
    top = space[:3] if space else []
    return {r["Channel Name"]: {
        "subscribers": int(r["Subscribers"]),
        "recent_avg_views": int(r["Recent Avg Views (last 10)"]),
        "upload_freq": float(r["Upload Frequency (videos/mo)"]),
        "age_years": float(r["Channel Age (yrs)"]),
    } for r in top}


def build_report(channel: dict, videos: list, analytics: dict, benchmarks: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Astronaut Girl — Channel Report ({now})", ""]

    # Basic stats
    lines += [
        "## Your Channel Stats",
        f"- Subscribers: {channel.get('subscribers', 0):,}",
        f"- Total Views: {channel.get('total_views', 0):,}",
        f"- Videos: {channel.get('video_count', 0)}",
        f"- Channel created: {channel.get('created', 'unknown')}",
        "",
    ]

    # Analytics
    if analytics and "error" not in analytics:
        lines += [
            f"## Last {analytics['period_days']} Days",
            f"- Views: {analytics['total_views']:,}",
            f"- Watch time: {analytics['watch_hours']:,} hours",
            f"- Avg view duration: {analytics['avg_view_duration_sec']}s",
            f"- Subscribers gained: {analytics['subscribers_gained']:,}",
            "",
        ]

    # Videos
    if videos:
        lines += ["## Your Videos (most recent first)"]
        for v in videos:
            lines.append(f"- [{v['published']}] {v['title']} — {v['views']:,} views, {v['likes']:,} likes")
        lines.append("")
    else:
        lines += ["## Your Videos", "- No videos uploaded yet.", ""]

    # Competitor comparison
    if benchmarks:
        lines += ["## vs Competitors"]
        for name, b in benchmarks.items():
            lines.append(
                f"- {name}: {b['subscribers']:,} subs | "
                f"{b['recent_avg_views']:,} recent avg views | "
                f"{b['upload_freq']}/mo"
            )
        lines.append("")

    return "\n".join(lines)


def main():
    print("Fetching your channel analytics...")

    creds = get_oauth_creds()
    yt = build("youtube", "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)

    channel = get_channel_stats(yt)
    if not channel:
        print("ERROR: Could not find channel. Check YOUR_CHANNEL_ID.")
        return

    print(f"Channel: {channel['name']}")
    videos = get_recent_videos(yt)
    analytics_data = get_analytics(analytics)
    benchmarks = load_competitor_benchmarks()

    report = build_report(channel, videos, analytics_data, benchmarks)
    print("\n" + report)

    # Save to memory so Nova can read it
    MEMORY_DIR.mkdir(exist_ok=True)
    output = MEMORY_DIR / "your_channel_latest.md"
    output.write_text(report)
    print(f"\nSaved to {output}")


if __name__ == "__main__":
    main()
