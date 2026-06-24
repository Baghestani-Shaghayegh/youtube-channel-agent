# Channel Strategy — Space Lofi / Cosmic Ambient

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
