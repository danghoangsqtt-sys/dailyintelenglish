# Phase 19 Spike — Remotion scaffold + render measurement (Task 19.1)

- **Task:** 19.1 (Coder). Design record: `.viepilot/phases/19-remotion/tasks/task-19.1.md`
  (D19.1-a..f, PM-approved 2026-09-28, sessions "Phân tích mã nguồn dự án" / a01f96).
- **Run date:** 2026-09-28. **Code HEAD at spike:** Phase 18 close-out (`v1.1.0-beta`,
  `die-vp-p18-complete`) plus this task's own doc-first + scaffold commits.
- **Scope:** measurement only. `app/services/video_service.py` and the ffmpeg fallback path
  are untouched (D19.1-f) — confirmed below (§5).
- **Real-episode caveat found during this task (flagging, not hiding):** the phase's own
  preflight note (`PHASE-STATE.md`) said "Owner has one real B1 8-min episode already in
  `data/app.db` with completed audio." A read-only query of the real DB found this is not
  currently true: **no project has `duration_minutes = 8` with a completed audio mix.** Only
  one project anywhere in the DB has a completed `audio_jobs` row at all —
  `b330d37f-a212-4cf7-a779-7a109098bd6c` ("Demo Episode", B1, planned 5 min, measured 2:56).
  That is the episode this spike renders and measures. §6/§7 extrapolate to 8 minutes from
  this real measurement rather than waiting on a new real 8-minute recording.

## 1. Environment

| Item | Value |
|---|---|
| OS | Windows 11 Pro, build 10.0.26200, 64-bit |
| CPU | Intel Core i7-12700, 12 cores / 20 logical processors |
| RAM | 31.7 GB |
| GPU | NVIDIA GeForce RTX 3060 (owner-specified 12 GB VRAM; Windows WMI under-reports this card as 4 GB — a known 32-bit `AdapterRAM` overflow bug on cards >4 GB, not a real hardware limit) |
| Node.js | v24.20.0 (current LTS line since Oct 2025; already installed, not added by this task) |
| npm | 11.19.0 |
| remotion / @remotion/cli / @remotion/renderer | 4.0.529 (resolved, `video-renderer/package-lock.json`) |
| react / react-dom | 19.3.0 |
| zod | 4.5.4 (Remotion's own recommended typed-props pattern, D19.1-b/c) |
| typescript | 5.9.3 (pinned below npm's `latest` tag, which is a TS 7 pre-GA line as of today — deliberately avoided for a measurement-only spike) |
| Headless Chromium | Chrome Headless Shell 149.0.7790.0 (auto-downloaded by Remotion on first render; cached at `video-renderer/node_modules/.remotion/`) |

## 2. Install footprint

| Item | Size |
|---|---|
| `video-renderer/node_modules/` (total, incl. Chrome cache) | 692,062,366 bytes (~660 MB) |
| … of which `node_modules/.remotion/` (Chrome Headless Shell) | ~270 MB |
| … of which JS/TS packages (remotion, @remotion/cli, @remotion/renderer, react, react-dom, zod, typescript, @types/*) | ~390 MB |
| Today's packaged app (`dist/DailyIntelEnglishStudio/`, pre-existing PyInstaller build) | 169 MB |
| Total added disk vs. pre-19.1 baseline | +692 MB (workspace only — see §6 for a packaged-app estimate, which differs) |

## 3. Real episode

| Field | Value |
|---|---|
| Project id | `b330d37f-a212-4cf7-a779-7a109098bd6c` |
| Name / genre | "Demo Episode", `small_talk`, 2 speakers |
| CEFR level | B1 |
| Planned duration | 5.0 min (`projects.duration_minutes`) |
| Script line count | 30 |
| Measured audio duration (ffprobe) | 176.02 s (2 min 56 s) — shorter than planned, and shorter than the phase's assumed 8-min case (see caveat above) |
| Audio file | `data/audio/b330d37f.../mix.mp3`, 3,522,284 bytes (~3.36 MB) |

## 4. Render measurement

Three consecutive real renders of the same episode (same subprocess contract, D19.1-d):

| Run | Wall time (`time.monotonic()`, includes bundling) |
|---|---|
| 1 | 61.268 s |
| 2 | 61.249 s |
| 3 (process-tree RAM-monitored run) | 60.432 s |

- **Wall time is stable, ~61 s end-to-end** (bundle + Chromium launch + frame render + encode)
  for a 2:56 / 30-line episode at 1280×720@30fps (5,281 frames).
- Remotion's own CLI output did not print a separate final "rendered in Xs" summary line
  distinct from the progress bars in this non-interactive/piped invocation, so no second,
  Remotion-self-reported number is available to compare against — the `time.monotonic()`
  figure above is the one real number this task has, and it is also the more operationally
  relevant one (it is what a caller of this subprocess actually waits on).
- Output: `data/tmp/phase19_spike/b330d37f....mp4`, 7,984,076 bytes (~7.6 MB), H.264/AAC,
  1280×720, 30 fps (all confirmed by `ffprobe`, raw JSON kept alongside this report's
  supporting evidence).
- **Peak RAM** (process-tree-scoped: python → npx → node → esbuild workers → Chrome Headless
  Shell processes spawned during the render; a shared dev machine runs several unrelated
  long-lived `node.exe` processes for other sessions, so peak was measured by filtering to
  processes whose start time was at/after this render's own start, not a system-wide
  `Get-Process node` sum): **~1.73 GB peak, across 17 processes** (Chromium's
  multi-process model — GPU/renderer/utility processes — accounts for most of the process
  count).

## 5. Correctness spot checks

- **Line 1 start** (`start_sec: 0.0`, "Alex: Hey Maya, are you an early bird or a night owl?"):
  frame extracted at t=1s shows exactly this text in the subtitle band.
- **Line 30 (last line) end** (`end_sec: 176.02`, "Maya: I will! Wish me luck!"): frame
  extracted at t=175s shows exactly this text.
- **Mid-episode spot check** (t=88s): shows "Maya: I know, right? But it is so tempting to
  sleep for five more minutes." — the correct active line for that timestamp per
  `audio_jobs.timestamps_json`.
- **A/V duration match:** audio 176.02 s vs. rendered video stream 176.033 s / audio stream
  176.064 s — a 0.01–0.04 s gap, well inside the existing media gate's ±0.5 s tolerance.
- **Resolution match:** rendered output is exactly 1280×720, matching
  `VIDEO_WIDTH_STANDARD`/`VIDEO_HEIGHT_STANDARD` and all three ffmpeg background PNGs —
  **no upscale**, per PM's D19.1-c confirmation.
- **Fallback path unaffected:** `app/services/video_service.py` was not modified by this
  task. `tests/test_video_studio_browser.py` — 10/10 passed, unchanged, after the
  `video-renderer/` workspace landed. Full suite: **1175/1175 passed**, `ruff check .` clean
  (same baseline as Phase 18 close-out). `tsc --noEmit` clean on `video-renderer/src/`.

## 6. Packaging estimate

Numbers, not adjectives, per the task card:

- Today's packaged app (`dist/DailyIntelEnglishStudio/`): **169 MB**.
- `video-renderer/node_modules/` as measured: **~660 MB**, of which **~270 MB** is the Chrome
  Headless Shell binary (unavoidable — it *is* the render engine, not a trimmable dependency)
  and **~390 MB** is JS/TS packages, some of which (`typescript`, `@types/*`, ~85 MB combined)
  are dev-only and would not ship in a packaged build.
- **Rough packaged-app estimate:** production-only Node deps (~305 MB: remotion,
  @remotion/cli, @remotion/renderer, react, react-dom, zod) + Chrome Headless Shell (~270 MB)
  ≈ **+575 MB**, even assuming the packaged app can rely on the owner's already-installed
  system Node.js (v24.20.0) rather than bundling a portable Node runtime. If a portable Node
  runtime must be bundled instead (no assumption made yet about the owner's target machines
  in general), add roughly **+100 MB** more.
- **Net effect: today's 169 MB app would grow to roughly 740 MB–840 MB** — a 4–5× increase.
  This matches ENH-013's own stated risk ("roughly 150–300 MB" was an early guess; the
  measured number is higher, mainly because of Chrome Headless Shell's real size on Windows).

## 7. Decision proposal (Coder proposal — PM decides)

**PASS**, with two explicit conditions carried into 19.2's task card:

1. **Render time is not the blocker ENH-013 worried about.** 61 s for a 2:56 episode
   extrapolates linearly (Remotion renders frame-by-frame) to roughly **166 s (~2.8 min) for
   a full 8-minute B1 episode** — far under the "several to 10+ min" feared in the phase
   spec. This is an extrapolation, not a direct 8-minute measurement, because no real
   8-minute episode with completed audio currently exists in the DB (see the caveat at the
   top of this report). Recommend re-confirming with one real 8-minute render opportunistically
   once the owner generates one, but **not** blocking 19.2 on it — the scaling assumption is
   low-risk (frame-driven render, no reason to expect a non-linear cliff at 8 minutes vs. 3).
2. **Packaging weight is the real, confirmed risk**, now with real numbers (§6: +575–840 MB).
   This was already a known risk in ENH-013's constraints; it is not a new blocker, but Task
   19.7 (wiring + packaging) should treat the Chrome Headless Shell's ~270 MB as a hard floor
   that has to be accepted, downloaded on first use rather than bundled, or the Remotion path
   dropped — not something 19.7 can "optimize away."

No SCOPE-CUT or STOP indicators found: composition mechanics, subprocess contract, and the
fallback invariant (I36) all worked exactly as designed on the first real render.
