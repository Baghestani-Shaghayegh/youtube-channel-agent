#!/usr/bin/env python3
"""
agent.py — Interactive + monitoring agent for space lofi YouTube channel research.

Usage:
  python agent.py                        # interactive chat mode
  python agent.py "your question here"   # single query mode
  python agent.py --monitor              # run weekly monitoring report
"""

import os
import sys
import json
import csv
import re
import time
from pathlib import Path
from datetime import datetime, timezone
import sys
sys.path.insert(0, str(Path(__file__).parent / "execution"))
from load_env import load_env
load_env()

import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "claude-opus-4-7"
MEMORY_DIR = Path("memory")
DIRECTIVES_DIR = Path("directives")
DATA_FILE = Path(".tmp/channel_research_master.csv")
CONVERSATION_LOG = Path("memory/conversation_history.json")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")

# ---------------------------------------------------------------------------
# Memory & context loading
# ---------------------------------------------------------------------------

def load_memory() -> str:
    """Load all memory files into a single context string."""
    parts = []
    if MEMORY_DIR.exists():
        for f in sorted(MEMORY_DIR.glob("*.md")):
            parts.append(f"## Memory: {f.stem}\n{f.read_text()}")
    return "\n\n".join(parts) if parts else ""


def load_directives() -> str:
    """Load all directives into context."""
    parts = []
    if DIRECTIVES_DIR.exists():
        for f in sorted(DIRECTIVES_DIR.glob("*.md")):
            if not f.name.startswith("_"):
                parts.append(f"## Directive: {f.stem}\n{f.read_text()}")
    return "\n\n".join(parts) if parts else ""


def load_channel_data(limit: int = 20) -> str:
    """Load top channel data from CSV as context."""
    if not DATA_FILE.exists():
        return "No channel data available yet. Run youtube_channel_research.py first."
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    space = [r for r in rows if r.get("Theme") == "Space ✓"]
    space.sort(key=lambda x: int(x["Subscribers"]) if x["Subscribers"].isdigit() else 0, reverse=True)

    lines = ["## Top Space ✓ Channels (from research data)"]
    lines.append(f"{'Channel':<40} {'Subs':>10} {'Recent Avg':>12} {'Uploads/mo':>11} {'Age':>6}")
    lines.append("-" * 85)
    for r in space[:limit]:
        subs = f"{int(r['Subscribers']):,}" if r["Subscribers"].isdigit() else "hidden"
        lines.append(
            f"{r['Channel Name'][:39]:<40} {subs:>10} "
            f"{int(r['Recent Avg Views (last 10)']):>12,} "
            f"{r['Upload Frequency (videos/mo)']:>11} "
            f"{r['Channel Age (yrs)']:>6}"
        )
    return "\n".join(lines)


def load_conversation_history() -> list:
    if CONVERSATION_LOG.exists():
        try:
            return json.loads(CONVERSATION_LOG.read_text())[-20:]  # last 20 turns
        except Exception:
            return []
    return []


def save_conversation_history(history: list):
    CONVERSATION_LOG.parent.mkdir(exist_ok=True)
    CONVERSATION_LOG.write_text(json.dumps(history[-40:], indent=2))


def build_system_prompt() -> str:
    memory = load_memory()
    directives = load_directives()
    channel_data = load_channel_data()

    return f"""You are Nova — a YouTube channel growth analyst for a space-themed lofi/ambient music channel.

## Your Persona

**Who you are:** A sharp, trustworthy analyst who is genuinely invested in this channel's success. You combine professional data-driven insight with real encouragement — not empty hype, but recognition when it's earned and a push when it's needed.

**How you communicate:**
- Concise: bullets over paragraphs, numbers over vague claims. Respect the user's time.
- Direct: if a strategy is wrong, say so. Never just confirm what they want to hear.
- Warm but professional: you care about their success, but you don't sugarcoat.

**Your 6 core traits — apply all of them in every response:**

1. **Curious** — Always ask "why is this happening?" not just "what is happening." Dig one layer deeper. If a video performed well, find out what specifically caused it.

2. **Skeptical** — Question weak strategies. If the data doesn't support a plan, push back. Your value is in being right, not in being agreeable.

3. **Accountable** — You remember what was discussed. Follow up on past advice. If you recommended posting a video last week, check if they did. Hold them to their goals.

4. **Pattern spotter** — Connect dots across data points the user wouldn't notice on their own. Example: "VIATMOS uploaded on Fridays 8 of their last 10 times — that's not random."

5. **Proactive** — Flag opportunities and risks without being asked. If a competitor just had a breakout week, bring it up. Don't wait to be asked.

6. **Encouraging with teeth** — Celebrate real wins with specific recognition. Push hard when they're slipping. "You didn't post this week — VIATMOS posted twice. That gap matters."

## Your Role

You operate within a 3-layer architecture:
- Layer 1: Directives (SOPs in /directives/) — what to do
- Layer 2: You (Nova) — intelligent decision making, pattern analysis, strategy
- Layer 3: Execution scripts in /execution/ — deterministic Python tools

When the user asks you to run a script, give them the exact command.
When you learn something new, suggest updating the relevant memory or directive file.
Always reference real channel names, real numbers, real dates.

---

{memory}

---

{directives}

---

{channel_data}

---

Today's date: {datetime.now().strftime('%Y-%m-%d')}
"""

# ---------------------------------------------------------------------------
# Monitoring report
# ---------------------------------------------------------------------------

def run_monitoring_report():
    """Generate a weekly monitoring report comparing current vs stored data."""
    print("Running weekly monitoring report...")

    # Load stored data
    if not DATA_FILE.exists():
        print("No data file found. Run youtube_channel_research.py first.")
        return

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    space = [r for r in rows if r.get("Theme") == "Space ✓"]

    # Fetch current stats for monitored channels
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    yt = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
    monitor_ids = [r["URL"].split("/")[-1] for r in space if r["Subscribers"].isdigit() and int(r["Subscribers"]) > 100]

    if not monitor_ids:
        print("No channels to monitor.")
        return

    resp = yt.channels().list(id=",".join(monitor_ids[:50]), part="snippet,statistics").execute()
    current = {item["id"]: item for item in resp.get("items", [])}

    # Build report
    report_lines = [
        f"📡 *Weekly Space Channel Monitor* — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "*Key Competitor Updates:*",
    ]

    for r in space:
        cid = r["URL"].split("/")[-1]
        if cid not in current:
            continue
        curr_stats = current[cid]["statistics"]
        curr_subs = int(curr_stats.get("subscriberCount", 0))
        prev_subs = int(r["Subscribers"]) if r["Subscribers"].isdigit() else 0
        sub_delta = curr_subs - prev_subs

        curr_views = int(curr_stats.get("viewCount", 0))
        prev_views = int(r["Total Views"])
        view_delta = curr_views - prev_views

        delta_str = f"+{sub_delta:,}" if sub_delta >= 0 else f"{sub_delta:,}"
        report_lines.append(
            f"• *{r['Channel Name']}* — {curr_subs:,} subs ({delta_str} this week) | +{view_delta:,} views"
        )

    report_lines += [
        "",
        "*Your Action Items This Week:*",
        "• Post 1 new space ambient video (target: 1–3 hrs)",
        "• Check VIATMOS for new upload — study title/thumbnail",
        "• Review YouTube Studio watch time on your recent uploads",
        "",
        f"_Data: {DATA_FILE}_",
    ]

    report = "\n".join(report_lines)
    print(report)

    # Send to Slack
    if SLACK_WEBHOOK:
        import urllib.request
        payload = json.dumps({"text": report}).encode()
        req = urllib.request.Request(SLACK_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req)
        print("\nReport sent to Slack.")
    else:
        print("\n(No SLACK_WEBHOOK_URL set — skipping Slack notification)")

    # Save report to memory
    report_path = MEMORY_DIR / f"monitor_{datetime.now().strftime('%Y%m%d')}.md"
    report_path.write_text(report)
    print(f"Report saved to {report_path}")


# ---------------------------------------------------------------------------
# Interactive chat
# ---------------------------------------------------------------------------

def chat(user_input: str, history: list) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system = build_system_prompt()

    history.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=history,
    )

    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})
    return reply


def refresh_channel_stats():
    """Run your_channel_analytics.py and return the output."""
    import subprocess
    script = Path(__file__).parent / "execution" / "your_channel_analytics.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    return result.stdout if result.returncode == 0 else f"Error: {result.stderr[:300]}"


def interactive_mode():
    print("Space Lofi Channel Agent")
    print("Type your question, or 'quit' to exit.\n")

    history = load_conversation_history()
    if history:
        print(f"(Resuming from {len(history)//2} previous turns)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue

        # Auto-refresh channel stats when user asks about their channel
        channel_triggers = ["how's my channel", "my channel stats", "how am i doing",
                           "check my channel", "my views", "my subscribers", "my videos"]
        if any(t in user_input.lower() for t in channel_triggers):
            print("(Refreshing your channel stats...)")
            refresh_channel_stats()

        if user_input.lower() in ("quit", "exit", "bye"):
            save_conversation_history(history)
            print("Conversation saved. Bye!")
            break

        reply = chat(user_input, history)
        print(f"\nAgent: {reply}\n")
        save_conversation_history(history)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if not args:
        interactive_mode()
    elif args[0] == "--monitor":
        run_monitoring_report()
    else:
        # Single query mode
        query = " ".join(args)
        history = load_conversation_history()
        reply = chat(query, history)
        print(reply)
        save_conversation_history(history)


if __name__ == "__main__":
    main()
