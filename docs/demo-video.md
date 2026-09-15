# Demo Video

`docs/demo/demo-video.webm` — a real screen recording of one full pipeline run against
the actual app (real Gemini calls, real Edge TTS synthesis, real ffmpeg audio/video
rendering — nothing mocked), captured with Playwright's built-in video recorder while
`scripts/record_demo_video.py` drove the UI. **223.9 seconds (~3:44)**, 1440×900, silent
(a screen capture of real UI state changes, no narration audio track) — shorter than
ROADMAP's "10 min" target figure because the actual pipeline is genuinely this fast, not
because footage was cut or sped up.

## What it shows, step by step

A single project ("Demo Episode", CEFR B1, `small_talk`, American accent, 2 speakers —
Alex and Maya, 5-minute duration target) moving through the entire production pipeline:

1. **Step 1 — Script Config**: filling the project form (name, topic, CEFR level,
   duration preset, genre chip, accent chip, both speaker names) and submitting.
2. **Step 2 — AI Script**: clicking "Generate Script" and the real Gemini-generated
   dialogue rendering as line cards.
3. **Step 3 — Learning Content**: clicking "Generate Learning Pack" and the
   vocabulary/idioms/grammar/quiz tabs populating.
4. **Step 4 — TTS Audio Studio**: clicking "Generate All" — this is the slowest step in
   the recording, since every line is synthesized sequentially via real Edge TTS calls
   before the final ffmpeg mix — ending with the audio player and download buttons
   appearing.
5. **Step 5 — Video Studio**: clicking "Generate video" and the rendered MP4 preview
   (background template + burned-in subtitles) appearing almost immediately.
6. **Step 6 — Thumbnail Generator**: clicking "Generate thumbnails" and the Gemini/Pillow
   variant grid populating.
7. **Step 7 — YouTube Package**: clicking "Generate YouTube Package" and the
   titles/description/chapters/tags sections populating.

## Real conditions during this recording

Not a clean-room run — real transient conditions surfaced and were absorbed correctly by
existing production code, which is itself useful evidence:
- Several Gemini calls hit real 429/503 responses and fell through
  `GEMINI_MODEL_FALLBACKS` (`gemini-3.8-flash` → `3.7` → `3.6`) before succeeding — the
  real fallback-chain mechanism working as designed, not a scripted scenario.
- OmniVoice's fallback path correctly and immediately deferred to Edge TTS for every
  line (`models/omnivoice` is empty on this machine — see `docs/tts-setup.md`).

## Reproducing this recording

```bash
venv\Scripts\python scripts\record_demo_video.py
```

Runs a real in-process `uvicorn` server (no manual server start needed) and writes
`docs/demo/demo-video.webm`. Total wall-clock time depends on live Gemini/Edge TTS
latency and quota state at run time — it was 226.1s end-to-end for the recording checked
into this repo.
