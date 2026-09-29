# Task 19.7 — `VideoService` wire-up + toggle + kill switch + packaging + `check_dependencies`

- **Status:** not started (doc-first card, awaiting Coder pickup after 19.6)
- **Owner:** Coder
- **Priority:** P0 (biggest task in Phase 19; first task in the phase that touches
  `app/services/video_service.py`; ships Remotion behind an opt-in toggle for real
  end-user use)
- **Dependency:** Task 19.6 accepted (`e3d92d6`); Remotion composition is feature-
  complete (karaoke + speaker chip + vocab card + intro/outro + chapter bar + still)
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.7";
  **Amendment A** (2026-09-28) — Chrome Headless Shell ~270 MB is a hard floor, plan for
  download-on-first-use / drop-Remotion / accept-bundle, NOT optimize away
- **Phase 19 invariants that constrain this task (from the plan §2):**
  - **I36 (opt-in and reversible):** request-time flag, settings toggle, and
    `DIE_VIDEO_RENDERER=remotion|ffmpeg` kill switch all resolve to `ffmpeg` when
    ambiguous. Remotion failure never fails a video — degrades to ffmpeg. Fallback rate
    reported.
  - **I37 (local-only):** no episode data leaves the machine from `video-renderer/`.
  - **I40 (thresholds unchanged):** media gate (duration ±0.5s, A/V drift, codec) still
    passes on Remotion output.

## Goal

Wire the completed Remotion composition into `VideoService.generate_video` behind a
strict opt-in path so a real user (owner) can render an episode through Remotion via the
app's own Step 5 UI (or an env-var kill switch). The default stays `ffmpeg` — a fresh
install with `DIE_VIDEO_RENDERER` unset renders exactly like today, byte-for-byte, no
Node/Chromium ever launched.

**Packaging decision lands here** (Amendment A). The Chrome Headless Shell binary is
~270 MB, unavoidable. Coder proposes one of three shapes in design (D19.7-h):
1. Bundle in packaged `.exe` (169 MB → 740-840 MB)
2. Download-on-first-use post-install (Remotion's own CLI supports this)
3. Drop packaging entirely — Remotion available only in dev mode

## Allowed files

- **Modify** `app/services/video_service.py` — extend `generate_video()` to accept
  `renderer: Literal["ffmpeg", "remotion"] = "ffmpeg"`, dispatch to existing ffmpeg
  path or new `_render_via_remotion` subprocess call. **Default must remain `"ffmpeg"`
  when the param is not passed** (D19.7-a). New `_render_via_remotion` invokes
  `scripts/run_remotion_spike.py`-style subprocess (or an extracted equivalent). If it
  fails (any exception, non-zero exit, timeout), fall back to ffmpeg path and record
  `fallback_used=True` in the result (I36-a).
- **Modify** `app/core/config.py` — new `VIDEO_RENDERER: Literal["ffmpeg", "remotion"]
  = "ffmpeg"` setting under `DIE_VIDEO_RENDERER` env var. Also new
  `REMOTION_ALLOW_DOWNLOAD: bool = True` for D19.7-h option 2.
- **Modify** `app/models/video.py` (or wherever the video-generate request model lives) —
  optional `renderer` field in `VideoGenerateRequest`; not required, defaults to setting.
- **Modify** `app/api/video.py` — pass `renderer` through to `VideoService.generate_video`.
- **Modify** `frontend/pages/step5_video.html` + `frontend/static/js/step5_video.js` —
  small "Renderer" pill/toggle above the existing Generate button. Options: "Standard
  (ffmpeg)" and "Enhanced (Remotion, opt-in)". Default is Standard. Toggle state passed
  through to the generate call. Disabled + tooltip "Remotion not available on this
  install" when `check_dependencies` reports Node/Chromium missing.
- **Modify** `scripts/check_dependencies.py` — new checks: Node.js version (≥ 20 per
  Remotion 4.0.x requirements), `video-renderer/node_modules/` present + freshly-installed
  (compare `package-lock.json` mtime), Chrome Headless Shell available (either bundled at
  known path OR downloadable if `REMOTION_ALLOW_DOWNLOAD=true`). Missing pieces are
  **guidance not crashes** (same discipline as Ollama-missing pre-Phase 18).
- **New** `app/services/video_renderer_remotion.py` — extracted helper if the subprocess
  contract deserves its own module (Coder decides in design). Same subprocess pattern
  the spike runner uses (temp props file, subprocess wall-time-measured invocation,
  strict output-path validation).
- **New** `tests/test_video_service_remotion.py` — real-file-based tests
  (subprocess mocked, but the wire-up path exercised end-to-end): renderer selection
  (default ffmpeg, override to remotion), Remotion failure → ffmpeg fallback (I36-a
  invariant), kill switch DIE_VIDEO_RENDERER=ffmpeg forces ffmpeg regardless of request,
  fallback rate reported correctly.
- **Modify** `tests/test_video_service.py` (existing ffmpeg-path tests) — add one guard
  test asserting the default renderer path is byte-for-byte identical to today's output
  (a real revert-verifier: this file was untouched all Phase 19, its existing tests
  must all still pass unmodified).
- **Packaging** — depends on D19.7-h choice:
  - Bundle: extend the PyInstaller spec (`app/desktop_launcher.py`'s associated `.spec`
    file) with the `video-renderer/` tree + Chrome Headless Shell binary.
  - Download-on-first-use: no bundle change; add first-run guidance flow.
  - Drop packaging: doc note only, no code change.
- `CHANGELOG.md` — one `[Unreleased]` bullet.
- `.viepilot/phases/19-remotion/PHASE-STATE.md` — flip 19.7 to done, evidence log entry.
- New `docs/operations/phase19-t7-wireup.md` — task-scoped report.

**Not allowed:** any file under `data/`, `docs/samples/`, `docs/report/`, the prior
Phase 19 reports (all immutable). `data/app.db` is `mode=ro` from Coder side (standing
post-19.2 rule).

## Design decisions (Coder, doc-first — commit under `docs(review)` before code)

### D19.7-a: Default preservation (the most important invariant)

- Confirm at code level, not just claim: with `DIE_VIDEO_RENDERER` unset and no
  `renderer` field in the request, `VideoService.generate_video()` executes the exact
  same code path it does today. Cite the branch/conditional.
- Confirm by test: `tests/test_video_service.py`'s existing 10+ tests still pass
  unmodified. Adding a `default_renderer_still_ffmpeg` test that revert-verifies (revert
  the new branch, confirm no existing test fails) is the strongest signal.
- Revert-and-confirm-failure discipline is critical this task — first `video_service.py`
  touch of Phase 19.

### D19.7-b: Request → setting → kill switch resolution order

- Recommend: **request-time `renderer` field > settings toggle > env var default.**
  Request field is the most specific ("this call wants X"). Settings toggle is the user
  preference. Env is deployment default.
- Kill switch `DIE_VIDEO_RENDERER=ffmpeg` (or any value not `remotion`) MUST force
  ffmpeg regardless of request. This is the "safety" direction of I36.
- The OTHER direction — request wants ffmpeg, env says remotion — should also honor the
  request (ffmpeg is the safer fallback, always allowed).
- Diagram the resolution in the design commit as ASCII decision tree.

### D19.7-c: Remotion subprocess contract

- Extract the spike runner's subprocess pattern into a callable helper (`_render_via_
  remotion(project_id, output_path, ...)`). Same temp-props-file + `time.monotonic()`
  wall time + strict output-path validation.
- Timeout: recommend 10 min (Gate B-11 evidence: 8-min episode ~2.8 min extrapolated;
  10 min is 3.5× safety margin for full-8-min real episodes and shared-machine load).
- On timeout OR non-zero exit OR missing output file: raise a new
  `RemotionRenderFailedError`; caller catches, sets `fallback_used=True`, dispatches to
  ffmpeg path.
- Log the fallback reason (timeout / non-zero exit / missing output) in structured form
  for the fallback-rate readout.

### D19.7-d: Fallback rate readout

- New endpoint `GET /api/video/health` (or extend `/api/health`) returning:
  `{remotion_configured: bool, remotion_total_calls: int, remotion_fallback_count: int,
  fallback_rate: float, last_fallback_reason: str | null}`.
- Counters live in a small module-level dict inside `video_renderer_remotion.py` — same
  approach as Phase 18's per-provider counters (D22 spirit).
- No database persistence — counters reset on server restart (owner-acceptable per Phase
  18 precedent).

### D19.7-e: `check_dependencies.py` extension

- Add 3 new checks: Node.js version, `video-renderer/node_modules` present + fresh,
  Chrome Headless Shell present-or-downloadable.
- GREEN when all 3 pass. YELLOW (guidance, not crash) when any missing.
- Missing dependency shows install guidance and states "Remotion path unavailable —
  Standard (ffmpeg) still works." Never hard-crash the app; ffmpeg default keeps working.

### D19.7-f: Step 5 UI toggle

- Small pill/toggle above Generate button, 2 options: "Standard" (ffmpeg) and
  "Enhanced (Remotion, opt-in)". Default is Standard.
- When `check_dependencies` reports Remotion path unavailable: Enhanced option is
  disabled with tooltip explaining why.
- Toggle state persisted via existing localStorage pattern used elsewhere in Step 5
  (subtitle-style picker etc.). Not saved to DB.

### D19.7-g: Test story

- Real-file-based tests for `video_service.py`'s new branches (subprocess mocked to
  simulate success + timeout + non-zero exit + missing output — all 4 paths tested).
- Kill switch test: env forces ffmpeg regardless of request.
- Default-preservation test: no toggle, no env → ffmpeg path unchanged.
- Existing `tests/test_video_service.py` tests must all pass unmodified.
- One live-verification: real Remotion render triggered via `POST /api/projects/{id}
  /video?renderer=remotion` against the running dev server (port 8000), owner-visible
  output at Step 5 UI. Document the wall time + output file path in handover.

### D19.7-h: Packaging decision (Amendment A)

**The blocker Amendment A left for this task.** Three options with real numbers:

- **Option 1 — Bundle Chrome Headless Shell in `.exe`:** 169 MB → 740-840 MB (~5×). Every
  user pays the bundle cost, including users who never touch Remotion path. Predictable
  install, no first-run download risk.
- **Option 2 — Download-on-first-use:** Remotion's own CLI supports this natively. Base
  `.exe` stays near today's 169 MB; first Remotion render downloads ~270 MB once, cached
  in `%LOCALAPPDATA%\DailyIntelEnglishStudio\video-renderer-cache\`. Requires network
  first time. Must degrade cleanly to ffmpeg if download fails.
- **Option 3 — Drop packaging, dev-mode only:** `.exe` unchanged (fastest ship). Remotion
  path only works when app runs from source via `uvicorn` (owner's own machine, which is
  already set up). End users get ffmpeg only.

**Recommend Option 2** (download-on-first-use) as best cost/benefit: users who don't
touch Remotion never pay; users who do, pay once. But this is Coder's design call after
probing Remotion's own download mechanics — cite the actual CLI/API used, confirm
degradation-on-download-failure works, measure real first-run download time from a
clean machine.

If Option 2 turns out to have hidden gotchas at probe time (Remotion's downloader
requires elevated permissions, or fails silently, or downloads a much smaller/larger
binary than expected), fall back to Option 3 for the T6 shipping window and document
Option 1 as a future upgrade path. **Do not just Option 1 by default without probing 2
first** — the 5× size cost is real.

## Verification

- Full suite still passes; new `tests/test_video_service_remotion.py` tests all pass
  (recommend +6-8 new tests covering the branches above).
- **Revert-and-confirm-failure** on the default-preservation test (revert the new
  renderer-selection branch, confirm existing tests break). This is critical this task.
- `git log fe06405..HEAD -- app/services/video_service.py` will now be non-empty for the
  first time in Phase 19. That's expected. Note the commit shas in evidence.
- Live-verify end-to-end: real render via `POST /api/projects/{id}/video?renderer=
  remotion` against the running dev server on port 8000, owner-visible output at Step 5.
- Kill switch tested: set `DIE_VIDEO_RENDERER=ffmpeg`, restart server, real request with
  `renderer=remotion` still runs ffmpeg.
- Media gate: real render output ffprobe'd, duration/A-V/codec all pass (I40 invariant).

## Evidence (Coder handover)

- Two shas (design + implementation).
- Full-suite line + ruff + tsc + vitest lines.
- Which packaging option (D19.7-h) chosen + real probe evidence + expected footprint.
- Live-render wall time via new wire-up path.
- Fallback rate readout example (real numbers after a few test calls).
- `test_video_service.py`'s existing 10+ tests all passed unmodified confirmation.
- Revert-and-confirm-failure done on default-preservation test.

## Definition of done

- Two commits, design before implementation.
- Remotion path callable via request flag + settings + env, ffmpeg still default.
- Kill switch verified. Fallback verified.
- Packaging shape decided + real evidence documented.
- All checks green. Existing video_service.py tests unmodified.
- Handover per Evidence checklist.

## PM note

This is the biggest task in Phase 19 by real code volume (touches backend + frontend +
tests + packaging + docs). If it takes 2-3 days that's expected. Don't rush the
default-preservation testing — first `video_service.py` touch in Phase 19 is where a
regression could silently ship. Revert-and-confirm-failure on the default-preservation
test is not optional this round.
