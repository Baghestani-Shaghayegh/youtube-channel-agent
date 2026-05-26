"""
weekly_monitor.py

Runs every Monday via cron. Re-fetches stats for Space ✓ channels,
compares to stored data, sends Slack summary, updates CSV.

Cron entry (runs every Monday 9am):
  0 9 * * 1 cd /path/to/repo && .venv/bin/python execution/weekly_monitor.py
"""

import os
import csv
import json
import time
import re
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from load_env import load_env
load_env()

import anthropic
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
DATA_FILE = Path(".tmp/channel_research_master.csv")
MEMORY_DIR = Path("memory")
MODEL = "claude-opus-4-7"


def load_space_channels() -> list[dict]:
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("Theme") == "Space ✓" and r["Subscribers"].isdigit()]


def fetch_current_stats(yt, channel_ids: list[str]) -> dict:
    resp = yt.channels().list(
        id=",".join(channel_ids),
        part="snippet,statistics"
    ).execute()
    return {item["id"]: item for item in resp.get("items", [])}


def parse_yt_date(s: str) -> datetime:
    s = re.sub(r"\.(\d+)([+\-Z])", lambda m: f".{m.group(1)[:6].ljust(6,'0')}{m.group(2)}", s)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_recent_videos(yt, channel_id: str, max_results: int = 3) -> list[dict]:
    try:
        resp = yt.search().list(
            channelId=channel_id, type="video", order="date",
            part="id,snippet", maxResults=max_results
        ).execute()
        return [{"title": v["snippet"]["title"], "published_at": v["snippet"]["publishedAt"]}
                for v in resp.get("items", [])]
    except HttpError:
        return []


def generate_ai_summary(changes: list[dict], new_videos: dict) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    strategy = (MEMORY_DIR / "channel_strategy.md").read_text() if (MEMORY_DIR / "channel_strategy.md").exists() else ""

    changes_text = "\n".join([
        f"- {c['name']}: {c['prev_subs']:,} → {c['curr_subs']:,} subs "
        f"({'+' if c['sub_delta']>=0 else ''}{c['sub_delta']:,}), "
        f"+{c['view_delta']:,} views this week"
        for c in changes
    ])

    videos_text = "\n".join([
        f"- {ch}: {', '.join(v['title'][:50] for v in vids[:2])}"
        for ch, vids in new_videos.items() if vids
    ])

    prompt = f"""You are a YouTube channel growth analyst for a space ambient music channel.

Here is the channel owner's strategy:
{strategy}

Here are this week's competitor updates:
{changes_text}

Recent videos posted by competitors:
{videos_text}

Write a concise weekly insight (5–7 bullet points) covering:
1. Which competitor is growing fastest and why it matters
2. Any notable new videos to study (title patterns, themes)
3. One specific action the channel owner should take this week
4. Any emerging trends or opportunities

Be direct and specific. Reference real channel names and numbers."""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def send_to_slack(message: str):
    if not SLACK_WEBHOOK:
        print("No SLACK_WEBHOOK_URL set — skipping Slack.")
        return
    payload = json.dumps({"text": message}).encode()
    req = urllib.request.Request(
        SLACK_WEBHOOK, data=payload,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)
    print("Sent to Slack.")


def update_csv(rows: list[dict], current_stats: dict, fieldnames: list[str]):
    for r in rows:
        cid = r["URL"].split("/")[-1]
        if cid in current_stats:
            stats = current_stats[cid]["statistics"]
            r["Subscribers"] = stats.get("subscriberCount", r["Subscribers"])
            r["Total Views"] = stats.get("viewCount", r["Total Views"])
            r["Video Count"] = stats.get("videoCount", r["Video Count"])

    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Updated {DATA_FILE}")


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting weekly monitor...")

    yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # Load stored data
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    space = [r for r in all_rows if r.get("Theme") == "Space ✓" and r["Subscribers"].isdigit()]
    channel_ids = [r["URL"].split("/")[-1] for r in space]

    if not channel_ids:
        print("No Space ✓ channels to monitor.")
        return

    # Fetch current stats
    current_stats = fetch_current_stats(yt, channel_ids[:50])

    # Compute deltas
    changes = []
    for r in space:
        cid = r["URL"].split("/")[-1]
        if cid not in current_stats:
            continue
        curr_subs = int(current_stats[cid]["statistics"].get("subscriberCount", 0))
        curr_views = int(current_stats[cid]["statistics"].get("viewCount", 0))
        prev_subs = int(r["Subscribers"])
        prev_views = int(r["Total Views"])
        changes.append({
            "name": r["Channel Name"],
            "channel_id": cid,
            "prev_subs": prev_subs,
            "curr_subs": curr_subs,
            "sub_delta": curr_subs - prev_subs,
            "view_delta": curr_views - prev_views,
        })

    changes.sort(key=lambda x: x["sub_delta"], reverse=True)

    # Fetch recent videos from top channels
    new_videos = {}
    for ch in changes[:5]:
        print(f"  Fetching recent videos: {ch['name']}")
        new_videos[ch["name"]] = fetch_recent_videos(yt, ch["channel_id"])
        time.sleep(1)

    # Generate AI summary
    print("Generating AI summary...")
    ai_summary = generate_ai_summary(changes, new_videos)

    # Build Slack message
    date_str = datetime.now().strftime("%Y-%m-%d")
    slack_msg = f"*📡 Weekly Space Channel Monitor — {date_str}*\n\n"
    slack_msg += "*Competitor Subscriber Changes:*\n"
    for c in changes:
        arrow = "📈" if c["sub_delta"] > 0 else ("📉" if c["sub_delta"] < 0 else "➡️")
        delta = f"+{c['sub_delta']:,}" if c["sub_delta"] >= 0 else f"{c['sub_delta']:,}"
        slack_msg += f"{arrow} *{c['name']}* — {c['curr_subs']:,} subs ({delta}) | +{c['view_delta']:,} views\n"

    slack_msg += f"\n*AI Insights:*\n{ai_summary}"

    print("\n" + slack_msg)
    send_to_slack(slack_msg)

    # Save report
    MEMORY_DIR.mkdir(exist_ok=True)
    report_file = MEMORY_DIR / f"monitor_{date_str}.md"
    report_file.write_text(slack_msg)
    print(f"Report saved to {report_file}")

    # Update CSV with latest stats
    update_csv(all_rows, current_stats, fieldnames)
    print("Done.")


def run_your_channel():
    """Run your_channel_analytics.py as part of the weekly report."""
    import subprocess
    script = Path(__file__).parent / "your_channel_analytics.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("Your channel stats updated.")
    else:
        print(f"Channel stats error: {result.stderr[:200]}")


if __name__ == "__main__":
    run_your_channel()
    main()
