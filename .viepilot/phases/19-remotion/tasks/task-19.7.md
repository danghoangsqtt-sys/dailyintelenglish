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

## Design decisions — Coder answers (2026-09-29)

Investigated real code before answering (no code written yet). All 8 of the card's own
D19.7-a..h points are **confirmed as the plan**, with real findings/corrections below —
most significantly on D19.7-b (scope clarification) and D19.7-h (the packaging probe, which
turned up a materially different real mechanism than Amendment A assumed).

### D19.7-a: Default preservation

Read `app/services/video_service.py:233-293` in full: `generate_video()` currently has **no
`renderer` concept at all** — its only branch is `aspect_ratio == "9:16"`. Plan: extract the
existing body's ffmpeg-calling section unchanged (the `_write_video_outputs_sync` call
through the `_render_video_sync`/`_render_vertical_sync`/`result` construction) so it remains
reachable as the exact same code, then add `renderer: Literal["ffmpeg", "remotion"] = "ffmpeg"`
as a new trailing parameter. With no argument passed (positional call sites in
`app/api/video.py` don't pass it) and no env override, `renderer` resolves to `"ffmpeg"` and
the function takes the literal branch that calls the unchanged ffmpeg path — same object
code, not a re-implementation. The dispatch looks like:

```python
async def generate_video(project_id, audio_job, template_id, aspect_ratio="16:9", renderer="ffmpeg") -> dict:
    ...same validation as today...
    effective_renderer = _resolve_renderer(renderer)  # D19.7-b
    if effective_renderer == "remotion":
        try:
            return await _render_via_remotion(...)
        except RemotionRenderFailedError as exc:
            logger.warning("remotion_render_failed_fallback_to_ffmpeg reason=%s", exc)
            # falls through to the exact same ffmpeg path below, result["fallback_used"] = True
    ...existing ffmpeg body, byte-for-byte, result["fallback_used"] = False...
```

Test plan: `tests/test_video_service.py`'s existing 12 tests must all pass with zero edits
(confirmed current count: 12 test functions in that file, none touch a `renderer` concept).
New `default_renderer_still_ffmpeg` test in that same file asserts calling
`generate_video(...)` with no `renderer` arg produces `result.get("fallback_used") in (None,
False)` and no Remotion subprocess is invoked (monkeypatch `_render_via_remotion` to raise if
called at all — the strongest possible signal that the default path never touches it).
Revert-and-confirm-failure: temporarily make the default resolve to `"remotion"`, confirm the
new guard test fails for real (an actual subprocess-invoked assertion, not a mock miss).

### D19.7-b: Resolution order — scope clarification (real finding)

The card's own text says "request-time `renderer` field > **settings toggle** > env var
default" (three tiers), but the "Allowed files" list has no `app/services/settings_service.py`
entry, no DB column, and no Settings-page UI — and D19.7-f explicitly says the Step 5 toggle
is "persisted via localStorage... **Not saved to DB**." Read `settings_service.py` to confirm
what a real DB-backed "settings toggle" looks like in this app (`set_ai_mode`,
`set_cloud_settings`, etc., all `async def set_*(db, ...)` writing to a `settings` table) —
none of that machinery is in this task's scope. **Resolved:** this task implements exactly
**two** real resolution tiers, not three. The "settings toggle" in the card's prose refers to
the localStorage-persisted Step 5 UI preference, which is not a server-side tier at all — it's
simply where the request's own `renderer` field value comes from before the request is sent.
A genuine DB-backed per-installation default (a real third tier, Settings-page-controlled)
is not in this task's Allowed files and is not implemented here; flagging so it isn't silently
assumed to exist. Decision tree (two real tiers):

```
DIE_VIDEO_RENDERER env var (default "ffmpeg")
        │
        ▼
  is env value "remotion"?
   ├─ no (unset / "ffmpeg" / anything else) ──► ffmpeg, ALWAYS (kill switch, ignores request)
   └─ yes ──► does the request specify renderer?
                ├─ no  ──► "remotion" (env default applies)
                ├─ "remotion" ──► "remotion"
                └─ "ffmpeg" ──► "ffmpeg" (request may always downgrade to the safe path)
```

`_resolve_renderer(requested: str | None) -> Literal["ffmpeg", "remotion"]` in
`video_renderer_remotion.py`, pure and unit-tested directly (no request/DB needed to test it).

### D19.7-c: Remotion subprocess contract

Extracting `scripts/run_remotion_spike.py`'s `_run_render`/`_run_still` pattern (temp props
file, `time.monotonic()` wall time, `cwd=video-renderer/`) into
`app/services/video_renderer_remotion.py::_render_via_remotion(project_id, audio_job, ...,
output_path)`. Timeout: **600s (10 min)**, per the card's own recommendation — cross-checked
against every real Phase 19 measurement so far: the highest real wall time observed across
19.1-19.6 was 19.6's own transient-load outlier at **85.07s** (task-19.6 report §7); 19.1's
linear extrapolation to a genuine 8-minute episode was **~166s**. 600s is a ~3.6x margin over
the extrapolated 8-min case and a ~7x margin over the worst real measurement seen so far —
matches the card's own justification, confirmed against real numbers rather than assumed.
`RemotionRenderFailedError(AppError)` added to `app/core/exceptions.py` (same base class as
`VideoRenderError`, `TTSError`, etc. — `app/core/exceptions.py:4-62`). Raised on timeout,
non-zero exit, or missing output file after exit 0 (defensive: D19.7-h's probe below showed
Remotion itself always produces a real non-zero exit on failure, but checking the file too
costs nothing and matches `_render_video_sync`'s own belt-and-suspenders style). Fallback
reason (`"timeout"` / `"non_zero_exit"` / `"missing_output"`) logged structurally and fed to
the D19.7-d counters.

### D19.7-d: Fallback rate readout

Read `app/api/ai_jobs.py`'s `/api/ai/health` (`health_router`, `app/main.py`'s
`_ai_circuits: dict[str, CircuitBreaker] = {}` at line 38) as the real in-memory-counter
precedent the card's "D22 spirit" note refers to — confirmed it's a genuine module-level
dict pattern already used for exactly this class of "process-lifetime, no DB" runtime state.
New `_remotion_stats` module-level dict in `video_renderer_remotion.py`:
```python
_remotion_stats = {"total_calls": 0, "fallback_count": 0, "last_fallback_reason": None}
```
`GET /api/video/health` (new route on `templates_router`'s existing `/api/video` prefix in
`app/api/video.py`, alongside `/templates`) returns `{remotion_configured: bool,
remotion_total_calls, remotion_fallback_count, fallback_rate, last_fallback_reason}`.
`remotion_configured` reports whether `check_dependencies`'s 3 new Remotion checks (D19.7-e)
currently pass — computed live, not cached, since Node/Chromium availability can change
between calls (e.g. mid-first-download). Resets on server restart, same as `_ai_circuits` —
owner-acceptable per the Phase 18 precedent the card cites.

### D19.7-e: `check_dependencies.py` extension — real correction (Node version)

The card says "Node.js version (≥ 20 per Remotion 4.0.x requirements)", but
`video-renderer/package.json:7-9` already declares `"engines": {"node": ">=24.0.0"}` for this
project's own actual pinned Remotion version (`4.0.529`), and the owner's real installed
Node is **v24.20.0** (confirmed 2026-09-28, PHASE-STATE.md preflight). Using this project's
own real stated requirement (`>=24`) rather than a generic "Remotion 4.0.x" figure from the
card avoids a check that could pass at a version this specific pinned release doesn't
actually support. Three new checks in `check_dependencies.py`, following the file's existing
`check_*() -> tuple[bool, str]` convention exactly (`check_ffmpeg`, `check_ollama`, etc.):
- `check_node_version()`: `node --version` (or `shutil.which`), parse major version, GREEN
  if `>= 24`.
- `check_video_renderer_deps()`: `video-renderer/node_modules/` exists AND its mtime is
  `>=` `video-renderer/package-lock.json`'s mtime (a stale/pre-lockfile-change install would
  otherwise silently report GREEN).
- `check_remotion_browser()`: GREEN if `video-renderer/node_modules/.remotion/` already has a
  downloaded browser (real path confirmed by probe, D19.7-h below) OR
  `settings.REMOTION_ALLOW_DOWNLOAD` is true (download-on-first-use will handle it) —
  otherwise YELLOW with the "Standard (ffmpeg) still works" guidance line, matching the
  file's existing `check_ollama`/`check_gpu` non-fatal style exactly. **Real edge case found
  during the packaging probe (not in the card):** Chrome Headless Shell has no Windows arm64
  build at all (`BrowserFetcher.js`'s `downloadBrowser`, source-confirmed) — on Windows
  arm64, this check reports YELLOW regardless of `REMOTION_ALLOW_DOWNLOAD`, since no
  download would ever succeed there.
- All three added to `informational_checks` (YELLOW, non-fatal), never `required_checks` —
  same discipline as the existing Ollama-missing precedent this file already follows.

### D19.7-f: Step 5 UI toggle — real correction (no existing localStorage precedent in Step 5)

The card says the toggle should persist "via the existing localStorage pattern used
elsewhere in Step 5 (subtitle-style picker etc.)" — grepped `frontend/static/js/step5_video.js`
directly: **no `localStorage` call exists anywhere in that file.** The only real
`localStorage` precedent in the whole frontend is `theme.js`'s dark/light toggle
(`STORAGE_KEY = "die-theme"`, kebab-case, `"die-"`-prefixed). No subtitle-style picker with
localStorage exists in Step 5 today either — flagging this as a card inaccuracy rather than
silently inventing a citation. Plan: follow `theme.js`'s real, confirmed convention instead —
new key `"die-video-renderer"`, values `"ffmpeg"` (default) / `"remotion"`. Toggle pill
disabled (with a tooltip, `title` attribute, matching this app's existing disabled-control
style) when `GET /api/video/health`'s `remotion_configured` is false. Toggle's chosen value
is read at Generate-click time and passed as the request body's `renderer` field (this is the
literal mechanism referenced by D19.7-b's "settings toggle" language, per that finding).

### D19.7-g: Test story

New `tests/test_video_service_remotion.py`: subprocess mocked via `monkeypatch.setattr` on
`video_renderer_remotion.subprocess.run` (matching `test_video_service.py`'s own
`_install_sleepy_subprocess_run` convention for the ffmpeg side) — 4 branches (success,
timeout, non-zero exit, missing output file), kill-switch test (env forces ffmpeg regardless
of request), default-preservation guard test (D19.7-a), fallback-rate-counter test (2 calls,
1 forced failure, asserts `fallback_rate == 0.5`). `tests/test_video_service.py` gets exactly
one new test (D19.7-a's guard); its existing 12 pass unmodified — reconfirmed as part of this
design pass, not just claimed.

### D19.7-h: Packaging decision — real probe, real correction to Amendment A's assumed mechanism

**Probed Option 2 directly, as the card requires, before recommending anything.** Real
findings, in order of how they were found:

1. **Real cache location (corrects the card's assumption):** Amendment A / this card's D19.7-b
   area assumed a bespoke `%LOCALAPPDATA%\DailyIntelEnglishStudio\video-renderer-cache\` path.
   Read `@remotion/renderer`'s real source
   (`node_modules/@remotion/renderer/dist/browser/get-download-destination.js`): the download
   cache is `getDownloadsCacheDir()`, which walks **up from `process.cwd()`** to the nearest
   directory containing a `package.json`, then uses `<that dir>/node_modules/.remotion/`.
   There is no env var to override this path — only an explicit `--browser-executable=<path>`
   CLI flag that bypasses the whole mechanism to point at an already-downloaded binary
   elsewhere. Confirmed for real: `video-renderer/node_modules/.remotion/` already exists on
   this dev machine at exactly **270 MB** (`chrome-headless-shell/win64/chrome-headless-shell-win64/`),
   matching Amendment A's on-disk estimate exactly, VERSION file reads `149.0.7790.0`.

2. **The CLI downloads automatically — zero custom orchestration code needed.** Real probe:
   renamed `video-renderer/node_modules/.remotion` out of the way, ran
   `npx remotion still src/index.ts StillFrame out.png --frame=0` with **no special flags**.
   Real terminal output: `Getting Headless Shell - 19.1 Mb/113.3 Mb` progressing to
   `Got Headless Shell`, then a normal successful render (exit 0, real PNG produced).
   `remotion render`/`remotion still` call `ensureBrowser()` internally before rendering —
   the existing `_run_render`/`_run_still`-style subprocess call already gets this behavior
   for free; no `browser ensure` pre-step or custom download orchestration is needed in
   `_render_via_remotion`.
3. **Real size correction:** the **network download is ~113.3 MB** (compressed zip); the
   **on-disk extracted footprint is ~270 MB** (Amendment A's number). These are two different
   numbers for two different things — worth stating precisely rather than conflating them.
4. **Degrade-on-failure confirmed, and it needs zero new code:** probed a real failure by
   passing a deliberately invalid `--browser-executable=/definitely/not/a/real/path`. Real
   result: exit code **1**, no output file produced, stderr:
   `Error: "browserExecutable" was specified as '...' but the path doesn't exist.` This is
   the *exact same shape* (non-zero exit, no output file) as every other Remotion failure
   D19.7-c's fallback contract already catches — a real network-download failure would
   surface the same way (an uncaught rejection inside the CLI process → non-zero exit), so
   **no special-case "download failed" branch is needed** in `_render_via_remotion`; the
   existing generic non-zero-exit → `RemotionRenderFailedError` → ffmpeg-fallback path
   already covers it. No elevated-permissions requirement was observed (ran as a normal,
   non-elevated shell on this dev machine).
5. **Real platform gap found (not in the card):** `BrowserFetcher.js`'s `downloadBrowser`
   explicitly throws `"Chrome Headless Shell is not available for Windows for arm64
   architecture"` — Windows-on-arm64 has no working download target at all. Handled by
   D19.7-e's `check_remotion_browser` reporting YELLOW unconditionally on that platform.

**Recommendation: Option 2 (download-on-first-use), confirmed — no hidden gotchas found.**
Packaging implementation plan, matching an existing precedent in this exact codebase for the
identical underlying problem: `app/core/config.py`'s `_default_data_dir()` already redirects
`DATA_DIR` to `%LOCALAPPDATA%\DailyIntelEnglishStudio\data` when `sys.frozen` is true, because
a frozen `.exe`'s own install directory (e.g. under `Program Files`) may not be user-writable.
The exact same problem applies here, since Remotion's cache path is relative to `cwd`: bundle
`video-renderer/`'s source + **production-only** `node_modules` (the 5 real `dependencies` in
`package.json` — `@remotion/captions`, `@remotion/cli`, `react`, `react-dom`, `remotion` —
excluding the 4 `devDependencies` — `typescript`, `vitest`, `@types/react`,
`@types/react-dom` — Task 19.3 measured these at +37 MB) as a read-only reference inside the
frozen bundle; on first real Remotion use, copy that reference once into
`%LOCALAPPDATA%\DailyIntelEnglishStudio\video-renderer\` (writable, same directory family as
`DATA_DIR`), and always invoke the render/still subprocess with `cwd` pointed at that copy —
Remotion's own cache-dir walk then naturally lands in a writable, per-user location, and the
270 MB browser downloads there automatically on first real use, exactly as Option 2 intends.
**Expected footprint (estimate, not yet freshly measured — flagging honestly):** derived from
existing measurements, not a fresh `npm install --omit=dev` probe: Task 19.1's full workspace
was ~660 MB including the 270 MB browser; Task 19.3 measured devDependencies at +37 MB. A
production-only install (dependencies only, no browser) is therefore estimated at roughly
**~350 MB** added to the packaged `.exe` (660 − 270 browser − 37 devDeps ≈ 353 MB) — a real
measured number from an actual `npm install --omit=dev && du -sh` will replace this estimate
in the implementation-phase report, per the Evidence checklist's "expected footprint" line.
This is still far below Option 1's 740-840 MB bundle-everything cost, and every user who never
touches the Remotion toggle pays 0 MB extra beyond the ~350 MB base-app growth (no 270 MB
browser download ever triggers for them).

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
