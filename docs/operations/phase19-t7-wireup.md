# Phase 19 Task 19.7 — `VideoService` wire-up + toggle + kill switch + packaging

- **Task:** 19.7 (Coder). Design record: `.viepilot/phases/19-remotion/tasks/task-19.7.md`
  (D19.7-a..h, PM-approved 2026-09-29, sha `906c5e5`).
- **Run date:** 2026-09-29. **Code HEAD at task start:** Task 19.6 accepted (`e3d92d6`,
  PM task-level).
- **Scope:** the first task in Phase 19 that touches `app/services/video_service.py`.
  `git log fe06405..<this task's implementation sha> -- app/services/video_service.py` is
  non-empty for the first time — expected, documented here per the card's own instruction.

## 1. Default preservation (D19.7-a) — confirmed at code and test level

`generate_video()`'s signature gained 4 new trailing keyword parameters
(`renderer="ffmpeg"`, `db=None`, `project=None`, `learning=None`); every pre-Phase-19 call
site (all of `app/api/video.py`'s route, every existing test) omits all 4, so
`_resolve_renderer("ffmpeg")` (actually called with the default value `renderer="ffmpeg"`
directly) always returns `"ffmpeg"`, and the function falls straight through to the
existing ffmpeg body — same object code as before this task, now reached via
`effective_renderer == "remotion"` evaluating false rather than being the only path.

**Revert-and-confirm-failure done for real** (not optional this round, per the card): with
`_resolve_renderer` temporarily hardcoded to always return `"remotion"`, both
`test_default_renderer_still_ffmpeg_never_touches_remotion`
(`tests/test_video_service.py`) and `test_kill_switch_forces_ffmpeg_even_when_request_wants_remotion`
(`tests/test_video_service_remotion.py`) failed with genuine `AssertionError`s from the
injected "must never be called" guards — not silent passes. Restored, both green again.

**Real correction to the design doc's own count:** the design record claimed
`tests/test_video_service.py` had "12 test functions" — the real count (confirmed by
running `pytest -v` before writing any code) is **21** existing tests, now **22** with the
new guard test. All 22 pass unmodified.

## 2. Resolution order (D19.7-b) — real decision tree, live-verified

Two real backend tiers (not three — see the design doc's own scope-clarification finding,
PM-accepted): the `DIE_VIDEO_RENDERER` kill switch decides whether Remotion is reachable at
all; a request may always downgrade to ffmpeg. Both directions verified live against a real,
isolated server instance (§5 below), not just unit tests.

## 3. Remotion subprocess contract (D19.7-c)

`app/services/video_renderer_remotion.py` (new): `render_via_remotion` builds real props
(reusing `avatar_service.resolve_avatar_path` for real avatar resolution — NOT
`project["speakers"]`'s own `avatar_image_path` field, which `project_service.get_project`
already rewrites into a served URL rather than a filesystem path, a real finding caught
before writing the copy helper) and hands off to `_render_via_remotion_sync` via
`asyncio.to_thread` for the blocking subprocess call (600s timeout, unchanged from the
design's justification). `RemotionRenderFailedError` (new, `app/core/exceptions.py`) raised
on timeout/non-zero-exit/missing-output; all 4 branches (success + 3 failure modes) unit
tested with a mocked `subprocess.run`.

**Production path deliberately does NOT re-synthesize missing word timestamps** (unlike
`scripts/run_remotion_spike.py`, which does this as a spike-only measurement-continuity
convenience for one pre-Task-19.2 demo episode). A real render whose line has no captured
`word_timestamps_json` simply renders the Task 19.3 (D19.3-c) plain-text fallback — no
karaoke highlight for that line, not an error, and no extra TTS cost on every render.

## 4. Fallback rate readout (D19.7-d)

`GET /api/video/health` (new route, `templates_router`'s existing `/api/video` prefix).
Real readout after this task's live verification (§5): 2 successful Remotion calls, 0
fallbacks —
```json
{"remotion_configured": true, "remotion_total_calls": 2, "remotion_fallback_count": 0,
 "fallback_rate": 0.0, "last_fallback_reason": null}
```
A separate server instance (kill-switch test, §5) correctly shows `remotion_total_calls: 0`
— proof the kill switch prevents Remotion from ever being attempted, not just from
succeeding.

## 5. Real live verification — isolated server, never touching the owner's port-8000 dev server

**Real constraint found during implementation, not anticipated in the design doc:** the
card's verification checklist asks to test the kill switch by "restart[ing] the server" and
to live-verify "against the running dev server on port 8000." Both are blocked by this
project's own standing rule (never stop/restart the port-8000 dev server, kept running for
the owner's own rehearsal use) — and since `settings.VIDEO_RENDERER` is read once at
`Settings()` construction (process startup), the *already-running* port-8000 process cannot
be made to honor a new `DIE_VIDEO_RENDERER` value without an actual restart. Confirmed this
isn't an oversight: `GET http://127.0.0.1:8000/api/video/health` returned a real 404 (that
process is running pre-19.7 code), proving no `--reload` picked up these changes either.

**Resolution (disclosed, not silently worked around):** ran the real, unmodified app on a
separate port (8091) against an isolated **copy** of `data/app.db` in a temp directory
(`DIE_DATA_DIR` override) — a real, honest file copy, never a live connection to the
production database, and completely isolated from the owner's running instance. Two
real server lifecycles:

1. **`DIE_VIDEO_RENDERER=remotion`** — real `POST /api/projects/b330d37f.../video/generate`
   with `{"renderer": "remotion", ...}` against the real pinned demo project. **Two runs**
   (the first request's background-shell handling was investigated and both turned out to
   have completed successfully — real evidence, not a flaw):
   - Run 1: **70.609s** wall time (`processing_time_ms: 70609.72`), `mode: "remotion"`,
     `fallback_used: false`.
   - Run 2: **72.457s** wall time, same result shape.
   - Real output ffprobe'd: 1280x720 h264 @ 30fps, 183.533s video / 183.573s audio (both
     streams present, 0.04s apart — well inside the ±0.5s I40 media-gate tolerance), 5506
     video frames (`ceil(183.533 × 30)`, exact — matches Task 19.6's own composition math).
   - This is the **first real end-to-end Remotion render triggered through the actual app's
     API route** (not the spike script) — proves the full composition (karaoke, speaker
     chip, vocab card, intro/outro, chapter bar) renders correctly via production code.
2. **`DIE_VIDEO_RENDERER` unset (default)** — same request, same project, `renderer:
   "remotion"` in the body. Real result: `mode: "background"`, `mp4_path` pointing at the
   real ffmpeg output (`video.mp4`, not `video_remotion.mp4`), `background_image:
   "deep_purple"` (the ffmpeg template actually used), wall time **7.76s** (matches ffmpeg
   speed, not Remotion's ~70s) — the kill switch genuinely forced ffmpeg. `/api/video/health`
   on this second instance showed `remotion_total_calls: 0`, confirming Remotion was never
   even attempted, not attempted-and-silently-ignored.

Both temporary server instances were shut down immediately after; `curl
http://127.0.0.1:8000/` was re-checked afterward and still returns 200 — the real dev server
was never touched.

## 6. `check_dependencies.py` extension (D19.7-e)

3 new informational (non-fatal) checks, delegating to `video_renderer_remotion`'s own
functions so the CLI script and `/api/video/health` share one real source of truth:
`check_node_version` (real finding: this project's own `video-renderer/package.json` pins
`>=24.0.0`, not the design's initial ">=20" — corrected before implementation, per the
design doc), `check_video_renderer_deps` (node_modules present + fresher than
package-lock.json), `check_remotion_browser` (already-downloaded OR
`REMOTION_ALLOW_DOWNLOAD`-permits-a-future-download; unconditionally YELLOW on Windows
arm64, since Chrome Headless Shell has no build for that platform — found during the design
probe).

## 7. Step 5 UI toggle (D19.7-f)

New "Standard (ffmpeg)" / "Enhanced (Remotion, opt-in)" pill above the Generate button.
Persisted via `localStorage` key `"die-video-renderer"` (following `theme.js`'s real,
confirmed `"die-*"` convention — the design doc's claimed existing Step 5 localStorage
precedent didn't exist, confirmed by grep before writing any code). Enhanced option disabled
with a tooltip when `GET /api/video/health`'s `remotion_configured` is false. A stored
`"remotion"` preference is only honored when currently configured — otherwise the toggle
would render checked-but-disabled, a confusing combination avoided deliberately.

**Necessary mechanical extension, disclosed (not in the card's Allowed files):**
`frontend/static/js/api.js`'s `generateVideo()` needed a new `renderer` parameter and a new
`getVideoHealth()` call — the same class of gap as Report-UX-1's HTML `<script>` tags and
Task 19.2's undercounted test file. Fixed and disclosed here rather than left broken.

## 8. Packaging decision (D19.7-h) — real production-only footprint measured

Design doc estimated ~350 MB (derived from prior measurements, not a fresh probe) for a
production-only `video-renderer/` install. **Real measurement this task**, in an isolated
temp copy of `package.json`/`package-lock.json` (never touching the real dev
`node_modules/`): `npm install --omit=dev --no-audit --no-fund` → **251 packages, 257 MB**,
confirmed to include zero browser bytes (`node_modules/.remotion` absent — the Chrome
Headless Shell download is a separate, later event, exactly as designed). **257 MB is
smaller than the design's own estimate**, not larger — a real, favorable correction.
Option 2 (download-on-first-use) recommendation stands, confirmed via the design phase's
live probe (renaming the browser cache away and re-rendering triggered a fully automatic
~113 MB download with zero custom code) and this task's real footprint number.

**Scope clarification, found while reading the card's own "Allowed files" text carefully:**
the card's Option 2 packaging bullet says "no bundle change" — meaning this task does not
modify `daily_intel_english_studio.spec` to add `video-renderer/` as bundled data. A
packaged `.exe` today therefore still has no working Remotion path (no `video-renderer/`
directory ships at all) — `check_dependencies.py`'s `check_video_renderer_deps` correctly
reports this as missing/YELLOW there, with "Standard (ffmpeg) still works" guidance. The
`_default_data_dir()`-style per-user-writable-copy plan documented in the design record
remains the right approach for **whenever a future task actually adds the `.spec` bundle
entry** — it is not implemented as working code in this task, since the card explicitly
scopes it out for now.

## 9. Full checks

- Python full suite: **1205/1205 passed** (1189 baseline + 16 new: 15 in
  `tests/test_video_service_remotion.py` + 1 guard test in `tests/test_video_service.py`).
- `ruff check .`: **clean** (whole repo).
- `tests/test_video_service.py`: all **22** tests (21 existing + 1 new) pass unmodified.
- **3 real, necessary test-assertion updates**, disclosed: `tests/test_video_shell_browser.py`
  (1) and `tests/test_video_studio_browser.py` (2) asserted the exact JSON body sent to
  `/video/generate` — adding the new `renderer` field to that body (D19.7-f) broke these 3
  real, pre-existing assertions. Fixed by adding `"renderer": "ffmpeg"` to each expected
  payload (the real, correct new default), not by weakening the assertions.
- `git log fe06405..<impl sha> -- app/services/video_service.py`: **non-empty for the first
  time in Phase 19** — expected, this task's whole point.
- Media gate (I40): real Remotion output's duration (183.533s video / 183.573s audio) is
  0.04s apart, well inside ±0.5s; codecs h264/aac, both real and playable (ffprobe-confirmed,
  §5).

## 10. Carry-over conditions (acknowledged, not acted on)

1. **8-min B1 episode:** still does not exist in `data/app.db`. This task's live
   verification rendered the same `b330d37f...` (2:56 actual) every prior Phase 19 task
   used.
2. **Packaged `.exe` Remotion support:** not implemented this task (D19.7-h's "no bundle
   change" scoping) — a future task must add `video-renderer/`'s production files to
   `daily_intel_english_studio.spec` and implement the per-user-writable-copy plan before a
   packaged install can offer the Enhanced renderer at all.
3. **Live network-download-failure fallback:** not re-demonstrated live this task (the
   design phase's own probe already produced this evidence with a bad `--browser-executable`
   path — real exit 1, no output file, degrading via the same generic non-zero-exit path
   this task's mocked tests also cover). Not repeated live here since it would require
   disrupting the shared `video-renderer/` directory's browser cache, which other
   concurrently-running Phase 19 work might depend on.
