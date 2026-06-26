"""
assemble_video.py

Assembles a YouTube-ready video by:
  1. Preprocessing the raw clip — removes Veo watermark + creates seamless loop
  2. Looping the clean clip to target duration
  3. Looping the audio track
  4. Merging both into a final MP4

Usage:
  python execution/assemble_video.py \
    --video ".tmp/raw/video_01.mp4" \
    --audio ".tmp/raw/audio_01.mp3" \
    --duration 3600 \
    --title "Purple Nebula Drift — 1 Hour Deep Space Ambient"

Output: .tmp/final_01.mp4

Requirements:
  ffmpeg installed (brew install ffmpeg / apt install ffmpeg)
"""

import os
import sys
import re
import math
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
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
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


def make_seamless_audio_loop(audio_path: Path, output: Path, crossfade: float = 3.0) -> Path:
    """Build a seamless, crossfade-looping audio unit.

    A plain -stream_loop concatenation produces an audible click/level-drop at
    every repeat because the track's end and start don't match. We fix that the
    same way the video is fixed: crossfade the tail back into the head so the
    unit's end flows continuously into its own start when looped.

    Unit = mid + acrossfade(tail, head):
      mid   = A[CF : DUR-CF]      (plays the steady middle)
      tail  = A[DUR-CF : DUR]     (continues smoothly out of mid)
      head  = A[0 : CF]           (fades in to where mid begins)
      acrossfade(tail, head) is an equal-power blend, so when the unit loops the
      end (~A[CF]) meets the start (A[CF]) with no jump.
    Loop unit length = DUR - CF.
    """
    duration = get_duration(audio_path)
    if duration <= 0:
        raise RuntimeError(f"Could not read duration of {audio_path.name}.")

    # keep the crossfade sane for short clips
    cf = min(crossfade, duration / 4)
    mid_end = duration - cf

    filtergraph = (
        f"[0:a]atrim={cf:.4f}:{mid_end:.4f},asetpts=N/SR/TB[mid];"
        f"[0:a]atrim={mid_end:.4f}:{duration:.4f},asetpts=N/SR/TB[tail];"
        f"[0:a]atrim=0:{cf:.4f},asetpts=N/SR/TB[head];"
        f"[tail][head]acrossfade=d={cf:.4f}:c1=tri:c2=tri[blend];"
        f"[mid][blend]concat=n=2:v=0:a=1[out]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-filter_complex", filtergraph,
        "-map", "[out]",
        "-c:a", "pcm_s16le",   # lossless intermediate so repeated looping stays clean
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Seamless audio loop failed:\n{result.stderr[-500:]}")
    return output


def format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def get_video_dimensions(file_path: Path) -> tuple:
    """Return (width, height) of the first video stream."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(file_path)
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return (1920, 1080)  # safe fallback
    try:
        w, h = result.stdout.strip().split(",")
        return (int(w), int(h))
    except Exception:
        return (1920, 1080)


def preprocess_clip(raw_clip: Path, output: Path, fade_duration: float = 2.0) -> Path:
    """
    Fix the raw clip before looping:
      1. Remove Veo watermark via delogo (inpaints from surrounding pixels)
      2. Create a mathematically seamless crossfade loop

    Seamless loop math (the key insight):
      The bridge crossfades from the ENDING into the BEGINNING of the clip.
      After the bridge, the video is at frame[fade_duration] — NOT frame[0].
      So main must ALSO start at frame[fade_duration], not frame[0].
      That way: end-of-bridge = start-of-main = same frame → truly seamless.

      Timeline of the processed clip:
        [fade_dur → fade_start] + [bridge: ending→beginning]
         ^starts at F             ^ends at frame[F]
      When looped: ...frame[F]...frame[fade_start]...bridge...frame[F]...  ✓

    Re-encodes the clip (required for filters). Fast because clips are short.
    """
    duration = get_duration(raw_clip)
    if duration <= 0:
        raise RuntimeError(f"Could not read duration of {raw_clip.name}. Is ffprobe installed?")

    # Cap fade to a quarter of the clip length
    fade_duration = min(fade_duration, duration / 4)
    fade_start = duration - fade_duration

    # Literal pixel dimensions — avoids iw/ih expression failures on newer ffmpeg
    vid_w, vid_h = get_video_dimensions(raw_clip)

    # Watermark removal: crop off the bottom 70px (where Veo watermark lives)
    # then scale back to original size. Clean result — no black box, no artifacts.
    # The ~6% vertical scale-up is invisible on slow nebula footage.
    crop_h = vid_h - 70

    print(f"  Clip: {duration:.1f}s  |  Resolution: {vid_w}x{vid_h}  |  Crossfade: {fade_duration:.1f}s")
    print(f"  Watermark: cropping bottom 70px then scaling back to {vid_w}x{vid_h}")

    # ffmpeg filter chain:
    # [0:v] → crop bottom strip → scale back up → split into 3 streams
    #   v1 → main body: from fade_duration to fade_start  ← starts at F, not 0
    #   v2 → ending: last fade_duration seconds
    #   v3 → beginning: first fade_duration seconds (used in bridge only)
    # xfade(ending → beginning) = smooth bridge, ends at frame[fade_duration]
    # concat(main, bridge) → starts at frame[F], ends at frame[F] → seamless ✓
    filter_complex = (
        # Crop bottom 70px (removes Veo watermark) then scale back to original size
        f"[0:v]crop={vid_w}:{crop_h}:0:0,scale={vid_w}:{vid_h}[clean];"
        # Split into 3 copies
        f"[clean]split=3[v1][v2][v3];"
        # Main body: fade_duration → fade_start (NOT from 0 — this is the loop fix)
        f"[v1]trim={fade_duration:.4f}:{fade_start:.4f},setpts=PTS-STARTPTS[main];"
        # Ending: last fade_duration seconds
        f"[v2]trim={fade_start:.4f}:{duration:.4f},setpts=PTS-STARTPTS[ending];"
        # Beginning: first fade_duration seconds (bridge fades into these frames)
        f"[v3]trim=0:{fade_duration:.4f},setpts=PTS-STARTPTS[beginning];"
        # Crossfade ending → beginning
        f"[ending][beginning]xfade=transition=fade:duration={fade_duration:.4f}:offset=0[bridge];"
        # Concat: main starts at frame[F], bridge ends at frame[F] → seamless
        f"[main][bridge]concat=n=2:v=1:a=0[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_clip),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",        # high quality (18 = nearly lossless)
        "-pix_fmt", "yuv420p",
        "-an",               # no audio — handled separately later
        str(output)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Clip preprocessing failed:\n{result.stderr[-700:]}")

    processed_duration = get_duration(output)
    print(f"  Preprocessed clip: {processed_duration:.1f}s  →  {output.name}")
    return output


def assemble_video(
    video_path: Path,
    audio_path: Path,
    target_duration: int,
    title: str,
    output_path: Path = None,
    fade_duration: float = 2.0,
    audio_crossfade: float = 15.0,
) -> Path:
    """
    Full pipeline:
      Step 0 — Preprocess: remove watermark + create seamless loop
      Step 1 — Loop the clean clip to target duration (stream copy, fast)
      Step 2 — Loop audio to target duration (encode to AAC)
      Step 3 — Merge video + audio into final MP4
    """

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Output filename: number from video file (video_01 → final_01)
    num_match = re.search(r"(\d+)", video_path.stem)
    if num_match:
        slug = num_match.group(1).zfill(2)
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

    # --- Step 0: Preprocess — watermark removal + seamless loop ---
    clean_clip = OUTPUT_DIR / f"_tmp_clean_{slug}.mp4"
    print("Step 0/3: Preprocessing clip (watermark removal + seamless loop)...")
    preprocess_clip(video_path, clean_clip, fade_duration=fade_duration)

    # --- Step 1: Loop the clean clip to target duration ---
    # Use concat demuxer: write a playlist of N repeats then trim to exact duration.
    # Much more reliable than -stream_loop with -c copy, which silently fails
    # on re-encoded clips and only plays through once.
    looped_video = OUTPUT_DIR / f"_tmp_video_{slug}.mp4"
    print("Step 1/3: Looping clean clip to target duration (concat)...")

    clip_duration = get_duration(clean_clip)
    if clip_duration <= 0:
        raise RuntimeError("Could not read preprocessed clip duration.")

    repeat_count = math.ceil(target_duration / clip_duration) + 2  # +2 for safety margin
    playlist_path = OUTPUT_DIR / f"_playlist_{slug}.txt"
    with open(playlist_path, "w") as f:
        for _ in range(repeat_count):
            f.write(f"file '{clean_clip.resolve()}'\n")

    cmd_video = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(playlist_path),
        "-t", str(target_duration),
        "-c:v", "copy",
        "-an",
        str(looped_video)
    ]
    result = subprocess.run(cmd_video, capture_output=True, text=True)
    playlist_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"Video loop failed:\n{result.stderr[-500:]}")
    print(f"  Done — {looped_video.stat().st_size / 1024 / 1024:.0f} MB")

    # --- Step 2: Loop audio to target duration ---
    looped_audio = OUTPUT_DIR / f"_tmp_audio_{slug}.m4a"
    print("Step 2/3: Looping audio (seamless crossfade loop, encoding to AAC)...")

    # First build a seamless crossfade loop unit so repeats don't click/drop,
    # then stream-loop that unit to the target duration.
    # 15s crossfade is the sweet spot for ambient drone — long enough that the
    # tonal morph at the loop point is gentler than the track's own natural
    # movement, so the seam is imperceptible (measured ~0.36x the mid-clip flux).
    seamless_unit = OUTPUT_DIR / f"_tmp_audioloop_{slug}.wav"
    make_seamless_audio_loop(audio_path, seamless_unit, crossfade=audio_crossfade)

    cmd_audio = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(seamless_unit),
        "-t", str(target_duration),
        # 3s fade-in so the very start eases in instead of jumping to full volume
        "-af", "afade=t=in:st=0:d=3",
        "-c:a", "aac",
        "-b:a", "192k",
        "-vn",
        str(looped_audio)
    ]
    result = subprocess.run(cmd_audio, capture_output=True, text=True)
    seamless_unit.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio loop failed:\n{result.stderr[-500:]}")
    print(f"  Done — {looped_audio.stat().st_size / 1024 / 1024:.0f} MB")

    # --- Step 3: Merge video + audio ---
    print("Step 3/3: Merging video and audio...")

    cmd_merge = [
        "ffmpeg", "-y",
        "-i", str(looped_video),
        "-i", str(looped_audio),
        "-c:v", "copy",
        "-c:a", "copy",
        "-shortest",
        str(output_path)
    ]
    result = subprocess.run(cmd_merge, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Merge failed:\n{result.stderr[-500:]}")

    # Clean up temp files
    clean_clip.unlink(missing_ok=True)
    looped_video.unlink(missing_ok=True)
    looped_audio.unlink(missing_ok=True)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  Done — {size_mb:.0f} MB")

    # --- Verify with ffprobe ---
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
    parser.add_argument("--fade", type=float, default=2.0,
                        help="Video crossfade duration in seconds for seamless loop (default: 2.0)")
    parser.add_argument("--audio-crossfade", type=float, default=15.0,
                        help="Audio loop crossfade in seconds; tune per track (default: 15.0)")
    args = parser.parse_args()

    if not check_ffmpeg():
        print("ERROR: ffmpeg is not installed.")
        print("  Mac:   brew install ffmpeg")
        print("  VPS:   sudo apt install -y ffmpeg")
        sys.exit(1)

    if not check_ffprobe():
        print("ERROR: ffprobe is not installed (comes with ffmpeg).")
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
        fade_duration=args.fade,
        audio_crossfade=args.audio_crossfade,
    )

    log_to_history(video_path, audio_path, title, args.duration, output)

    print(f"\nNext steps:")
    print(f"  1. Generate thumbnail: python execution/generate_thumbnail.py \"{title}\"")
    print(f"  2. Upload to YouTube")


if __name__ == "__main__":
    main()
