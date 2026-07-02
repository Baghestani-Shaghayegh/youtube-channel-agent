"""
generate_metadata.py

Generates YouTube title, description, and tags for a Nebula Drift video
using Claude. Based on VIATMOS title formula and channel strategy.

Usage:
  python execution/generate_metadata.py --theme "purple nebula" --duration 1
  python execution/generate_metadata.py --file ".tmp/final_01.mp4"

Output: prints JSON + saves to .tmp/metadata_<number>.json
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

import anthropic

OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"

SYSTEM_PROMPT = """You write YouTube titles and descriptions for Nebula Drift,
a space ambient music channel. Your job is to sound like a real person, not
AI-generated marketing copy. Winner channels in this niche (VIATMOS, Astral
Ambience, AMBIENT CIVILIZATION) title each video as a named concept/place/story,
and their descriptions are short, concrete, and plain.

TITLE format: "[Evocative concept] | [short descriptor] for [1-2 use cases]"
- The concept is a NAME for the experience, like a track name or a place:
  "The Silent Spiral", "Adrift Beneath a Billion Stars", "ORION'S GATE",
  "The Last Starlight", "Stranded"
- Max 70 chars. NEVER use an em dash (use |). Never put "Nebula Drift" in it.
- NOT keyword soup: never "X | Deep Space Ambient for Sleep, Study & Relaxation"

DESCRIPTION format (short, 3 blocks, ~5 lines total):
1. One concrete sentence about what is literally in the video. Plain words.
2. What the music is, honestly: "One hour of continuous ambient drone. No drums,
   no melody, no interruptions." + what to use it for, with ONE small human touch
   (e.g. "or staring at the ceiling at 2am").
3. "New space ambient every Tuesday and Friday." newline "@nebuladriftambient"
Then a blank line and exactly 3 hashtags relevant to the video.

BANNED (AI tells): em dashes, "journey", "immersive", "serene", "tranquility",
"soundscape", "Let the...", "guide you", "drift into", "whether you're",
"perfect for", "dose of", "explore the cosmos", exclamation marks, and any
four-paragraph parallel structure.

Always return valid JSON only — no markdown, no explanation outside the JSON.
"""


def generate_metadata(theme: str, duration_hours: int = 1, video_number: str = "") -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    number_str = f" (video #{video_number})" if video_number else ""
    prompt = f"""Generate YouTube metadata for a Nebula Drift video{number_str}.

Theme/visual: {theme}
Duration: {duration_hours} hour{"s" if duration_hours != 1 else ""}

Generate:
1. title — concept-first per the system prompt format, max 70 chars, no em dash
2. description — the 3-block human format from the system prompt (short, concrete,
   no banned words)
3. tags — 20 tags as an array, mix of broad (ambient music, sleep music)
   and specific (space ambient, ambient drone, deep space music, 1 hour ambient)

Return ONLY this JSON structure, nothing else:
{{
  "title": "...",
  "description": "...",
  "tags": ["...", "..."]
}}"""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # Extract JSON (handles cases where model adds extra text)
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        raise ValueError(f"Could not parse JSON from response:\n{text[:300]}")

    metadata = json.loads(json_match.group())

    # Validate required keys
    for key in ("title", "description", "tags"):
        if key not in metadata:
            raise ValueError(f"Missing key '{key}' in generated metadata")

    return metadata


def save_metadata(metadata: dict, video_number: str = "") -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    suffix = video_number if video_number else datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUTPUT_DIR / f"metadata_{suffix}.json"
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    return path


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube metadata for Nebula Drift")
    parser.add_argument("--theme", default="cosmic nebula drift",
                        help="Video theme or visual description")
    parser.add_argument("--duration", type=int, default=1,
                        help="Video duration in hours (default: 1)")
    parser.add_argument("--file", default="",
                        help="Path to the video file (used to extract number)")
    args = parser.parse_args()

    # Extract video number from file path if provided
    video_number = ""
    if args.file:
        match = re.search(r"(\d+)", Path(args.file).stem)
        if match:
            video_number = match.group(1).zfill(2)

    print(f"Generating metadata for: '{args.theme}' ({args.duration}hr)...")
    metadata = generate_metadata(args.theme, args.duration, video_number)

    print("\n" + "=" * 60)
    print(f"Title:\n  {metadata['title']}")
    print(f"\nDescription:\n{metadata['description']}")
    print(f"\nTags:\n  {', '.join(metadata['tags'])}")
    print("=" * 60)

    path = save_metadata(metadata, video_number)
    print(f"\nSaved: {path}")
    return metadata


if __name__ == "__main__":
    main()
