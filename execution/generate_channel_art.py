"""
generate_channel_art.py

Generates YouTube channel art for Nebula Drift using Gemini image generation.
Produces two files:
  - .tmp/banner.png       — 2560x1440px YouTube channel banner
  - .tmp/profile.png      — 800x800px profile picture

Usage:
  python execution/generate_channel_art.py --banner
  python execution/generate_channel_art.py --profile
  python execution/generate_channel_art.py --both
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

import requests
from PIL import Image
import io

OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"

# Image generation via Hugging Face Inference API (free with account)
# Model: FLUX.1-schnell — fast, high quality, free on HF
HF_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
HF_TOKEN = os.getenv("HF_TOKEN", "")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

BANNER_PROMPT = """
A stunning YouTube channel banner for a space ambient music channel called "Nebula Drift".

Wide cinematic format. Deep black space background. A single large glowing nebula
in rich purple, blue and teal tones dominates the center-left. Shimmering stardust
and subtle gas clouds fill the background. Photorealistic, 8K quality, cinematic.

Center of the image shows the channel name "Nebula Drift" in clean, elegant white
typography — modern sans-serif, slightly glowing. Below it in smaller text:
"Deep Space Ambient Music".

Right side of the image fades into darker space. Left side has the main nebula glow.
The overall mood is peaceful, vast, and cinematic — like floating through the cosmos.
No people, no planets, no spacecraft. Dark and moody.
"""

PROFILE_PROMPT = """
A YouTube channel profile picture / logo for "Nebula Drift", a space ambient music channel.

Square format. Dark black background. A beautiful glowing cosmic nebula or galaxy
in the center — rich purple, blue and teal colors, softly glowing.

The letter "N" or the letters "ND" subtly integrated into the nebula shape,
or the nebula itself as a standalone icon without text.

Simple, clean, recognizable at small sizes (will be shown as a small circle).
Photorealistic nebula art, cinematic quality. No people, no faces.
Minimal design — the nebula IS the logo.
"""

# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

def generate_image(prompt: str, label: str) -> bytes:
    """Generate image via Hugging Face Inference API (free with HF account).
    Uses FLUX.1-schnell — fast, high quality, free tier available."""
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    else:
        print("  Warning: no HF_TOKEN set — request may be slow or blocked.")
        print("  Get a free token at: https://huggingface.co/settings/tokens")

    print(f"Calling Hugging Face FLUX.1-schnell for {label}...")
    print("  (First call may take 20-60s while model loads)")

    resp = requests.post(
        HF_API_URL,
        headers=headers,
        json={"inputs": prompt},
        timeout=120,
    )

    if resp.status_code == 200:
        return resp.content

    if resp.status_code == 503:
        raise RuntimeError(
            "Model is loading on Hugging Face servers — wait 30s and try again."
        )

    raise RuntimeError(
        f"Hugging Face API error {resp.status_code}: {resp.text[:300]}\n"
        "Make sure HF_TOKEN is set in your .env file."
    )


def resize_and_save(image_bytes: bytes, target_size: tuple, output_path: Path) -> Path:
    """Resize image to exact target dimensions and save as PNG."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_resized = img.resize(target_size, Image.LANCZOS)
    output_path.parent.mkdir(exist_ok=True)
    img_resized.save(output_path, "PNG")
    size_kb = output_path.stat().st_size // 1024
    print(f"  Saved: {output_path}  ({target_size[0]}x{target_size[1]}px, {size_kb}KB)")
    return output_path


def generate_banner() -> Path:
    output_path = OUTPUT_DIR / "banner.png"
    image_bytes = generate_image(BANNER_PROMPT, "channel banner")
    return resize_and_save(image_bytes, (2560, 1440), output_path)


def generate_profile() -> Path:
    output_path = OUTPUT_DIR / "profile.png"
    image_bytes = generate_image(PROFILE_PROMPT, "profile picture")
    return resize_and_save(image_bytes, (800, 800), output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate Nebula Drift channel art")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--banner", action="store_true", help="Generate channel banner (2560x1440)")
    group.add_argument("--profile", action="store_true", help="Generate profile picture (800x800)")
    group.add_argument("--both", action="store_true", help="Generate both banner and profile")
    args = parser.parse_args()

    results = []

    if args.banner or args.both:
        path = generate_banner()
        results.append(f"Banner: {path}")

    if args.profile or args.both:
        path = generate_profile()
        results.append(f"Profile: {path}")

    print("\n✓ Channel art ready:")
    for r in results:
        print(f"  {r}")
    print("\nUpload to YouTube Studio → Customization → Branding")


if __name__ == "__main__":
    main()
