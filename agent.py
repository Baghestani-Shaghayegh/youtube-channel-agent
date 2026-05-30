#!/usr/bin/env python3
"""
agent.py — Nova: YouTube channel growth analyst + video production assistant.

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
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent / "execution"))
from load_env import load_env
load_env()

import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-5"
MEMORY_DIR = Path("memory")
DIRECTIVES_DIR = Path("directives")
DATA_FILE = Path(".tmp/channel_research_master.csv")
CONVERSATION_LOG = Path("memory/conversation_history.json")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
RAW_DIR = Path(".tmp/raw")

# ---------------------------------------------------------------------------
# Memory & context loading
# ---------------------------------------------------------------------------

def load_memory() -> str:
    parts = []
    if MEMORY_DIR.exists():
        for f in sorted(MEMORY_DIR.glob("*.md")):
            parts.append(f"## Memory: {f.stem}\n{f.read_text()}")
    return "\n\n".join(parts) if parts else ""


def load_directives() -> str:
    parts = []
    if DIRECTIVES_DIR.exists():
        for f in sorted(DIRECTIVES_DIR.glob("*.md")):
            if not f.name.startswith("_"):
                parts.append(f"## Directive: {f.stem}\n{f.read_text()}")
    return "\n\n".join(parts) if parts else ""


def load_channel_data(limit: int = 20) -> str:
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
    if not CONVERSATION_LOG.exists():
        return []
    try:
        history = json.loads(CONVERSATION_LOG.read_text())
    except Exception:
        return []

    # Strip tool_use and tool_result blocks — they reference IDs that no
    # longer exist in a new session and cause a 400 from the API.
    # Keep only plain text turns so history loads safely every time.
    clean = []
    for msg in history:
        content = msg.get("content", "")

        # String content (normal text turn) — keep as-is
        if isinstance(content, str):
            clean.append(msg)
            continue

        # List content — filter to text blocks only
        if isinstance(content, list):
            text_blocks = [
                b for b in content
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip()
            ]
            if text_blocks:
                # Flatten to a single string so it's always safe to reload
                combined = " ".join(b["text"] for b in text_blocks)
                clean.append({"role": msg["role"], "content": combined})
            # If only tool blocks, drop the turn entirely

    return clean[-20:]


def save_conversation_history(history: list):
    CONVERSATION_LOG.parent.mkdir(exist_ok=True)
    CONVERSATION_LOG.write_text(json.dumps(history[-40:], indent=2))


def build_system_prompt() -> str:
    memory = load_memory()
    directives = load_directives()
    channel_data = load_channel_data()

    return f"""You are Nova — a YouTube channel growth analyst and video production assistant for Nebula Drift, a space-themed cosmic ambient music channel.

## Your Persona

**Who you are:** A sharp, trustworthy analyst who is genuinely invested in this channel's success. You combine professional data-driven insight with real encouragement — not empty hype, but recognition when it's earned and a push when it's needed.

**How you communicate:**
- Concise: bullets over paragraphs, numbers over vague claims. Respect the user's time.
- Direct: if a strategy is wrong, say so. Never just confirm what they want to hear.
- Warm but professional: you care about their success, but you don't sugarcoat.

**Your 6 core traits — apply all of them in every response:**

1. **Curious** — Always ask "why is this happening?" not just "what is happening." Dig one layer deeper.
2. **Skeptical** — Question weak strategies. If the data doesn't support a plan, push back.
3. **Accountable** — You remember what was discussed. Follow up on past advice.
4. **Pattern spotter** — Connect dots across data points the user wouldn't notice on their own.
5. **Proactive** — Flag opportunities and risks without being asked.
6. **Encouraging with teeth** — Celebrate real wins with specific recognition. Push hard when they're slipping.

## Your Role & Tools

You have tools you can call directly — use them without asking for permission when the intent is clear:

- **list_raw_files** — see what video clips and audio tracks are available
- **assemble_video** — loop a clip + track into a YouTube-ready video
- **generate_metadata** — generate YouTube title, description, and tags using Claude (call this first when the user wants to upload)
- **upload_video** — upload a finished video to YouTube with scheduling (only after user approves metadata)
- **send_slack_message** — notify the user on Slack when a task completes
- **read_file** — read any file in the project (scripts, directives, memory)
- **write_file** — write or overwrite any file in the project
- **run_command** — run a shell command in the project directory

## CRITICAL: Always execute immediately — never just plan

When you decide to do something, call the tool RIGHT NOW in this same response.
**Never** describe what you're about to do and then stop — that is a failure.
The correct pattern is: decide → call tool → get result → call next tool → done.
Chain all steps in one go without pausing for confirmation.

Examples of WRONG behavior:
- "I'll now fix the script and reassemble." ← then stopping with no tool call
- "Doing that now." ← then stopping with no tool call
- Listing steps you're about to take, then not taking them

Examples of RIGHT behavior:
- Immediately calling read_file, then write_file, then run_command, then assemble_video — all in one response flow

## Self-Annealing: Fix Broken Scripts Yourself

When a script fails, DO NOT just report the error and stop. Fix it immediately:
1. Read the error message carefully
2. Use **read_file** to inspect the broken script
3. Identify the exact problem
4. Use **write_file** to fix the script
5. Use **run_command** to test the fix
6. Retry the original task
7. Update the relevant directive with what you learned

Only escalate to the user if the fix requires information you truly don't have.

When assembling a video:
1. Call list_raw_files first to see what's available
2. Pick the best clip + track combo (check upload_history to avoid repeats)
3. Confirm your selection in a brief message, then immediately proceed — don't wait for a second approval unless files are ambiguous
4. Assemble the video
5. When done, send a Slack message with the result (file path, size, title)
6. Suggest the next step (thumbnail, then upload)

## Upload workflow (after assembly is done)

When the user asks to "upload", "prep the upload", "schedule it", or anything similar:
1. Identify the video file (ask once if unclear — check .tmp/ for final_*.mp4 files)
2. Call **generate_metadata** to generate title, description, and tags. Infer the theme from the filename (e.g. "nebula drift") unless you know it better from context. Duration defaults to 1.
3. Show the user a formatted preview of the generated metadata:
   - **Title:** ...
   - **Description:** (first paragraph only + "...")
   - **Tags:** (comma-separated list)
4. **STOP and wait for explicit approval** — this is the ONE exception to the "execute immediately" rule. Never upload without the user saying "looks good", "upload it", "go ahead", or similar.
5. Once approved, confirm the schedule: ask if they want a specific publish time (UTC), publish now, or keep private. If they already told you, use that.
6. Call **upload_video** with the video path, metadata path, and schedule/publish setting.
7. After upload completes, send a **send_slack_message** with: video title, YouTube URL, scheduled publish time, and a link to YouTube Studio to add the thumbnail.
   Format: "✅ *[Title]* uploaded!\nURL: [url]\nScheduled: [time or 'private']\nAdd thumbnail: [studio url]"

## Architecture

You operate within a 3-layer system:
- Layer 1: Directives (SOPs in /directives/) — what to do
- Layer 2: You (Nova) — intelligent decision making, pattern analysis, strategy
- Layer 3: Execution scripts in /execution/ — deterministic Python tools

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
# Tool definitions (Claude tool-use schema)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "list_raw_files",
        "description": "List available raw video clips and audio tracks in the .tmp/raw/ folder. Call this before assembling a video to see what files are available.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "assemble_video",
        "description": "Assemble a YouTube-ready video by looping a raw video clip and audio track to the target duration using ffmpeg. Output goes to .tmp/final_<slug>.mp4.",
        "input_schema": {
            "type": "object",
            "properties": {
                "video": {
                    "type": "string",
                    "description": "Path to the raw video clip file (e.g. .tmp/raw/nebula_clip.mp4)"
                },
                "audio": {
                    "type": "string",
                    "description": "Path to the audio track file (e.g. .tmp/raw/cosmic_track.mp3)"
                },
                "title": {
                    "type": "string",
                    "description": "YouTube video title (used for filename and metadata)"
                },
                "duration": {
                    "type": "integer",
                    "description": "Target duration in seconds. Default is 3600 (1 hour). Use 7200 for 2 hours."
                }
            },
            "required": ["video", "audio", "title"]
        }
    },
    {
        "name": "generate_metadata",
        "description": "Generate a YouTube title, description, and tags for a Nebula Drift video using Claude. Call this first when the user asks to upload. Show the result to the user and wait for their approval before uploading.",
        "input_schema": {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "description": "Visual theme or description of the video (e.g. 'purple nebula drift', 'cosmic deep space', 'red giant star')"
                },
                "duration": {
                    "type": "integer",
                    "description": "Video duration in hours (default: 1)"
                },
                "video_file": {
                    "type": "string",
                    "description": "Optional: path to the video file. Used to extract the video number so the metadata is saved as metadata_01.json etc."
                }
            },
            "required": ["theme"]
        }
    },
    {
        "name": "upload_video",
        "description": "Upload a video to YouTube with metadata. ONLY call this after the user has explicitly approved the generated title, description, and tags. Sends Slack notification when done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "video": {
                    "type": "string",
                    "description": "Path to the video file to upload (e.g. .tmp/final_01.mp4)"
                },
                "metadata": {
                    "type": "string",
                    "description": "Path to the metadata JSON file (e.g. .tmp/metadata_01.json)"
                },
                "schedule": {
                    "type": "string",
                    "description": "Optional: schedule publish time in UTC ISO format (e.g. 2026-06-07T18:00:00). If omitted and publish_now is false, video stays private."
                },
                "publish_now": {
                    "type": "boolean",
                    "description": "If true, make the video public immediately after upload."
                }
            },
            "required": ["video", "metadata"]
        }
    },
    {
        "name": "send_slack_message",
        "description": "Send a message to the Nebula Drift Slack channel. Use this to notify the user when a video assembly or other task is complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send. Use Slack markdown (*bold*, _italic_). Include key details like file path, size, and next steps."
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of any file in the project (scripts, directives, memory files). Use this to inspect a broken script before fixing it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the project root. E.g. 'execution/assemble_video.py' or 'directives/video_assembly.md'"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file in the project. Use this to fix a broken script or update a directive. Only works within the project directory — cannot write outside it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file relative to the project root. E.g. 'execution/assemble_video.py'"
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file."
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command in the project directory. Use this to test a fixed script, run ffprobe/ffmpeg diagnostics, check ffmpeg version, or validate a fix before reporting success. Output is capped at 2000 chars.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run. Runs from the project root directory. E.g. 'python3 execution/assemble_video.py --help' or 'ffmpeg -version'"
                }
            },
            "required": ["command"]
        }
    }
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_list_raw_files() -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    video_exts = {".mp4", ".mov", ".mkv", ".avi"}
    audio_exts = {".mp3", ".wav", ".flac", ".aac", ".m4a"}

    all_files = list(RAW_DIR.iterdir())
    videos = sorted([f for f in all_files if f.suffix.lower() in video_exts])
    audios = sorted([f for f in all_files if f.suffix.lower() in audio_exts])

    if not videos and not audios:
        return (
            f"No files found in {RAW_DIR}/\n"
            "Add your raw video clips and music tracks there, then ask me again."
        )

    lines = []
    if videos:
        lines.append("Video clips:")
        for v in videos:
            size_mb = v.stat().st_size / 1024 / 1024
            lines.append(f"  {v.name}  ({size_mb:.0f} MB)  [{RAW_DIR / v.name}]")
    if audios:
        lines.append("Audio tracks:")
        for a in audios:
            size_mb = a.stat().st_size / 1024 / 1024
            lines.append(f"  {a.name}  ({size_mb:.0f} MB)  [{RAW_DIR / a.name}]")
    return "\n".join(lines)


def tool_assemble_video(video: str, audio: str, title: str, duration: int = 3600) -> str:
    script = Path(__file__).parent / "execution" / "assemble_video.py"
    cmd = [
        sys.executable, str(script),
        "--video", video,
        "--audio", audio,
        "--duration", str(duration),
        "--title", title,
    ]
    print(f"\n  → Running: {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        return f"Assembly failed:\n{result.stderr[-600:]}"


def tool_generate_metadata(theme: str, duration: int = 1, video_file: str = "") -> str:
    script = Path(__file__).parent / "execution" / "generate_metadata.py"
    cmd = [
        sys.executable, str(script),
        "--theme", theme,
        "--duration", str(duration),
    ]
    if video_file:
        cmd += ["--file", video_file]
    print(f"\n  → Running: {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        return f"Metadata generation failed:\n{result.stderr[-600:]}"


def tool_upload_video(video: str, metadata: str, schedule: str = "", publish_now: bool = False) -> str:
    script = Path(__file__).parent / "execution" / "upload_to_youtube.py"
    cmd = [
        sys.executable, str(script),
        "--video", video,
        "--metadata", metadata,
    ]
    if schedule:
        cmd += ["--schedule", schedule]
    if publish_now:
        cmd.append("--publish-now")
    print(f"\n  → Running: {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent),
        timeout=600,   # uploads can take a few minutes
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        return f"Upload failed:\n{result.stderr[-600:]}"


def tool_send_slack(message: str) -> str:
    if not SLACK_WEBHOOK:
        return "No SLACK_WEBHOOK_URL set in .env — message not sent."
    payload = json.dumps({"text": message}).encode()
    req = urllib.request.Request(
        SLACK_WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        return "Slack message sent successfully."
    except Exception as e:
        return f"Slack error: {e}"


PROJECT_ROOT = Path(__file__).parent.resolve()


def tool_read_file(path: str) -> str:
    target = (PROJECT_ROOT / path).resolve()
    # Safety: must stay inside the project
    if not str(target).startswith(str(PROJECT_ROOT)):
        return f"Refused: path is outside the project directory."
    if not target.exists():
        return f"File not found: {path}"
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


def tool_write_file(path: str, content: str) -> str:
    target = (PROJECT_ROOT / path).resolve()
    # Safety: must stay inside the project
    if not str(target).startswith(str(PROJECT_ROOT)):
        return f"Refused: path is outside the project directory."
    # Safety: never overwrite .env or credentials
    if target.name in (".env", "credentials.json", "token.json", "token_yt.json", "token_upload.json"):
        return f"Refused: will not overwrite sensitive file {target.name}."
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Written: {path} ({len(content)} chars)"
    except Exception as e:
        return f"Error writing file: {e}"


def tool_run_command(command: str) -> str:
    print(f"\n  → $ {command}\n")
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=300,   # 5 min max
    )
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += result.stderr
    output = output.strip()
    if len(output) > 2000:
        output = output[:2000] + "\n...(truncated)"
    if not output:
        output = f"(exit code {result.returncode}, no output)"
    return output


def execute_tool(name: str, inputs: dict) -> str:
    """Dispatch a tool call to its implementation."""
    if name == "list_raw_files":
        return tool_list_raw_files()
    elif name == "assemble_video":
        return tool_assemble_video(**inputs)
    elif name == "generate_metadata":
        return tool_generate_metadata(**inputs)
    elif name == "upload_video":
        return tool_upload_video(**inputs)
    elif name == "send_slack_message":
        return tool_send_slack(inputs["message"])
    elif name == "read_file":
        return tool_read_file(inputs["path"])
    elif name == "write_file":
        return tool_write_file(inputs["path"], inputs["content"])
    elif name == "run_command":
        return tool_run_command(inputs["command"])
    else:
        return f"Unknown tool: {name}"


def content_to_serializable(content):
    """Convert API content blocks to plain dicts for JSON storage."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        result = []
        for block in content:
            if hasattr(block, "type"):
                if block.type == "text":
                    result.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    result.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            elif isinstance(block, dict):
                result.append(block)
        return result
    return content

# ---------------------------------------------------------------------------
# Chat with agentic tool-use loop
# ---------------------------------------------------------------------------

def chat(user_input: str, history: list) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system = build_system_prompt()

    history.append({"role": "user", "content": user_input})

    # Agentic loop — keep going until Claude stops calling tools
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            messages=history,
            tools=TOOLS,
        )

        if response.stop_reason == "tool_use":
            # Print any text Nova said before invoking tools
            for block in response.content:
                if hasattr(block, "type") and block.type == "text" and block.text.strip():
                    print(f"\nNova: {block.text.strip()}")

            # Add assistant turn to history (serializable format)
            history.append({
                "role": "assistant",
                "content": content_to_serializable(response.content)
            })

            # Execute each tool and collect results
            tool_results = []
            for block in response.content:
                if not (hasattr(block, "type") and block.type == "tool_use"):
                    continue
                print(f"\n[Tool: {block.name}]")
                result = execute_tool(block.name, block.input)
                print(result[:300] + ("..." if len(result) > 300 else ""))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            # Feed results back for the next loop iteration
            history.append({"role": "user", "content": tool_results})

        else:
            # Final text response — done
            reply = "".join(
                block.text for block in response.content
                if hasattr(block, "type") and block.type == "text"
            )
            history.append({"role": "assistant", "content": reply})
            return reply

# ---------------------------------------------------------------------------
# Monitoring report
# ---------------------------------------------------------------------------

def run_monitoring_report():
    """Generate a weekly monitoring report comparing current vs stored data."""
    print("Running weekly monitoring report...")

    if not DATA_FILE.exists():
        print("No data file found. Run youtube_channel_research.py first.")
        return

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    space = [r for r in rows if r.get("Theme") == "Space ✓"]

    from googleapiclient.discovery import build
    yt = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
    monitor_ids = [
        r["URL"].split("/")[-1]
        for r in space
        if r["Subscribers"].isdigit() and int(r["Subscribers"]) > 100
    ]

    if not monitor_ids:
        print("No channels to monitor.")
        return

    resp = yt.channels().list(id=",".join(monitor_ids[:50]), part="snippet,statistics").execute()
    current = {item["id"]: item for item in resp.get("items", [])}

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
        "• Post 1 new space ambient video (1 hour)",
        "• Check VIATMOS for new upload — study title/thumbnail",
        "• Review YouTube Studio watch time on your recent uploads",
        "",
        f"_Data: {DATA_FILE}_",
    ]

    report = "\n".join(report_lines)
    print(report)

    if SLACK_WEBHOOK:
        tool_send_slack(report)
        print("\nReport sent to Slack.")

    report_path = MEMORY_DIR / f"monitor_{datetime.now().strftime('%Y%m%d')}.md"
    report_path.write_text(report)
    print(f"Report saved to {report_path}")


# ---------------------------------------------------------------------------
# Interactive chat
# ---------------------------------------------------------------------------

def refresh_channel_stats():
    script = Path(__file__).parent / "execution" / "your_channel_analytics.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    return result.stdout if result.returncode == 0 else f"Error: {result.stderr[:300]}"


def interactive_mode():
    print("Nova — Nebula Drift Channel Assistant")
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
        print(f"\nNova: {reply}\n")
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
        query = " ".join(args)
        history = load_conversation_history()
        reply = chat(query, history)
        print(reply)
        save_conversation_history(history)


if __name__ == "__main__":
    main()
