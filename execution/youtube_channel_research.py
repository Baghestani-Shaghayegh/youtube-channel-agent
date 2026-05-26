"""
youtube_channel_research.py

Inputs:  YOUTUBE_API_KEY in .env, SEARCH_QUERIES list below
Outputs: .tmp/channel_research.csv

Discovers YouTube channels for given search queries, pulls channel stats and
recent video performance, and writes a competitive intelligence CSV.
"""

import os
import csv
import re
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

# ---------------------------------------------------------------------------
# Config — edit these to change the niche
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    "space lofi music",
    "cosmic lofi beats",
    "galaxy lofi music",
    "space ambient lofi",
    "lofi space chill",
    "space lofi hip hop",
    "interstellar lofi",
]

MAX_CHANNELS_PER_QUERY = 10   # YouTube returns at most 50
RECENT_VIDEOS_TO_SAMPLE = 10  # for computing recent avg views
OUTPUT_PATH = ".tmp/channel_research.csv"
# ---------------------------------------------------------------------------


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise EnvironmentError("YOUTUBE_API_KEY not set in .env")
    return build("youtube", "v3", developerKey=api_key)


def api_call_with_backoff(request, max_retries: int = 5):
    """Execute an API request, retrying with backoff on 429 rate-limit errors."""
    from googleapiclient.errors import HttpError
    delay = 10
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status == 429 and attempt < max_retries - 1:
                print(f"    Rate limited — waiting {delay}s before retry {attempt+1}/{max_retries-1}...")
                time.sleep(delay)
                delay *= 2
            else:
                raise


def search_channels(yt, query: str, max_results: int) -> list[str]:
    """Return a list of channel IDs matching the query."""
    resp = api_call_with_backoff(
        yt.search().list(
            q=query,
            type="channel",
            part="id",
            maxResults=max_results,
            relevanceLanguage="en",
        )
    )
    return [item["id"]["channelId"] for item in resp.get("items", [])]


def fetch_channel_stats(yt, channel_ids: list[str]) -> dict:
    """Fetch snippet + statistics for up to 50 channel IDs at once."""
    resp = api_call_with_backoff(
        yt.channels().list(
            id=",".join(channel_ids),
            part="snippet,statistics,contentDetails",
        )
    )

    channels = {}
    for item in resp.get("items", []):
        cid = item["id"]
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        channels[cid] = {
            "channel_id": cid,
            "name": snippet.get("title", ""),
            "description": snippet.get("description", "")[:200].replace("\n", " "),
            "url": f"https://www.youtube.com/channel/{cid}",
            "published_at": snippet.get("publishedAt", ""),
            "subscribers": stats.get("subscriberCount", "hidden"),
            "total_views": stats.get("viewCount", 0),
            "video_count": stats.get("videoCount", 0),
        }
    return channels


def fetch_recent_videos(yt, channel_id: str, max_results: int) -> list[dict]:
    """Return recent video IDs and publish dates for a channel."""
    resp = api_call_with_backoff(
        yt.search().list(
            channelId=channel_id,
            type="video",
            order="date",
            part="id,snippet",
            maxResults=max_results,
        )
    )
    return [
        {
            "video_id": item["id"]["videoId"],
            "published_at": item["snippet"]["publishedAt"],
            "title": item["snippet"]["title"],
        }
        for item in resp.get("items", [])
    ]


def fetch_video_stats(yt, video_ids: list[str]) -> dict:
    """Return view counts keyed by video ID."""
    if not video_ids:
        return {}
    resp = api_call_with_backoff(
        yt.videos().list(
            id=",".join(video_ids),
            part="statistics",
        )
    )
    return {
        item["id"]: int(item["statistics"].get("viewCount", 0))
        for item in resp.get("items", [])
    }


def parse_yt_date(s: str) -> datetime:
    # Python 3.9 fromisoformat only handles 0 or 6 decimal digits — normalize
    s = re.sub(r"\.(\d+)([+\-Z])", lambda m: f".{m.group(1)[:6].ljust(6,'0')}{m.group(2)}", s)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def compute_upload_frequency(publish_dates: list[str]) -> float:
    """Videos per month based on the sampled date range."""
    if len(publish_dates) < 2:
        return 0.0
    dates = sorted(parse_yt_date(d) for d in publish_dates)
    span_days = (dates[-1] - dates[0]).days or 1
    return round(len(dates) / (span_days / 30), 1)


def channel_age_years(published_at: str) -> float:
    if not published_at:
        return 0.0
    created = parse_yt_date(published_at)
    now = datetime.now(timezone.utc)
    return round((now - created).days / 365.25, 1)


def main():
    yt = get_youtube_client()
    os.makedirs(".tmp", exist_ok=True)

    # --- Step 1: discover channels across all queries ---
    print(f"Searching {len(SEARCH_QUERIES)} queries...")
    seen_ids: set[str] = set()
    ordered_ids: list[str] = []

    for i, query in enumerate(SEARCH_QUERIES):
        print(f"  '{query}'")
        ids = search_channels(yt, query, MAX_CHANNELS_PER_QUERY)
        for cid in ids:
            if cid not in seen_ids:
                seen_ids.add(cid)
                ordered_ids.append(cid)
        if i < len(SEARCH_QUERIES) - 1:
            time.sleep(3)  # stay under search-queries-per-minute quota

    print(f"Found {len(ordered_ids)} unique channels.\n")

    # --- Step 2: fetch channel stats in batches of 50 ---
    all_channel_data = {}
    for i in range(0, len(ordered_ids), 50):
        batch = ordered_ids[i : i + 50]
        all_channel_data.update(fetch_channel_stats(yt, batch))

    # --- Step 3: fetch recent videos + compute metrics per channel ---
    rows = []
    for cid, ch in all_channel_data.items():
        print(f"  Sampling videos: {ch['name']}")
        recent = fetch_recent_videos(yt, cid, RECENT_VIDEOS_TO_SAMPLE)
        time.sleep(1)  # stay under search-queries-per-minute quota

        video_ids = [v["video_id"] for v in recent]
        view_map = fetch_video_stats(yt, video_ids)

        view_counts = [view_map.get(vid, 0) for vid in video_ids]
        recent_avg = int(sum(view_counts) / len(view_counts)) if view_counts else 0

        # best video in sample
        best = max(zip(video_ids, view_counts), key=lambda x: x[1], default=(None, 0))
        best_title = next((v["title"] for v in recent if v["video_id"] == best[0]), "")

        pub_dates = [v["published_at"] for v in recent]
        last_upload = pub_dates[0] if pub_dates else ""
        upload_freq = compute_upload_frequency(pub_dates)

        subs = ch["subscribers"]
        total_views = int(ch["total_views"])
        vid_count = int(ch["video_count"]) or 1
        avg_views_all = int(total_views / vid_count)

        rows.append({
            "Channel Name": ch["name"],
            "URL": ch["url"],
            "Subscribers": subs,
            "Total Views": total_views,
            "Video Count": ch["video_count"],
            "Avg Views / Video (all time)": avg_views_all,
            "Recent Avg Views (last 10)": recent_avg,
            "Upload Frequency (videos/mo)": upload_freq,
            "Channel Age (yrs)": channel_age_years(ch["published_at"]),
            "Last Upload": last_upload[:10] if last_upload else "",
            "Top Recent Video": best_title,
            "Top Recent Video Views": best[1],
            "Description": ch["description"],
        })

    # sort by subscribers descending (hidden = last)
    rows.sort(
        key=lambda r: int(r["Subscribers"]) if str(r["Subscribers"]).isdigit() else -1,
        reverse=True,
    )

    # --- Step 4: write CSV ---
    if not rows:
        print("No results to write.")
        return

    fieldnames = list(rows[0].keys())
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {len(rows)} channels written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
