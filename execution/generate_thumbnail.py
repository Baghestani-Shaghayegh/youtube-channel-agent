"""
generate_thumbnail.py

Generates a YouTube thumbnail for Nebula Drift using Imagen 3.

Usage:
  python execution/generate_thumbnail.py "Deep Space Nebula Journey"
  python execution/generate_thumbnail.py "Cosmic Drift" --style dark

Output: .tmp/thumbnail_<slug>.png (2560x1440 for YouTube)
"""

import os
import sys
import re
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from load_env import load_env
load_env()

from google import genai
from google.genai import types as genai_types

API_KEY = os.getenv("GOOGLE_AI_API_KEY")
OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"

# FREE TIER model — DO NOT change to imagen-* (requires paid plan)
# gemini-2.5-flash-image supports native image generation
IMAGE_MODEL = "gemini-2.5-flash-image"

# Nebula Drift thumbnail style — based on competitor research
# Dark background, single glowing nebula, minimal text, high contrast
BASE_PROMPT = """
A stunning YouTube thumbnail for a space ambient music channel called "Nebula Drift".
Deep space background, photorealistic cosmic nebula in rich purple, blue and teal tones,
glowing stardust and gas clouds, cinematic quality, 8K resolution.
Dark and moody atmosphere with one central glowing nebula or cosmic object.
Minimal text space at the bottom third. No people, no faces.
Style: like a NASA Hubble photo but more cinematic and artistic.
Wide format 16:9 ratio.
"""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def generate_thumbnail(title: str, extra_style: str = "") -> Path:
    client = genai.Client(api_key=API_KEY)

    prompt = BASE_PROMPT
    if title:
        prompt += f"\nThe video is titled: '{title}'. Reflect the mood and theme of this title."
    if extra_style:
        prompt += f"\nExtra style notes: {extra_style}"

    print(f"Generating thumbnail for: '{title}'")
    print(f"Calling Gemini ({IMAGE_MODEL})...")

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = slugify(title) if title else datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = OUTPUT_DIR / f"thumbnail_{slug}.png"

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image"):
            output_path.write_bytes(part.inline_data.data)
            print(f"Saved: {output_path}")
            return output_path

    raise RuntimeError("No image in response")


def main():
    title = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Deep Space Nebula Drift"
    path = generate_thumbnail(title)
    print(f"\nThumbnail ready: {path}")
    print("Upload this to YouTube when publishing your video.")


if __name__ == "__main__":
    main()
