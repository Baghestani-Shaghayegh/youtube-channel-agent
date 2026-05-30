"""
next_publish_time.py

Prints the next scheduled YouTube publish datetime based on the channel strategy.
Publish day: Friday, Publish time: 20:00 UTC.
If today is Friday but it's already past 20:00 UTC, returns next Friday.

Usage:
  python execution/next_publish_time.py

Output (stdout):
  2026-06-05T20:00:00   ← ISO 8601, UTC, ready to pass to --schedule
"""

from datetime import datetime, timezone, timedelta

PUBLISH_WEEKDAY = 4      # Monday=0 … Friday=4 … Sunday=6
PUBLISH_HOUR_UTC = 20   # 8pm UTC = 3pm EST / 12pm PST


def next_publish_time() -> datetime:
    now = datetime.now(timezone.utc)
    days_ahead = PUBLISH_WEEKDAY - now.weekday()

    # Same weekday but past the publish hour → push to next week
    if days_ahead < 0 or (days_ahead == 0 and now.hour >= PUBLISH_HOUR_UTC):
        days_ahead += 7

    target = now + timedelta(days=days_ahead)
    return target.replace(hour=PUBLISH_HOUR_UTC, minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    dt = next_publish_time()
    print(dt.strftime("%Y-%m-%dT%H:%M:%S"))
