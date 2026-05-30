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

SYSTEM_PROMPT = """You are a YouTube metadata specialist for Nebula Drift —
a space ambient music channel. You write titles, descriptions, and tags
that are optimized for YouTube search and click-through rate in the space
ambient / cosmic music niche.

Key context:
- Channel: Nebula Drift (@nebuladriftambient)
- Style: Cinematic deep space ambient, like VIATMOS
- Title formula: "[Visual scene] — [Duration] Deep Space Ambient for [use case]"
- Example titles from top competitor VIATMOS:
  "Flows of Universes — Deep Space Ambient & Meditative Cosmic Journey"
  "Black Hole — Deep Space Ambient Music for Focus and Relaxation"
- Target audience: people studying, sleeping, meditating, working
- Always return valid JSON only — no markdown, no explanation outside the JSON
"""


def generate_metadata(theme: str, duration_hours: int = 1, video_number: str = "") -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    number_str = f" (video #{video_number})" if video_number else ""
    prompt = f"""Generate YouTube metadata for a Nebula Drift video{number_str}.

Theme/visual: {theme}
Duration: {duration_hours} hour{"s" if duration_hours != 1 else ""}

Generate:
1. title — max 70 characters, follow the formula
2. description — 4 short paragraphs:
   - Hook sentence about the visual/mood
   - What it is and what it's good for (studying, sleep, focus, meditation)
   - Line about Nebula Drift and weekly uploads
   - Subscribe CTA with handle @nebuladriftambient
   End with a blank line then: #SpaceAmbient #NebulaMusic #DeepSpaceMusic
3. tags — 20 tags as an array, mix of broad (ambient music, sleep music)
   and specific (space ambient, nebula music, cosmic drift, deep space music)

Return ONLY this JSON structure, nothing else:
{{
  "title": "...",
  "description": "...",
  "tags": ["...", "..."]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
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
