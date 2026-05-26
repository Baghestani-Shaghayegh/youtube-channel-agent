# Video Assembly Directive

## Purpose
Automate the production of upload-ready YouTube videos for Nebula Drift by combining raw video clips and music tracks using ffmpeg. Nova decides which files to use and in what order, then calls the execution script.

## Inputs

### Source folders (ask user if not specified)
- **Video clips**: raw space visual clips (`.mp4`, `.mov`, `.mkv`)
- **Audio tracks**: music files (`.mp3`, `.wav`, `.flac`, `.aac`)
- These can be anywhere on the user's machine. Common defaults:
  - `~/Movies/nebula-drift-clips/`
  - `~/Music/nebula-drift-tracks/`
  - Or user drops them in `.tmp/raw/`

### Parameters
- **Target duration**: default 7200 seconds (2 hours). Can be 3600 (1hr) or 10800 (3hr).
- **Video title**: used for output filename slug and YouTube metadata

## Nova's Decision Logic (which file to use first)

When the user has multiple clips/tracks available, Nova picks based on:

1. **Variety first**: don't repeat the same clip or track back-to-back across uploads
2. **Best visual → best track pairing**: match moods (e.g. bright nebula clip + upbeat ambient, dark void clip + slower drone)
3. **Check memory/upload_history.md** (if it exists) to see what was uploaded last — pick something different
4. **When in doubt**: ask the user which clip and which track to use

Nova should always confirm the selection with the user before running the script:
> "I'll use `nebula_purple_v2.mp4` + `cosmic_drift_track1.mp3` for a 2-hour video. Title: 'Purple Nebula Drift — 2 Hours Deep Space Ambient'. Shall I assemble it?"

## Execution Script

```
python execution/assemble_video.py \
  --video ".tmp/raw/nebula_purple_v2.mp4" \
  --audio ".tmp/raw/cosmic_drift_track1.mp3" \
  --duration 7200 \
  --title "Purple Nebula Drift — 2 Hours Deep Space Ambient"
```

Script output: `.tmp/final_<slug>.mp4` — ready to upload to YouTube.

## What the Script Does (ffmpeg pipeline)

1. **Loop video** to target duration using `-stream_loop -1` (no re-encoding, fast)
2. **Loop audio** to target duration using `-stream_loop -1`
3. **Merge** looped video + looped audio into one output file
4. **Trim** to exact duration
5. Output: H.264 video + AAC audio, 1920x1080 or 3840x2160 depending on source

## Output

- File: `.tmp/final_<slug>.mp4`
- Format: MP4, H.264 + AAC (YouTube-compatible)
- Size estimate: ~1-3 GB for 2 hours at 1080p

After assembly, Nova should:
1. Confirm file was created and print file size
2. Suggest thumbnail to generate (run `generate_thumbnail.py` with same title)
3. Remind user to upload manually or ask if they want auto-upload

## Dependencies

- **ffmpeg** must be installed
  - Mac: `brew install ffmpeg`
  - VPS (Ubuntu): `sudo apt install -y ffmpeg`
- Check: `ffmpeg -version`

## Upload History Tracking

After each successful assembly, append to `memory/upload_history.md`:
```
- Date: YYYY-MM-DD
  Video clip: filename.mp4
  Audio track: filename.mp3
  Title: "..."
  Duration: 2hr
  Output: .tmp/final_slug.mp4
  Uploaded: [yes/no]
```

This lets Nova avoid repeating the same combo and track what's been done.

## Edge Cases

- **No ffmpeg**: script prints install instructions and exits with clear error
- **Video shorter than audio or vice versa**: both are independently looped, so length mismatch doesn't matter
- **Very large source files**: `-c copy` (stream copy) means no re-encoding — stays fast
- **Incompatible audio format**: script converts to AAC automatically using `-c:a aac`
- **Missing file**: script exits immediately with a clear "file not found" message

## Quality Checklist (Nova reviews before telling user it's done)

- [ ] Output file exists in `.tmp/`
- [ ] File size is reasonable (>500MB for 2hr video)
- [ ] Duration matches target (ffprobe check)
- [ ] Nova has logged it in memory/upload_history.md
- [ ] Thumbnail generated or flagged for generation
