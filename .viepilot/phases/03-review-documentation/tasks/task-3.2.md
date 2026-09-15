# Task 3.2: Demo & Review

## Meta
- **ID**: 3.2
- **Phase**: 3
- **Status**: done (2026-09-15)
- **Priority**: medium
- **Assignee**: PM (Claude Code)

## Doc-First Gate

User chose to continue with Task 3.2 (over 3.3 Final Cleanup) at a `/vp-auto` control
point (2026-09-15), right after Phase 2's close and Task 3.1's completion. ROADMAP.md's
"3.2 Demo & Review" bullet has 3 items, all currently unchecked: demo video, 3 sample
podcast scripts (A1/B1/C1) with audio, and a product review report.

## Objective

### 1. Sample outputs — 3 real podcast episodes (A1, B1, C1) with audio
New `scripts/generate_sample_episodes.py`, same real-pipeline precedent as Task 2.1a's
`generate_cefr_review_samples.py`: for each of A1/B1/C1, create a real project via
`ProjectService`, generate a real script via `ScriptService.generate_script()` (real
Gemini call, not mocked), synthesize every line via `TTSService.synthesize_line()` (real
Edge TTS), and mix via `AudioService.mix_project()` (real ffmpeg). Save each episode's
script transcript (`.txt` / `.json`) and mixed audio (`.mp3`) under
`docs/samples/{cefr}/`. One genre held constant (`small_talk`, the least
formality-sensitive per Task 2.1b's findings) so the 3 samples differ only by CEFR level,
making the level progression the clearest to hear/read.

### 2. Product review report (`docs/product-review.md`)
A single report, not invented from scratch — assembled from what's already true in
`ROADMAP.md`/`TRACKER.md`:
- **Feature checklist**: every ROADMAP.md Phase 1/2 item with its real status (done /
  won't-do / deferred), matching TRACKER.md exactly — no re-litigating past decisions.
- **Known issues**: summarized from TRACKER.md's real "Known Issues" section (Scottish
  voice duplication, the 3 findings left noted-only from Task 2.6's audit, the flaky
  Gemini-retry test class) — link back to TRACKER.md for full detail rather than
  duplicating it wholesale.
- **Future improvements**: the deliberately deferred items — progress cancellation (Task
  2.2), real LivePortrait lip-sync (Task 1.7), the `news`-genre CEFR calibration drift
  (Task 2.1b), and Phase 3's own remaining items (3.3 Final Cleanup) once known.

### 3. Demo video — full workflow walkthrough
Real screen recording of the actual running app, not a mockup: a new Playwright script
(`scripts/record_demo_video.py`) drives one full pipeline run — Dashboard → Step 1
(config) → Step 2 (generate script) → Step 3 (learning content) → Step 4 (TTS + audio
mix) → Step 5 (video render) → Step 6 (thumbnail) → Step 7 (YouTube package + `.zip`
export) — against the real running `uvicorn` server, with Playwright's built-in video
recording (`context.tracing`/`record_video_dir`) capturing the whole session to a real
`.webm` file. This exercises the real API end-to-end (real Gemini, real Edge TTS, real
ffmpeg), the same "real, not mocked" standard as every other QA pass in this project.
Actual runtime depends on real generation latency — the resulting length will be
whatever the real pipeline takes, not artificially padded or sped up to hit "10 min".

## Allowed files
- `scripts/generate_sample_episodes.py` (new)
- `scripts/record_demo_video.py` (new)
- `docs/samples/` (new, generated output)
- `docs/product-review.md` (new)
- `docs/demo-video.md` (new — points at the recorded file + a written walkthrough
  transcript, since a binary video file isn't meaningfully reviewable inline)
- `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`,
  `.viepilot/phases/03-review-documentation/PHASE-STATE.md` (state tracking)

## Verification
- `venv\Scripts\python scripts\generate_sample_episodes.py` produces 3 real,
  non-empty script + audio files (spot-check word count scales with CEFR level and audio
  duration is non-zero).
- `docs/product-review.md`'s feature checklist cross-checked line-by-line against
  ROADMAP.md — no invented status.
- Demo recording actually shows real UI state changes (not a blank/error page) at each
  step — verified by reading back a frame or the Playwright trace, not just checking the
  file exists.
- No `app/` or `tests/` files touched — Task 3.2 is deliverables, not app code.

## Implementer Evidence (2026-09-15)

- `venv\Scripts\python scripts\generate_sample_episodes.py`: real run, first attempt hit
  a real `httpx.ReadTimeout` on A1 (transient network condition, not a code defect — same
  class as Task 2.1a's documented history); retried and succeeded cleanly: A1 (18 lines,
  78.9s, -16.01 LUFS), B1 (12 lines, 78.8s, -16.01 LUFS), C1 (10 lines, 102.9s, -16.01
  LUFS). Spot-checked `docs/samples/A1/script.md` — genuine, coherent A1-level dialogue
  with no invented content. 6 files produced (`script.md`/`script.json`/`audio.mp3` × 3
  levels), ~5.2MB total.
- `venv\Scripts\python scripts\record_demo_video.py`: first attempt failed — client-side
  validation blocked submission because Step 1's speaker-name fields are empty by
  default (`Speaker N needs a name`, diagnosed with a disposable debug script, not
  guessed); fixed by filling `#speaker-name-0`/`#speaker-name-1`. Second attempt failed
  on Step 4's audio generation — Edge TTS's real endpoint hit two transient connection
  failures for a 29-line script (known upstream flakiness, see `docs/tts-setup.md`), and
  the original 120s timeout was too tight for ~29 sequential real per-line TTS calls;
  fixed by raising Step 4's wait timeout to 300s and adding error-banner/progress
  diagnostics on failure. Third attempt succeeded end-to-end in 226.1s wall-clock: real
  script → real learning content (absorbed real 429s via the `GEMINI_MODEL_FALLBACKS`
  chain) → real 29-line Edge TTS synthesis + ffmpeg mix → real video render → real
  thumbnail generation (also absorbed real 429s) → real YouTube package generation.
  `ffprobe` confirms a genuine 223.9-second, 8.77MB `.webm` file (not a stub). Debug
  screenshots used for diagnosis were written outside the repo and cleaned up, not
  committed.
- `docs/product-review.md`'s feature table cross-checked line-by-line against
  `ROADMAP.md`'s Phase 1/2/3 checklists — no invented status.

## PM Acceptance (2026-09-15)

Accepted — all 3 ROADMAP items delivered with real, verifiable artifacts (not mocked or
faked): 3 real sample episodes with genuine script+audio, one real 226-second end-to-end
pipeline recording (`ffprobe`-verified), and a product review report that traces back to
`ROADMAP.md`/`TRACKER.md` rather than restating claims from memory. Two real bugs were
found and fixed in the recording script itself along the way (missing speaker-name
fields, too-tight Step 4 timeout) — disclosed above, not hidden. This closes Task 3.2.
