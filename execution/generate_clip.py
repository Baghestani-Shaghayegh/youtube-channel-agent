"""
generate_clip.py

Generates a short space ambient video clip using Google Veo 2,
then loops it to the target duration using ffmpeg.

Usage:
  python execution/generate_clip.py "cosmic nebula drift" --duration 7200
  (duration in seconds, default 7200 = 2 hours)

Output: .tmp/video_<slug>.mp4
"""

import os
import sys
import re
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

import google.generativeai as genai

API_KEY = os.getenv("GOOGLE_AI_API_KEY")
OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"

# Space visual prompt tuned for Nebula Drift aesthetic
BASE_PROMPT = """
Slow cinematic drift through a glowing cosmic nebula in deep space.
Rich purple, blue and teal gas clouds, shimmering stardust.
Extremely slow, peaceful camera movement — like floating weightlessly through space.
No people, no text, no planets, no spacecraft.
Photorealistic, 8K quality, dark background with luminous nebula glow.
Seamlessly loopable motion. Cinematic color grading.
"""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def loop_video(clip_path: Path, target_seconds: int, output_path: Path):
    """Loop a short clip to target duration using ffmpeg."""
    print(f"Looping clip to {target_seconds//3600}h {(target_seconds%3600)//60}m...")

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",       # loop infinitely
        "-i", str(clip_path),
        "-t", str(target_seconds),  # stop at target duration
        "-c", "copy",               # no re-encoding = fast
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr[:300]}")
    print(f"Looped video saved: {output_path}")


def generate_clip(theme: str, target_duration_sec: int = 7200) -> Path:
    genai.configure(api_key=API_KEY)

    prompt = BASE_PROMPT
    if theme:
        prompt += f"\nTheme/mood: {theme}"

    slug = slugify(theme) if theme else "nebula-drift"
    OUTPUT_DIR.mkdir(exist_ok=True)
    clip_path = OUTPUT_DIR / f"clip_{slug}_raw.mp4"
    final_path = OUTPUT_DIR / f"video_{slug}.mp4"

    # Generate clip with Veo 2
    print(f"Generating space clip: '{theme}'")
    print("Calling Veo 2 (this takes 2-5 minutes)...")

    client = genai.Client()
    operation = client.models.generate_videos(
        model="veo-3.0-generate-001",
        prompt=prompt,
        config=genai_types.GenerateVideosConfig(
            aspect_ratio="16:9",
            duration_seconds=8,
        ),
    )

    # Poll until done
    while not operation.done:
        print("  Waiting for Veo 2...")
        time.sleep(15)
        operation = client.operations.get(operation)

    if not operation.response.generated_videos:
        raise RuntimeError("Veo 2 returned no video")

    # Download clip
    video = operation.response.generated_videos[0]
    clip_path.write_bytes(client.files.download(file=video.video))
    print(f"Raw clip saved: {clip_path} ({clip_path.stat().st_size // 1024}KB)")

    # Loop to target duration
    if check_ffmpeg():
        loop_video(clip_path, target_duration_sec, final_path)
        return final_path
    else:
        print("WARNING: ffmpeg not found. Install it to loop the clip.")
        print("  Mac: brew install ffmpeg")
        print("  VPS: apt install ffmpeg")
        return clip_path


def main():
    args = sys.argv[1:]
    duration = 7200  # default 2 hours

    if "--duration" in args:
        idx = args.index("--duration")
        duration = int(args[idx + 1])
        args = args[:idx] + args[idx+2:]

    theme = " ".join(args) if args else "cosmic nebula drift"
    path = generate_clip(theme, duration)
    print(f"\nVideo ready: {path}")
    print("Add your music track, then upload to YouTube.")


if __name__ == "__main__":
    main()
