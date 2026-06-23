"""
analyze_video.py

Watch a local video file and describe its visual content using Claude's vision API.
Extracts evenly-spaced frames with ffmpeg and sends them to Claude.

Two modes:
  1. Default (describe)  — scene, colors, mood, + suggested YouTube titles.
                           Used before writing metadata / assembling a video.
  2. --motion            — analyze MOTION across frames (forward travel vs zoom/rotate,
                           parallax, morphing, loop quality). Used to critique AI-generated
                           clips before regenerating with a better prompt.

Usage:
  python execution/analyze_video.py ".tmp/raw/video_01.mp4"
  python execution/analyze_video.py "clip.mp4" --motion
  python execution/analyze_video.py "clip.mp4" --frames 12

Dependencies: ffmpeg, anthropic (pip install anthropic), ANTHROPIC_API_KEY in .env
"""

import os
import sys
import base64
import json
import argparse
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()


def video_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def extract_frames(path: str, num_frames: int = 8) -> list[str]:
    """Return num_frames evenly-spaced frames as base64 JPEG strings (in time order)."""
    duration = video_duration(path)
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(num_frames):
            # spread across the clip; for a single frame just grab the middle
            t = duration * (i / (num_frames - 1)) if num_frames > 1 else duration / 2
            fp = os.path.join(tmp, f"f{i:02d}.jpg")
            subprocess.run(
                ["ffmpeg", "-ss", f"{t:.3f}", "-i", path, "-vframes", "1",
                 "-vf", "scale=640:360:force_original_aspect_ratio=decrease",
                 "-q:v", "3", fp],
                capture_output=True,
            )
            if os.path.exists(fp):
                frames.append(base64.standard_b64encode(open(fp, "rb").read()).decode())
    return frames


def build_frame_blocks(frames: list[str], duration: float) -> list[dict]:
    blocks = []
    for i, f in enumerate(frames):
        t = duration * (i / (len(frames) - 1)) if len(frames) > 1 else 0
        blocks.append({"type": "text", "text": f"Frame {i+1} (t={t:.1f}s):"})
        blocks.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg", "data": f}})
    return blocks


DESCRIBE_PROMPT = (
    "These frames are from a space ambient video for the YouTube channel 'Nebula Drift' "
    "(1-hour+ deep space ambient music with cosmic visuals).\n\n"
    "Respond with ONLY a valid JSON object in this exact format:\n"
    "{\n"
    '  "scene_type": "brief scene label (e.g. purple nebula, starfield, galaxy core)",\n'
    '  "dominant_colors": ["color1", "color2", "color3"],\n'
    '  "mood": "1-2 sentence mood/atmosphere description",\n'
    '  "visual_details": "2-3 sentence description of what is visually shown",\n'
    '  "suggested_titles": ["title 1", "title 2", "title 3"]\n'
    "}\n\n"
    "Title formula: [What is visually shown] Deep Space Ambient Music for Sleep, Study & Relaxation. "
    "Do NOT use the em dash character. Do NOT put 'Nebula Drift' in the titles. Only output the JSON."
)

MOTION_PROMPT = (
    "These frames are in time order from an AI-generated space video clip. "
    "Analyze the MOTION across the frames and report concisely:\n"
    "1. Is the camera genuinely moving forward (dolly), or is it zooming/pulsing/rotating/static? "
    "Look for parallax (near stars streaking past faster than distant ones).\n"
    "2. What specifically makes it read as fake or artificial (uniform scaling, morphing clouds, breathing zoom, etc.)?\n"
    "3. Do the nebula/dust clouds keep their shape, or do they morph unnaturally?\n"
    "4. Loop quality: does the last frame closely match the first (for a seamless loop)?\n"
    "5. Concrete prompt changes to fix the issues for the next generation.\n"
    "Be specific and practical."
)


def analyze(path: str, motion: bool, num_frames: int) -> str:
    import anthropic
    duration = video_duration(path)
    frames = extract_frames(path, num_frames)
    if not frames:
        raise RuntimeError("Could not extract frames. Is ffmpeg installed?")
    content = build_frame_blocks(frames, duration)
    content.append({"type": "text", "text": MOTION_PROMPT if motion else DESCRIBE_PROMPT})
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-opus-4-8", max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )
    return msg.content[0].text.strip()


def main():
    ap = argparse.ArgumentParser(description="Describe or critique a local video with Claude vision.")
    ap.add_argument("video", help="Path to the video file")
    ap.add_argument("--motion", action="store_true",
                    help="Critique motion/loop quality instead of describing content")
    ap.add_argument("--frames", type=int, default=8, help="Number of frames to sample (default 8)")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: file not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    mode = "motion analysis" if args.motion else "visual description"
    print(f"Extracting {args.frames} frames and running {mode}...", file=sys.stderr)
    result = analyze(args.video, args.motion, args.frames)

    if not args.motion:
        # describe mode returns JSON — strip code fences if present, pretty-print
        raw = result
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            print(json.dumps(json.loads(raw.strip()), indent=2))
            return
        except json.JSONDecodeError:
            pass
    print(result)


if __name__ == "__main__":
    main()
