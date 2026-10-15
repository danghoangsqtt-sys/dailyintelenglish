# YouTube motion and phrase-level character performance — 2026-10-15

The owner accepted the richer motion, requested it for YouTube 16:9, and selected upgrading dialogue movement with the existing picture packs.

## YouTube adaptation

- Scene drift, activity reveal/light sweep, speaker spotlight/meters, learning-card motion, caption/word animation, reading progress and side-gutter bokeh now run in both layouts.
- Landscape spotlights follow the actual 1280x720 character slots; particles scale with the canvas.
- YouTube captions use centered short pages (up to 16 words/96 characters, 32 px type), replacing the previous entire-paragraph overlay. The animated speaker label and reading progress are retained.
- The learning card has a centered, bounded width between the characters. Portrait keeps its existing safe column and caption density.

## Character upgrade using existing assets

Both real characters already have 29 pictures, including seven complete gesture pairs. The previous renderer could keep a greeting wave or talking pose throughout a 15–20 second line.

- Split long turns into phrases using the existing word timestamps and script punctuation, with a maximum phrase length/time.
- Select available gestures from the phrase: greeting/wave, thanks/heart, pointing/look, uncertain/open, question/thinking; generic explanation uses talk/open poses.
- Hold speaking bursts for roughly 0.8–2.3 seconds, with at least 0.9 seconds of neutral rest between them. Short leftover fragments do not cause a brief extra pose flash.
- The listener reacts briefly near phrase endings, then rests, rather than holding a listening gesture through the whole monologue.
- Add bounded whole-picture drift/lean: translation at most 1.5 px horizontally and 0.8 px vertically, rotation at most 0.3 degrees, no body resizing.
- Compensate imported picture head-offset metadata on the whole picture so expression/mouth/gesture swaps have less registration jitter.
- Mouth open/closed still follows the original audio intervals. A gesture is used only when its required picture pair exists. Short lines, missing word timing and minimal packs retain the previous fallback.
- Cue generation is deterministic and cached against immutable line/plan/character objects.
- Final real-episode cue audit: **64 speaking gesture bursts and 53 listener reactions** across both characters. Hoang's first 19.608-second turn contains five speaking bursts; its greeting wave lasts 1.212 seconds, with neutral rests instead of a held wave. Evidence: `final-cue-audit.json`.

This is a sprite performance upgrade. It does not create articulated in-between arm/hand frames or a rig. Dissimilar poses are not blended; the owner chose to use the existing packs.

## Verification

- **89 Vitest tests passed**, TypeScript clean. New regression tests cover semantic multi-gesture turns, neutral rests, listener reactions, original mouth intervals, missing-pair fallback, movement bounds, alignment/mirroring and landscape geometry.
- Actual `Episode` DOM scans: **757 sampled frames per layout**, including line entrance/exit samples. **Zero caption/card overflow failures** in either layout.
- Landscape: 59 caption pages measured; maximum caption height **142.188 px**, vocabulary **238 px**. Portrait: 88 pages, maximum **235.563 px** and **321 px** respectively.
- Inspected real dialogue/learning stills and produced a **24-second YouTube motion sample** covering several pose bursts and a speaker handoff: `data/tmp/youtube-dialogue-motion/preview-youtube.mp4`.
- Backend video service, render bridge and export/API regression suite: **49 passed** (one existing Starlette/httpx deprecation warning). Ruff and `git diff --check` passed.

## Render budget finding

The first full landscape attempt exceeded the historical 600-second deadline: Remotion completed 7,484 frames in 724 seconds, but the bridge rejected the timed-out job and retained the previous published output. Diagnostic: `data/video/357bc2b2-c1c7-4df6-9a4f-8c532634f165/video_remotion.render-202755dd.log`. A separate 300-frame motion benchmark took 29.445 seconds, consistent with the higher animated-render cost.

`DIE_REMOTION_RENDER_TIMEOUT_SECONDS` now configures a bounded, shared deadline across both attempts: default **3,600 seconds**, accepted range **60–7,200**. The initial 1,800-second setting was sufficient for landscape but the full portrait was only near frame 5,255/7,484 after 24 minutes, so its measured cost required a larger allowance. Retry count and atomic publication are unchanged. Regression tests check the configured budget, remaining time after a transient navigation failure, deadline exhaustion and validation bounds. This accommodates the measured render cost; it does not claim a speed improvement.

## Full outputs

Before regeneration, the SQLite DB and existing horizontal/vertical MP4/SRT files were snapshotted under `data/backups/youtube-dialogue-20261015-120722/`.

Landscape completed through the normal API in **768.178 seconds**: 1280x720 H.264/AAC, duration **249.514667 seconds**, **309,314,558 bytes**.

Portrait's Remotion child completed all **7,484 frames** and stitching in **2,058.309 seconds**. The source server had already passed its initial 1,800-second deadline to the subprocess, so that API returned a timeout even though the Windows child continued to completion. A task-local watcher preserved a second NTFS link to that exact completed staging file before bridge cleanup. No partial output was published.

The recovery required the completed bridge diagnostic, expected dimensions/codecs/duration/frame count, original AAC bitstream equality and a successful **full video decode**. Only then did the one-off script call the existing atomic publisher, vertical-path service and export sync. This is documented staging recovery, not a successful portrait HTTP response. `failure-portrait.json`, `preserved-link.json` and `result-portrait.json` retain that distinction.

| Output | Size | Duration | Publication |
|---|---|---|---|
| YouTube 16:9 | 1280x720; 309,314,558 bytes | 249.514667 s | Normal generation API |
| Portrait 9:16 | 1080x1920; 470,108,918 bytes | 249.514667 s | Validated completed staging recovery |

Both final files are H.264/AAC, with **0.048 s** A/V duration difference, identical original AAC bitstreams, unchanged SRT, and matching source/export hashes. The job is `complete` with no error; export reports `last_error: null`. Finished dialogue, learning-card, insert and portrait outro frames were inspected. Final evidence: `data/tmp/youtube-dialogue-motion/final-evidence.json`.

The measured render cost is a remaining practical limitation: about **13 minutes landscape / 34 minutes portrait** for this 4:09 episode on this machine. Raising the deadline accommodates that work; performance optimization has not been claimed. The source server was restarted after all children finished and now uses the 3,600-second default. Source app: http://127.0.0.1:8001.

Technical status: **implemented_verified_pending_pm**. No formal owner gate is self-accepted.

Evidence, candidate gesture audit and QA scripts: `data/tmp/youtube-dialogue-motion/`. No external model calls, dependency installation, EXE build/release, commit/push or self-acceptance of owner gates.
