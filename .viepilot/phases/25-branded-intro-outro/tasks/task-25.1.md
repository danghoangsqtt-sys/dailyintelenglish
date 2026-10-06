# Task 25.1: Spike: female voice samples + morph intro/outro preview (doc-first card)

## Objective

Before any product code, give the owner two things to decide on:

1. **Three female voice samples** (Edge TTS, the engine the app already uses). Each sample says the
   greeting + a wish and the farewell.
2. **A rendered preview MP4** of the proposed morph intro and outro, on a real project's title,
   topic and speakers.

## Paths

- `scripts/spike_brand_voice.py` (new; not shipped)
- `video-renderer/src/BrandSpike.tsx` (new; spike composition, registered under a separate id)
- `video-renderer/src/Root.tsx` (register the spike composition)
- `docs/operations/phase25-spike-brand.md` (new report)

## File-Level Plan

1. **`spike_brand_voice.py`:**
   - **Voices:** `en-US-AvaMultilingualNeural`, `en-US-JennyNeural`, `en-GB-SoniaNeural`.
   - **Texts:**
     - "Welcome to Daily Intel English Channel! Wishing you a wonderful time learning English today."
     - "Thanks for watching Daily Intel English! Keep practising, and see you in the next lesson."
   - **Output:** MP3s plus durations in `data/tmp/brand-spike/`.
2. **`BrandSpike.tsx`:** the intro (brand → morph to the episode → wish) and the outro (morph back
   → thanks + chips).
   - The animation uses `spring`/`interpolate`: shared elements change position, scale, radius and
     colour.
   - The fonts are the system sans for now; the bundled-font decision is part of the report.
   - Props: title, topic, CEFR level, speakers, the wish, the voice MP3.
3. **Render** the spike composition with Remotion for one real project (DB read-only) and the
   first voice. Then take stills at the key frames for the report.
4. **Report:**
   - the voice files and their lengths;
   - the stills and the MP4 path;
   - the font question (a bundled OFL font such as Montserrat or Poppins needs a download
     approval).

## Verification

- 3 voice files exist and play.
- The MP4 renders: intro + outro ≈ 15 s.
- Stills are checked by eye.
- **The owner decides:** the voice, the look (changes?) and the font.
