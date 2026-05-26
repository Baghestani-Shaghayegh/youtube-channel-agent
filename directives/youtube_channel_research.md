# Directive: YouTube Channel Competitive Research

> SOP for researching YouTube channels in a niche (e.g. space-theme lofi music), gathering growth metrics, and producing a competitive intelligence report. Living document — update as you learn.

## Goal

Produce a spreadsheet of competitor YouTube channels with key growth metrics to inform channel strategy: what's working, how big they are, how active, and what content performs best.

## Inputs

- **Search queries**: list of keyword strings to find channels (e.g. "space lofi music", "cosmic lofi", "galaxy lofi beats")
- **Max channels per query**: default 10
- **Recent videos to sample**: default 10 (for avg views calculation)
- **Output**: Google Sheet or local CSV in `.tmp/`

## Tools / Scripts

- `execution/youtube_channel_research.py` — discovers channels via search, pulls stats, writes output
- YouTube Data API v3 (free, 10,000 units/day quota)
  - `search.list` costs 100 units per call
  - `channels.list` costs 1 unit per call
  - `videos.list` costs 1 unit per call

## Steps

1. Run `execution/youtube_channel_research.py` with search queries for the niche
2. Script searches YouTube for channels matching each query
3. Script deduplicates and fetches full stats for each channel
4. Script fetches recent 10 videos per channel to compute recent avg views
5. Script writes results to `.tmp/channel_research.csv` (and optionally Google Sheets)
6. Review output and note top performers, upload frequency, engagement patterns

## Output Columns

| Column | Source |
|---|---|
| Channel Name | snippet |
| Channel URL | computed |
| Subscribers | statistics |
| Total Views | statistics |
| Video Count | statistics |
| Avg Views / Video | total views ÷ video count |
| Recent Avg Views | avg of last 10 videos |
| Upload Frequency | videos per month (last 10) |
| Channel Age (yrs) | snippet.publishedAt |
| Last Upload | most recent video date |
| Top Video Title | separate call |
| Top Video Views | separate call |
| Description | snippet |

## Edge Cases & Known Gotchas

- YouTube API quota is 10,000 units/day. Each search = 100 units. Budget: ~8 searches + stats lookups.
- **Per-minute search quota is ~6 searches/min** — script uses exponential backoff (10s → 20s → 40s) on 429s. Don't remove the `time.sleep(3)` between queries or the `time.sleep(1)` between per-channel video fetches.
- `subscriberCount` is hidden for channels with <1000 subs — script handles this gracefully.
- Search results include non-channel results — script filters `type=channel` only.
- Same channel can appear across multiple queries — deduplicate by channel ID.
- Some channels have 0 videos (music compilations often use Content ID) — skip or flag these.
- Python 3.9's `fromisoformat` doesn't accept 5-digit microseconds — fixed via `parse_yt_date()` regex normalization.
- 7 queries → ~58 unique channels (typical for niche lofi sub-genres). Expect 10-15 min runtime due to rate-limiting pauses.

## Changelog

- 2026-05-25 — initial draft, space lofi niche. Fixed: datetime parsing (Python 3.9), exponential backoff on 429s.
