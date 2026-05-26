"""
assemble_video.py

Assembles a YouTube-ready video by looping a raw video clip and audio track
to a target duration using ffmpeg. No re-encoding on the video = fast.

Usage:
  python execution/assemble_video.py \
    --video ".tmp/raw/nebula_clip.mp4" \
    --audio ".tmp/raw/ambient_track.mp3" \
    --duration 3600 \
    --title "Purple Nebula Drift — 1 Hour Deep Space Ambient"

Output: .tmp/final_<slug>.mp4

Requirements:
  ffmpeg installed (brew install ffmpeg / apt install ffmpeg)
"""

import os
import sys
import re
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"
MEMORY_DIR = Path(__file__).parent.parent / "memory"
UPLOAD_HISTORY = MEMORY_DIR / "upload_history.md"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def check_ffmpeg() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_ffprobe() -> bool:
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_duration(file_path: Path) -> float:
    """Get duration of a media file in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(file_path)
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def assemble_video(
    video_path: Path,
    audio_path: Path,
    target_duration: int,
    title: str,
    output_path: Path = None
) -> Path:
    """
    Loop video and audio independently to target_duration, then merge.

    Strategy:
    - Video: stream-loop (no re-encode, very fast for H.264 source)
    - Audio: stream-loop, then re-encode to AAC (required for mixing)
    - Merge: combine looped video + looped audio, trim to exact duration
    """

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Extract number from video filename (e.g. video_01.mp4 → "01")
    # Falls back to slugified title or timestamp if no number found
    num_match = re.search(r"(\d+)", video_path.stem)
    if num_match:
        file_number = num_match.group(1).zfill(2)  # ensure at least 2 digits
        slug = file_number
    elif title:
        slug = slugify(title)
    else:
        slug = datetime.now().strftime("%Y%m%d-%H%M%S")

    if output_path is None:
        output_path = OUTPUT_DIR / f"final_{slug}.mp4"

    print(f"\n{'='*60}")
    print(f"Nebula Drift — Video Assembly")
    print(f"{'='*60}")
    print(f"Video : {video_path.name}")
    print(f"Audio : {audio_path.name}")
    print(f"Target: {format_duration(target_duration)}")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")

    # --- Step 1: Loop video to target duration ---
    # Use stream copy (no re-encode) — much faster for H.264
    looped_video = OUTPUT_DIR / f"_tmp_video_{slug}.mp4"
    print("Step 1/3: Looping video (stream copy, no re-encode)...")

    cmd_video = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(video_path),
        "-t", str(target_duration),
        "-c:v", "copy",
        "-an",                        # strip audio from video track
        str(looped_video)
    ]
    result = subprocess.run(cmd_video, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Video loop failed:\n{result.stderr[-500:]}")
    print(f"  Done — {looped_video.stat().st_size / 1024 / 1024:.0f} MB")

    # --- Step 2: Loop audio to target duration ---
    # Convert to AAC so it merges cleanly with the video container
    looped_audio = OUTPUT_DIR / f"_tmp_audio_{slug}.m4a"
    print("Step 2/3: Looping audio (encoding to AAC)...")

    cmd_audio = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(audio_path),
        "-t", str(target_duration),
        "-c:a", "aac",
        "-b:a", "192k",
        "-vn",                        # no video
        str(looped_audio)
    ]
    result = subprocess.run(cmd_audio, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio loop failed:\n{result.stderr[-500:]}")
    print(f"  Done — {looped_audio.stat().st_size / 1024 / 1024:.0f} MB")

    # --- Step 3: Merge video + audio ---
    print("Step 3/3: Merging video and audio...")

    cmd_merge = [
        "ffmpeg", "-y",
        "-i", str(looped_video),
        "-i", str(looped_audio),
        "-c:v", "copy",               # keep video as-is (already looped)
        "-c:a", "copy",               # keep AAC as-is
        "-shortest",                   # stop at whichever stream ends first
        str(output_path)
    ]
    result = subprocess.run(cmd_merge, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Merge failed:\n{result.stderr[-500:]}")

    # Clean up temp files
    looped_video.unlink(missing_ok=True)
    looped_audio.unlink(missing_ok=True)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  Done — {size_mb:.0f} MB")

    # --- Verify duration with ffprobe ---
    if check_ffprobe():
        actual_duration = get_duration(output_path)
        if actual_duration > 0:
            print(f"\nVerification: {format_duration(int(actual_duration))} (target: {format_duration(target_duration)})")
            if abs(actual_duration - target_duration) > 10:
                print(f"  WARNING: Duration off by {abs(actual_duration - target_duration):.0f}s")

    print(f"\n✓ Final video ready: {output_path}")
    print(f"  Size: {size_mb:.0f} MB ({size_mb / 1024:.1f} GB)")
    return output_path


def log_to_history(video_path: Path, audio_path: Path, title: str,
                   target_duration: int, output_path: Path):
    """Append this assembly to memory/upload_history.md."""
    MEMORY_DIR.mkdir(exist_ok=True)

    entry = (
        f"\n## {datetime.now().strftime('%Y-%m-%d')}\n"
        f"- **Title**: {title}\n"
        f"- **Video clip**: {video_path.name}\n"
        f"- **Audio track**: {audio_path.name}\n"
        f"- **Duration**: {format_duration(target_duration)}\n"
        f"- **Output**: {output_path}\n"
        f"- **Uploaded**: no\n"
    )

    if UPLOAD_HISTORY.exists():
        existing = UPLOAD_HISTORY.read_text()
        UPLOAD_HISTORY.write_text(existing + entry)
    else:
        UPLOAD_HISTORY.write_text(
            "# Upload History\n\nTrack of all assembled videos for Nebula Drift.\n" + entry
        )

    print(f"  Logged to {UPLOAD_HISTORY}")


def main():
    parser = argparse.ArgumentParser(description="Assemble a Nebula Drift YouTube video")
    parser.add_argument("--video", required=True, help="Path to raw video clip")
    parser.add_argument("--audio", required=True, help="Path to music track")
    parser.add_argument("--duration", type=int, default=3600,
                        help="Target duration in seconds (default: 3600 = 1 hour)")
    parser.add_argument("--title", default="",
                        help="Video title (used for filename slug)")
    parser.add_argument("--output", default=None,
                        help="Custom output path (optional)")
    args = parser.parse_args()

    # Check ffmpeg
    if not check_ffmpeg():
        print("ERROR: ffmpeg is not installed.")
        print("  Mac:   brew install ffmpeg")
        print("  VPS:   sudo apt install -y ffmpeg")
        sys.exit(1)

    video_path = Path(args.video).expanduser().resolve()
    audio_path = Path(args.audio).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else None

    title = args.title or video_path.stem

    output = assemble_video(
        video_path=video_path,
        audio_path=audio_path,
        target_duration=args.duration,
        title=title,
        output_path=output_path,
    )

    log_to_history(video_path, audio_path, title, args.duration, output)

    print(f"\nNext steps:")
    print(f"  1. Generate thumbnail: python execution/generate_thumbnail.py \"{title}\"")
    print(f"  2. Upload to YouTube manually (or ask Nova to trigger upload script)")
    print(f"  3. Nova will mark it as uploaded in memory/upload_history.md")


if __name__ == "__main__":
    main()
