# Channel Strategy — Space Lofi / Cosmic Ambient

> **See also: [monetization_playbook.md](monetization_playbook.md)** (July 2026) — the
> data-driven path to 1K subs + 4K watch hours: 2025+ winner-cohort research, concept-first
> title formula, duration roadmap, KPIs, and revenue expectations.

## The Channel Concept
Long-form looped videos (1–4 hours) showing cosmic nebula and space visuals with space-themed ambient/lofi music on top. Think: beautiful space visuals + mood music, looped.

## Key Research Findings (May 2026)

### True Competitor Channels (Space ✓)
- **Relaxation Ambient Music** — 456K subs, 82 videos, 1.9/mo, avg 1.57M views/video, 11 yrs old. Proof the format has extreme longevity.
- **VIATMOS** — 57.5K subs in under 1 year, 45 videos, 4.3/mo, 86K recent avg views. THE blueprint to follow.
- **Space Relax Music Channel** — 63.6K subs, 257 videos, 15.8/mo, only 1.7K recent avg views. Warning: volume without quality kills performance.
- **Cosmic Nostalgia | Ambient Music by Oktawia** — 2.5K subs, 8.3/mo, 109 recent avg views.
- **Space Ambient Music** — 2.1K subs, 10 yrs old, stagnant.

### The #1 Insight
VIATMOS: 57K subs in 10 months, 45 videos, 4.3/mo = ~1 video/week. Top video 423K views. Algorithm is actively pushing this niche RIGHT NOW.

### Growth Playbook
- Post 1 video/week (4/mo), high quality
- Videos: 1–4 hours, looped cosmic nebula visuals + space ambient music
- Title formula: "[Visual scene] — Deep Space Ambient for [use case]"
- Example: "Flows of Universes — Deep Space Ambient & Meditative Cosmic Journey"
- Thumbnails: dark background, single glowing nebula, minimal text
- Month 3+: push to 4–8hr videos for sleep/study search traffic
- Add 1 live stream/premiere per month

### What NOT to Do
- Don't post 15+/mo — Space Relax Music Channel burned out, recent views collapsed
- Don't pick a generic channel name — space/cosmic/nebula in the name matters for search
- Don't quit early — views come before subscribers in this niche

## Your Channel
- **Channel Name:** Nebula Drift ✓ (decided May 2026)
- **Channel ID:** UCZJe8Esgl8BWJv_XpAC1FBA
- **Channel URL:** https://www.youtube.com/channel/UCZJe8Esgl8BWJv_XpAC1FBA
- **Created:** May 2026
- **Status:** Just launched — no videos yet

## Upload Schedule
- **Frequency:** 1 video per week (4/month)
- **Publish day:** Friday
- **publishAt time (UTC):** 20:00 UTC — 3pm EST / 12pm PST
- **Why:** Catches US East Coast end-of-day, West Coast noon; YouTube indexes 6–8 hrs before Friday night peak
- **Indexing buffer:** 2 hours (Nova schedules 2 hrs before target visibility time automatically)
- **Current video duration:** 1 hour (3600s) — starting point
- **Month 3+ duration:** push to 4–8 hours for sleep/study search traffic
- **Assembly script default:** `--duration 3600`
- **Title formula:** "[Visual scene] — Deep Space Ambient for [use case]"

## Visual Identity

### Color Palette
- Deep black backgrounds
- Purple (primary) — electric violet, magenta-purple
- Blue (secondary) — electric blue, ice blue, glowing cyan accents
- White/light blue for stars and core glows

### Style
- Swirling vortex / spiral nebula shapes (not flat fields)
- Glowing luminous center with cloud formations spiraling outward
- Cinematic, high contrast, dramatic lighting
- No text or logos in the raw images

### Channel Art (set June 2026)
- **Profile picture**: swirling purple/blue nebula vortex, glowing blue starfield core — circle crops perfectly to the center
- **Banner**: wide deep space scene, purple nebula on left, blue nebula sweeping right, small spiral galaxy bottom right, no text overlay in the image itself

### Thumbnail Formula
- Same purple/blue palette as channel art
- Single dominant nebula shape, dark background
- Minimal text — title only, clean white font, bottom or center
- No em dash in text (reads as AI-generated)

### Image Generation Prompts (ChatGPT/DALL-E)
- Profile: "glowing cosmic nebula vortex, deep blue and purple swirling clouds, starfield in the center, dark black background, cinematic space art, square format"
- Banner: "wide cinematic deep space scene, swirling nebula clouds in purple and blue, dense starfield, dark background, no text, ultra wide panoramic format"

### Video Generation Prompts (Runway / Seedance 2.0)
**Setup that works:** single start image OR text-to-video (NOT same start+end keyframe —
that causes a "breathing" zoom). The assembly script handles the seamless loop via
crossfade, so don't try to make Runway loop it. 16:9, 1080p, audio OFF. Generate 2-3
times and pick the best (each run is random). Run output through
`execution/analyze_video.py --motion` to check it before assembly.

**Calm starfield drift (no clouds, no center band) — the look we landed on (Jun 2026):**
> Gentle continuous forward drift through deep space at a calm relaxed cruising pace, the camera glides smoothly forward through an open star field, countless distant stars slowly passing by, clear dark empty space with a faint even blue and purple tint spread softly across the whole frame, stars evenly scattered everywhere, no horizontal line, no horizon, no glowing band or light streak across the middle, no nebula clouds, no gas clouds, no fog, stars hold steady and sharp, peaceful and meditative, dark black background, smooth steady motion, not rushed, no warp speed, no streaking stars, no zooming, no pulsing, no rotation, no people

**Kling AI (kling.ai) — use POSITIVE phrasing, it rejects negative-heavy prompts:**
Kling's content filter throws "content you uploaded violates community guidelines" on prompts
with a long stack of negatives (especially "no people"). Use this positive-phrased version
instead (same clean starfield look, no filter trip):
> Gentle continuous forward drift through deep space at a calm relaxed cruising pace, the camera glides smoothly forward through a clean open star field, countless distant stars as sharp points of light evenly scattered across the whole frame, clear dark empty space with a faint soft blue and purple tint, peaceful and meditative, dark black background, smooth slow steady motion

(positives replace negatives: "clean open star field / evenly scattered" = no clouds/band;
"sharp points of light / smooth slow motion" = no warp/streaking; drop "no people" entirely.)
Settings on Kling: Video 3.0, text-to-video (no start/end frame), 720p, 16:9.

### THE #1 LOOP RULE — generate LOW-MOTION clips
A clip can only loop cleanly if its end frame ≈ its start frame. Clips with continuous
zoom/rotation/forward-dolly NEVER loop forward-only — every crossfade length just trades a
ghosty dissolve (long fade) for a hard pop (short fade). We burned a whole session on the
video_04 galaxy because it zoomed+rotated non-stop. Don't repeat that — generate near-static
clips from the start.

**Loop-friendly (near-static) prompt — use this as the default:**
> Almost completely still spiral galaxy in deep space, the galaxy stays fixed and centered in the frame, extremely subtle barely-perceptible drift, gentle slow shimmer of distant stars, no camera movement, no zoom, no rotation, no scaling, no pushing forward, glowing purple and blue galactic arms, thousands of tiny sharp stars, deep black background, calm static and serene, cinematic photorealistic

(swap "spiral galaxy" for "star field" / "nebula" as needed; keep the "no camera movement,
no zoom, no rotation" core.)

**Keyframe trick for loops:** if the tool supports start+end frames, use the SAME image for
BOTH. That forces the clip to return to its start = guaranteed loop. The "breathing zoom" we
hit before only happened because the MOTION was big; with a near-static prompt the motion is
tiny, so same-start-end gives a clean loop with no breathing. (Only works if you have a still
image; pure text-to-video can't set frames.)

**Assembly loop tools (execution/assemble_video.py):**
- `--loop-mode boomerang` = forward+reverse, mathematically seamless (no crossfade artifact)
  but the clip plays backward in the 2nd half. VERDICT (2026-07-02): user watched the
  boomerang final_04 and rejected it — the forward/backward motion IS noticeable, even on
  slow galaxy footage. Do NOT use boomerang; always loop forward-only with crossfade mode.
  (Checked video_04 crossfade at 1.5s fade: blend zone shows no visible ghosting, just a
  brief softness — acceptable. The "ghosty dissolve vs hard pop" warning above was
  overstated for this clip.)
- `--fade <sec>` tunes the video crossfade; `--audio-crossfade <sec>` tunes the audio loop
  (sweep per track — was 22s for audio_03, 20s for audio_04).

**Other prompt-tuning lessons:**
- Do NOT put "4K quality" in prompts (user preference).
- "volumetric nebula clouds / cosmic gas" → adds clouds (remove if you want a clean starfield)
- "glow far in the distance" → renders as an unwanted horizontal band/horizon line; use
  "faint even tint spread across the whole frame" instead
- "imperceptible / glacial / barely creeps" → TOO slow for a *drift*; but PERFECT for a loop clip
- Always include "no warp speed, no streaking stars" — Seedance/Kling default to a warp zoom otherwise
- Energetic warp-speed clips → title for Focus/Study; calm drift clips → title for Sleep/Relaxation
- Hailuo/MiniMax watermark = bottom-right ("MINIMAX | Hailuo AI"); assembly's bottom-70px crop removes it

## Competitor Case Studies (June 2026)

### NebulaDriftHQ (@NebulaDriftHQ) — FAILED, what NOT to do
1,340 subs, 6,341 total views, 55 videos in 3.6 months, then died (last upload Dec 2025).
Mistakes: (1) **over-posted ~14 videos/month** (often 2/day) → burnout; (2) **death spiral** —
when early videos got ~100 views they panic-posted MORE low-effort videos, and views
collapsed to 1-5 each; (3) **stop-start** (daily 2 weeks, then 2.5 months silent, then quit);
(4) all 1-hour, no long-form; (5) emoji-stuffed titles, format changed midway, no consistent
brand; (6) **quit at month 3.6** when patience was the only thing left.

### ViewEscape (@ViewEscape) — WINNING, the blueprint (long-term)
217K subs, 47M total views, 145 videos over ~23 months. Median ~179K views/video, some hit
1-2M. Formula: (1) **10-HOUR videos, every one** = the watch-time engine; (2) **slow pace,
~2.2 uploads/month** (quality > quantity, opposite of the failed channel); (3) **scene-based
concept** — each video is a *place to escape to* ("Cozy Balcony over the Radiant City",
"Private Interstellar Suite in Deep Space"), not abstract loops; (4) **layered ambience**
(rain, thunder, water, hum), not just music; (5) **consistent for ~2 years, never quit**.

### Neural Beats Lab (@NeuralBeatsSpace) — new channel, Shorts-trap cautionary tale
Created Apr 2026; 7 subs, 3,325 views, 83 videos in ~2 months. Posts a 1-hour video AND a
Short for every cosmic object, daily (~40/month — extreme over-posting).
- **Proves the no-Shorts decision:** their Shorts get 167-606 views but the channel has only
  7 SUBS and the 1-hour videos (the real product) die at 1-9 views. Shorts traffic doesn't
  convert and doesn't watch long-form. Vanity views, no real audience.
- Same over-posting burnout pattern as NebulaDriftHQ.
- **ONE idea worth borrowing:** their title hook = real astronomical object + 432Hz, e.g.
  "M82 | 432Hz Deep Space Ambient - Cigar Galaxy", "NGC-7023 - Iris Nebula". Real galaxy/
  nebula names are specific and searchable; 432Hz is a searched sleep/meditation term; gives an
  endless themed series with built-in variety. Could adopt for some of our titles without
  changing the core format.

### Our decision (June 2026) given this data
- **Keep current concept** (abstract nebula/starfield ambient) for now. A scene-based "escape
  destination" channel like ViewEscape is a possible SEPARATE future channel, not a pivot.
- **Do NOT jump to 10-hour videos yet.** Our avg view duration is ~11 min; a 10hr video would
  show ~1.8% completion and the algorithm would read that as instant bailing. Long videos only
  pay off once we have an audience that leaves them on overnight. Grow video length GRADUALLY
  (1hr → 2hr → 3hr) as average watch-time rises, not all at once.
- **Core lessons we DO adopt from both:** never panic-post, keep titles clean/consistent (no
  emoji spam), stay consistent, and don't quit early.

## Distribution Decision (June 2026)
**Long-form YouTube only.** No Shorts, no Instagram. Rationale: this niche grows on
long watch-time (looped sleep/study sessions) via search/suggested, not viral clips.
Shorts subscribers rarely watch long-form and can dilute the audience signal. All
energy goes into a consistent library of long (3hr+) videos. Revisit Shorts only as
a measured teaser experiment after 5-8 long videos are up.

## Audio Production (Suno) — the sound we want

The target sound is a **smooth, glassy, beatless ambient drone** like `audio_01.mp3`
(spikiness ~0.60, percussive ~1%). NOT the spiky/lofi version (Infinite Drift had
pulse 0.184, percussive 6.9% — too much movement). Smooth = sustained/static, not
"evolving" or "textured".

### Suno recipe (makes the sound we like)
- **Mode:** Advanced, Lyrics = Instrumental
- **Styles box:**
  > sustained ambient drone, pure smooth continuous pad, deep space soundscape, static unchanging tone, warm soft pads, gentle and steady, sleep music, formless, timeless, seamless loop, no drums, no beat, no melody
- **Exclude styles:** leave EMPTY (a heavy exclude list over-sterilizes it and kills the warmth)
- **Weirdness:** 0%   **Style Influence:** ~20%
- Avoid the words "ethereal, slow evolving, soft noise, airy textures" — they add the grain/spikiness we don't want.
- To get variations of the same vibe: keep the prompt, just hit Create 3-4x.

### Known Suno quirk
Suno tends to "develop" the track and sneak in a beat partway (the Jun 2026 track
grew a beat at ~2:20). Fixes: (a) trim to the clean section before the beat, or
(b) add "static and unchanging from start to finish, no development, no build, no
progression" to the prompt.

## Audio Post-Processing (automated in execution/assemble_video.py)

ALWAYS polish audio before/at assembly — these are now built into the assembly script:
1. **Trim out any beat** — find the beat-free window (use the segment analyzer); also
   pick the most self-similar loop window (best spectral match start↔end) for a clean loop.
2. **Seamless crossfade loop** — `make_seamless_audio_loop()` with a **15s** crossfade
   (sweet spot for ambient: seam change ~0.36x the music's natural movement = inaudible).
3. **3s fade-in at the start** so the audio eases in instead of jumping to full volume.
Tools: `execution/analyze_video.py` (video), and the audio analysis scripts for
beat-location / loop-window / seam measurement.

## Search Term Research (June 2026)

### Key finding: title for the SEARCH, not the channel name
Searching "nebula drift" / "nebula drift ambient" shows that videos built around the
phrase "Nebula Drift" almost all flop — even big channels. Examples:
- Sheyda Official (117K subs) → 25 views on its "Nebula Drift" video
- Space Relax Music Channel (63.9K subs) → 0 views on "Crimson Nebula Drift"
- Highest view count for ANY "nebula drift ambient" video: ~547 views
Lesson: "Nebula Drift" is a fine CHANNEL name but a dead VIDEO-TITLE / search term.
Never put "Nebula Drift" in video titles — use it only for channel branding.

### What actually wins (searched high-intent terms)
Searched: "deep space ambient sleep", "space ambient music study",
"1 hour space music focus", "cosmic ambient relaxation", "deep space music for sleep".
The niche is enormous — sleep/study ambient is one of YouTube's biggest categories.

**THE BLUEPRINT — Celestial Ambience (only 31.7K subs):**
- Video "Starfield - Ambient Space Music for Sleep/Study/Relaxing 10 Hours" = 22.4M views
- That one video = 78% of the channel's 28.8M total views (a single breakout hit, not
  consistent — but proves a small channel CAN hit 22M in this exact niche)
- Channel: UCstsO2Wf4sCWjauPZs35tlQ

### Actionable takeaways
1. **Go long.** Winners run 3–12 hours, not 1 hour. People loop them all night for
   sleep = huge watch-time. Since our video is a looped clip + audio, longer costs
   nothing extra to produce. Push to 3–10 hours sooner than "Month 3+".
2. **Stack use cases in the title.** Winners cram Sleep/Study/Relaxing into one title
   to catch every search intent at once — don't pick just "Sleep".
3. **Winning title formula:** `[Cosmic noun] - Deep Space Ambient Music for Sleep, Study & Relaxation [X Hours]`
4. Study Celestial Ambience's thumbnails as the model.

## Research Data Location
- Google Sheet (master): https://docs.google.com/spreadsheets/d/1OWJ2Z0BXNby4mxcxZojVQ0sKFshmxg5jhGimCwQWXZo
- Local CSV: .tmp/channel_research_master.csv

## Monitoring Targets (check weekly)
- VIATMOS: UCi0C7tOvioiAFWozysY7NyQ
- Relaxation Ambient Music: UCkFeoNSqYTa7trn75WM9tsg
- Space Relax Music Channel: UCSFB7Xy5Fa1pVVKP_CajIrw
- Cosmic Nostalgia: UCWdmm6WzJsjQ-_3a4VU8tsQ
- Celestial Ambience: UCstsO2Wf4sCWjauPZs35tlQ  (BLUEPRINT — 31.7K subs, 22.4M-view breakout)
