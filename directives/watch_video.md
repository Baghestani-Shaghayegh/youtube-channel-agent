# Watch Video Directive

## Purpose
Let Nova "watch" a local video clip by analyzing its frames with Claude's vision API, so
Nova can (a) describe visual content before writing YouTube titles/metadata, and (b) critique
AI-generated clips (motion, parallax, loop quality) before regenerating them with a better prompt.

This removes the need to ask the user "what does the clip show?" — Nova just looks.

## Tool
`execution/analyze_video.py` — extracts evenly-spaced frames with ffmpeg, sends them to
Claude (`claude-opus-4-8`), prints the result.

## Modes

### Describe (default) — before assembly / metadata
```
python execution/analyze_video.py ".tmp/raw/video_01.mp4"
```
Returns JSON: `scene_type`, `dominant_colors`, `mood`, `visual_details`, `suggested_titles`.
Use `scene_type` + colors to write the title. Note: titles follow the channel formula,
never contain an em dash, and never contain the words "Nebula Drift" (that phrase has no
search demand — see channel_strategy.md).

### Motion critique — for AI-generated clips (Runway/Seedance/Kling)
```
python execution/analyze_video.py "clip.mp4" --motion
```
Reports whether the camera truly moves forward vs zoom/pulse/rotate, whether there's
parallax/depth, whether clouds morph unnaturally, and how well the clip loops — plus
concrete prompt fixes. Use this to iterate on generation prompts.

Optional: `--frames N` to sample more frames (default 8) for longer or fast-moving clips.

## When to use
- User drops a new clip in `.tmp/raw/` and wants it prepared → describe mode first
- User generated a clip in Runway/Seedance and it "feels off" → motion mode
- Before running `assemble_video.py` if the visual content is unknown

## Dependencies
- ffmpeg (`brew install ffmpeg` / `sudo apt install -y ffmpeg`)
- `pip install anthropic` (VPS: `pip3 install anthropic --break-system-packages`)
- `ANTHROPIC_API_KEY` in `.env`

## Notes / learnings
- Frames are downscaled to 640x360 to keep vision token cost low; quality is plenty for
  scene/motion judgment.
- Common AI-clip failure found in practice: same start+end keyframe in Runway produces a
  "breathing zoom" (zoom in then pull back) that reads as fake. Fix: single start keyframe +
  forward-travel prompt, and let `assemble_video.py`'s crossfade handle the seamless loop.
