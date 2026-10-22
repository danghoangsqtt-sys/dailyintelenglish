# PHASE-STATE — Phase 63: viral Shorts (news, text on blur)

- **Status:** implemented_verified_pending_owner_review 2026-10-22. Full pytest 1973 passed (10 new); 158 Vitest (6 new); tsc clean.
- **Real sandbox runs (cloud AI, Edge TTS, Remotion):** news Short from a sample article — script with the headline hook, facts in its own words and "Follow … for more English news"; plan of 6 segments, 9:16 only; rendered 1080×1920 in 107 s. The first plan was refused by the chart guard because the narration says numbers in words → the guard now reads worded numbers ("eight", "ten thousand", "twenty-five"). Blur Short — 5 text/quote segments, words popping with the voice over blurred scenes, rendered in 107 s. Layout fixes after reviewing the frames (ticker label, headline anchored above the captions, card above the headline).
- **Notes:** a segment with only an outside-AI picture prompt still needs a picture before approval (unchanged rule), so an automatic night run stops such a news Short at the visual plan for the owner. `tests/test_shorts.py` (the older clips feature) was overwritten by mistake during the work and restored from git; the new tests are `tests/test_viral_shorts.py`. StillFrame now picks the VOX / news / blur scene too (it always used the presenter scene).
- **Tasks:** 6/6.

| Task | Scope | Status |
|---|---|---|
| 63.1 | Data + contracts + link reader | implemented_verified |
| 63.2 | Prompts | implemented_verified |
| 63.3 | Renderer NewsScene / BlurScene | implemented_verified |
| 63.4 | Step 1 card + Step 5 | implemented_verified |
| 63.5 | Automation for Shorts series | implemented_verified |
| 63.6 | Verification + real Shorts | implemented_verified |
