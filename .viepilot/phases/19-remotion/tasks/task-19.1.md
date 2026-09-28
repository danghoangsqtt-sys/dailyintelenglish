# Task 19.1 — Spike: Remotion scaffold + minimal composition, measure render time

- **Status:** not started (doc-first card, awaiting Coder pickup)
- **Owner:** Coder
- **Priority:** P0 (blocks every other Phase 19 task card)
- **Dependency:** Phase 18 closed (2026-09-26, `v1.1.0-beta`, `die-vp-p18-complete`); a real
  completed B1 8-min episode exists in `data/app.db` (owner-supplied, read-only)
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.1"; ENH-013
  ("Constraints / risks" — render time, packaging weight, licence)

## Goal

Prove Remotion can render this project's video shape on the owner's machine within an
acceptable time and disk envelope, **before** any full-implementation task card is written
for 19.2 onward. This is a measurement task, not a feature task — no user-visible behaviour
changes.

## Allowed files

- **New** `video-renderer/` workspace (isolated Node/TypeScript/React tree, its own
  `package.json`, `tsconfig.json`, `.gitignore`, source under `video-renderer/src/`).
  - `video-renderer/package.json`, `video-renderer/tsconfig.json`, `video-renderer/.gitignore`
    (must exclude `node_modules/`, build output, and any absolute paths).
  - `video-renderer/src/index.ts` (Remotion entry: `registerRoot`).
  - `video-renderer/src/Root.tsx` (one composition: `Episode`).
  - `video-renderer/src/Episode.tsx` (React component: background + line-level subtitle track
    driven by an input props object).
  - `video-renderer/src/types.ts` (input-props types: `episodeId`, `lines[]` with
    `startSec`/`endSec`/`speaker`/`text`, `audioPath`, `outputPath`, `fps`, `width`,
    `height`).
  - `video-renderer/README.md` (install + how the CLI is invoked; ≤ 60 lines).
- **New** `scripts/run_remotion_spike.py` (Python-side runner: reads one real project from
  `data/app.db`, builds the input-props JSON, invokes `npx remotion render` as a subprocess,
  captures wall time + exit code + output file size, writes results into the spike report).
  Must be a pure script under `scripts/`, never imported by `app/`.
- **New** `docs/operations/phase19-spike-remotion.md` (the measurement report — see
  "Evidence" below for the exact structure expected).
- **New** `.viepilot/phases/19-remotion/tasks/task-19.1.md` (this file) already exists.
- `CHANGELOG.md` (append under `[Unreleased]` a single "Phase 19 spike (planning-only)" bullet
  once the report is on disk — no user-visible behaviour is claimed).

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, or `docs/implementation/`
(implementation-plan amendments come from PM after this report lands, not from the spike
itself). `data/app.db` is read-only for this task — no write of any kind, not even a
schema-migration test.

## Design decisions (Coder, doc-first — commit these under `docs(review)` before code)

The Coder writes a design section here answering each of the following, PM approves, then
code lands in a separate commit. This mirrors the Phase 18 doc-first pattern.

### D19.1-a: Remotion + Node versions

- Which Remotion version is pinned in `video-renderer/package.json` (record the exact
  `^X.Y.Z` and the resolved lockfile version)?
- Which Node LTS is required (`.nvmrc` or `engines.node` — pick one and document why)?
- Which package manager (npm / pnpm) — pick one, justify in one line, and use it consistently
  for the whole workspace.

### D19.1-b: Input-props schema

- The exact TypeScript shape of the input props (see `video-renderer/src/types.ts` above).
- Must be a strict subset of what already exists in `app/services/video_service.py` +
  `AudioService.mix_project`'s measured timestamps + `speakers` rows — **no new DB read
  paths, no schema change.** Justify each field.
- Explicitly no per-word timing in the spike input (that arrives in Task 19.2 only if
  the spike passes). Line-level start/end/speaker/text mirrors today's SRT.

### D19.1-c: Composition shape

- The composition renders a plain-colored background matching one of today's 3 ffmpeg
  templates, plus a bottom-third subtitle band showing the active line's `speaker: text`
  (styled to match today's libass burn-in, not fancier). The audio track is the same
  `AudioService`-mixed MP3 from `data/audio/<project_id>/final.mp3`, attached via Remotion's
  `<Audio>` component with `src` pointing to the local file.
- Explicit non-goals for the spike, called out here so scope stays honest: no karaoke, no
  active-speaker highlight, no vocab cards, no intro/outro, no chapter bar, no thumbnail
  still. Those are 19.3–19.6.
- Resolution 1920×1080, 30 fps, matching today's ffmpeg output exactly.

### D19.1-d: Subprocess contract

- The exact `npx remotion render <entry> <compositionId> <output> --props <path-or-JSON>`
  invocation, including how the input-props file is passed (temp file in Python's `tempfile`,
  never on the command line — command-line args are logged; a temp file is not).
- How stdout/stderr are captured (Python subprocess, `text=True`, timeouts).
- How wall time is measured (Python `time.monotonic()` around the subprocess boundary, not
  Remotion's own reported time — those two disagree by the Chromium spin-up overhead).

### D19.1-e: Real-episode selection

- Which project row from `data/app.db` is used (PM proposes: the most recent
  `status = 'complete'` B1 project; Coder confirms the id in the report, does not embed it in
  source).
- How the runner reads it (existing `ProjectService.get_project` + audio-job lookup) without
  taking any write lock and without triggering any autosave paths.

### D19.1-f: Fallback stance during the spike

- The spike **never** touches `app/services/video_service.py`. Today's ffmpeg-only default
  keeps producing videos for every other path. Verified by running the existing video
  browser tests (`tests/test_video_studio_browser.py`) after `video-renderer/` lands to prove
  they are still green.

## Design decisions — Coder answers (2026-09-28)

### D19.1-a: Remotion + Node versions

- **Remotion:** `^4.0.529` for both `remotion` and `@remotion/cli` (checked against the npm
  registry today, 2026-09-28 — the current published `latest`). Lockfile will record the
  exact resolved version after `npm install`; that resolved number goes into the spike
  report's "Environment" section, not restated here.
- **Node:** the owner's machine already has **Node v24.20.0** installed (`node --version`,
  verified directly — Phase 19's own preflight note that "Node.js runtime is not currently
  installed" is stale as of today and should be corrected in PHASE-STATE.md). Node 24 has
  been the active LTS line since October 2025, so this is not a pre-release runtime. I'm
  pinning `"engines": {"node": ">=24.0.0"}` in `video-renderer/package.json` rather than
  adding a `.nvmrc` — nothing else in this repo uses nvm, and `engines` is enough to
  document the requirement and gets enforced by npm on install (`engine-strict=true` in
  `video-renderer/.npmrc`).
- **Package manager: npm.** It's already installed alongside Node (v11.19.0) with nothing
  extra to add; the repo has zero existing Node tooling to match, so the lowest-friction
  choice wins. `video-renderer/package-lock.json` is committed so the resolved versions are
  reproducible.
- **React:** `^19.3.0` (latest on npm today). Remotion 4.0.529's peer dependency is
  `react`/`react-dom` `>=16.8.0`, so 19.x is compatible.

### D19.1-b: Input-props schema

```ts
// video-renderer/src/types.ts
export interface EpisodeLine {
  startSec: number;
  endSec: number;
  speaker: string;   // display label, e.g. "Alex" — not the speaker UUID
  text: string;
}

export interface EpisodeInputProps {
  episodeId: string;   // projects.id
  lines: EpisodeLine[];
  audioPath: string;   // absolute path to the already-mixed MP3
  outputPath: string;  // where this render's MP4 goes (spike scratch path, see D19.1-e)
  fps: number;          // 30
  width: number;
  height: number;
}
```

Field-by-field justification, and why nothing here opens a new DB read path:

- `episodeId` ← `project["id"]` from the existing `project_service.get_project(db, project_id)`.
- `lines[]` ← a straight 1:1 map of `audio_job["timestamps"]` entries, which
  `audio_service._mix_project_sync` already produces and stores as
  `audio_jobs.timestamps_json` (Task 1.6b). Each entry is already exactly
  `{start_sec, end_sec, label, speaker_id, text}` — the same shape `video_service.generate_srt`
  consumes today. The spike renames `label` → `speaker` in the TS type only for naming
  clarity; no new field, no new query.
- `audioPath` ← `audio_job["mp3_path"]`, i.e. whatever path `AudioService` actually wrote
  (`data/audio/<project_id>/mix.mp3` in the current code — note the phase `SPEC.md` text says
  `final.mp3`, which doesn't match the real filename; using the service's own returned path
  sidesteps that and any future rename).
- `outputPath` ← a spike-only scratch path the runner script picks
  (`data/tmp/phase19_spike/<project_id>.mp4`), never `data/video/<project_id>/video.mp4` —
  that path belongs to the ffmpeg fallback's `video_jobs` row and must not be raced or
  overwritten by an unrelated spike render.
- `fps` ← `30`, matching `VIDEO_FPS` (app/core/constants.py) so Remotion's frame count for an
  8-minute episode is the same ~14,400 frames the phase spec estimates.
- `width`/`height` ← **1280×720**, PM-confirmed (see D19.1-c below) — matches today's actual
  ffmpeg background PNGs (`frontend/static/video_backgrounds/*.png`) and
  `VIDEO_WIDTH_STANDARD`/`VIDEO_HEIGHT_STANDARD` exactly.

No per-word timing field is included, per D19.1-b's explicit non-goal — `lines[]` is
line-level only, mirroring today's SRT exactly.

**PM review — APPROVED with changes (2026-09-28):** confirmed **1280×720** — the card's
"1920×1080" line was a PM error, not a deliberate upscale (verified against
`app/core/constants.py:45-46`, `VIDEO_WIDTH_STANDARD=1280`/`VIDEO_HEIGHT_STANDARD=720`). The
composition renders at 1280×720 @ 30 fps. The spike report's §5 correctness spot-check adds
one sentence noting the rendered resolution matches the source background assets exactly (no
upscale). PM will correct the card's resolution text as part of the post-spike plan Amendment.

### D19.1-c: Composition shape

Resolution resolved to **1280×720 @ 30 fps** (see PM review above); everything else proceeds
as specified in the card.

- Plain-colored background: the spike reuses one of the three existing PNGs
  (`frontend/static/video_backgrounds/{midnight,deep_purple,charcoal_wave}.png`) as a static
  `<Img>` — no new artwork.
- Bottom-third subtitle band: a `<div>` positioned at the same relative screen position
  libass's ffmpeg `subtitles=` burn-in defaults to, showing `${line.speaker}: ${line.text}`
  for whichever `line` has `startSec <= currentFrame/fps < endSec`. Font/size/color chosen to
  visually approximate (not pixel-match) today's libass default styling — exact match isn't
  gate-worthy for a spike, called out explicitly in the report's §5 spot-check instead.
- Audio: Remotion's `<Audio src={staticFile(...) or absolute path}>` pointed at
  `audioPath`, i.e. the same normalized mix `AudioService` already produced. No re-encoding
  of the source audio before Remotion touches it.
- Confirmed non-goals for this task, unchanged from the card: no karaoke, no active-speaker
  highlight, no vocab cards, no intro/outro, no chapter bar, no thumbnail still.

### D19.1-d: Subprocess contract

- Invocation shape:
  `npx remotion render video-renderer/src/index.ts Episode <outputPath> --props=<tempPropsPath>`
  run with `cwd=video-renderer/` so Remotion resolves its own `remotion.config.ts` and
  `node_modules` normally.
- The input-props JSON is written with Python's `tempfile.NamedTemporaryFile(suffix=".json",
  delete=False)` before the subprocess call, its path passed via `--props=<path>`, and the
  temp file is deleted in a `finally` block after the render (or on any exception) — never
  passed as an inline `--props='{...}'` JSON blob on argv (keeps argv short for an 8-minute
  episode's line array, and avoids Windows' ~8K command-line length limit).
- `subprocess.run([...], capture_output=True, text=True, timeout=<render timeout>, cwd=...)`.
  stdout/stderr are both captured to variables and written into the spike report verbatim
  (truncated if very long) — never streamed to this session's own terminal, consistent with
  the standing rule about not letting subprocess output leak past what's needed (this data
  isn't secret, but the pattern of "capture, don't stream" stays consistent everywhere).
- Timeout: reuse the existing `_render_timeout_seconds` formula's shape (floor + per-second
  multiplier) but with wider constants for a first Chromium-based render — proposed floor
  600s, multiplier 8.0×audio-seconds, documented in the runner script's docstring; the actual
  measured wall time goes in the report regardless of what the timeout was set to.
- Wall time: `time.monotonic()` immediately before and after the `subprocess.run(...)` call,
  not Remotion's own self-reported render time (both are captured and both appear in the
  report, labeled separately, so the Chromium spin-up delta is visible).

### D19.1-e: Real-episode selection

- Selection query (read-only): the runner asks for projects with `status = 'complete'` whose
  `audio_jobs.status = 'complete'`, ordered by `projects.created_at DESC`, and picks the first
  one whose `audio_jobs.duration_seconds` is closest to 480s (8 minutes) — reusing
  `project_service.get_project` and `audio_service.get_audio_job` as-is, no new SQL against
  `app/services/*`. The runner script itself issues one small `SELECT id, created_at FROM
  projects WHERE status = 'complete' ORDER BY created_at DESC` to build the candidate list,
  since no existing service function returns "all complete projects" — this is a read-only
  ad hoc query local to `scripts/run_remotion_spike.py`, not a new function in `app/`.
- **Read-only enforcement at the connection level**, not just convention: the runner opens
  its own SQLite connection via
  `aiosqlite.connect(f"file:{db_path}?mode=ro", uri=True)` — a real OS-level read-only handle,
  not the app's shared read-write singleton (`app/db/database.py`), so a bug in the spike
  script cannot write to `data/app.db` even accidentally.
- The resolved project id is printed into the spike report's §3 "Real episode" section; it is
  never hardcoded into `video-renderer/` source or `scripts/run_remotion_spike.py` itself (the
  script takes it as a runtime lookup result, per the card's instruction).
- No write lock, no autosave path: `get_project` and `get_audio_job` are both pure `SELECT`s
  (confirmed by reading their current implementations) — using a `mode=ro` connection makes
  this true structurally as well as by inspection.

### D19.1-f: Fallback stance during the spike

- Confirmed: `video-renderer/` and `scripts/run_remotion_spike.py` never import or reference
  `app/services/video_service.py`, and no file under `app/` is touched by this task (matches
  "Allowed files" above).
- After `video-renderer/` lands, `tests/test_video_studio_browser.py` is run unchanged
  (read-only from this task's point of view — no edits to that file) to confirm the existing
  ffmpeg video-browser behaviour is still green. Result goes into the Definition-of-done
  checklist, not the spike report itself (report is about Remotion, not a regression suite).

## Verification

- Full suite (unchanged files only: this task cannot fail an existing test): **1175/1175
  pass, ruff clean**, same baseline as Phase 18 close-out.
- One real render of the selected episode succeeds end-to-end, its output MP4 opens in a
  media player, and `ffprobe` confirms duration within ±0.5 s of the source audio's duration
  (same tolerance as the existing media gate).
- The spike report `docs/operations/phase19-spike-remotion.md` is on disk and answers every
  "Evidence" item below with real measured numbers, not estimates.

## Evidence (structure of the spike report, filled in real)

The report is the deliverable. It must include, in this order:

1. **Environment.** Windows version, CPU model, RAM, GPU (owner's RTX 3060 12 GB), Node
   version, npm/pnpm version, Remotion version, headless Chromium version (Remotion prints
   this on first render).
2. **Install footprint.** `du -sh video-renderer/node_modules` (or Windows equivalent),
   Chromium binary size on disk, total added disk vs the pre-19.1 baseline.
3. **Real episode.** Project id, script line count, audio duration in seconds (from
   `ffprobe`), audio file size.
4. **Render measurement.** Wall time from `time.monotonic()`, Remotion's own reported time,
   output MP4 file size, output resolution/fps/codec (from `ffprobe`), peak RAM during
   render (Windows Task Manager screenshot or `Get-Process` capture).
5. **Correctness spot checks.** Manually stepped-through timestamps (start of line 1, end of
   line N) confirmed against SRT; audio-video sync check (existing media gate's A/V drift
   threshold applies verbatim); one extracted frame at t=middle showing the subtitle band.
6. **Packaging estimate.** Best current guess (numbers, not adjectives) of what a PyInstaller
   build including `video-renderer/node_modules` + Chromium would add to today's `.exe` size
   (owner's real 2026-09-18 packaged .exe size is the baseline — read from Phase 12 evidence
   or re-measure).
7. **Decision proposal.** One paragraph: PASS / SCOPE-CUT (which of 19.3–19.6 to drop) /
   STOP. This is a Coder proposal — PM decides.

## Definition of done

- All allowed files exist, all disallowed files unchanged.
- The full test suite is still 1175/1175 (this task adds no tests — it adds a Node workspace
  and a Python runner script).
- The spike report is on disk with every "Evidence" item filled from real measurement.
- `ruff check .` still clean; `node --check` (or `tsc --noEmit`) clean on the new
  `video-renderer/` sources.
- A separate `docs(review): task 19.1 design` commit lands before any code commit, so the
  git history proves the doc-first gate (per the standing self-implementation feedback rule).
- Handover message to PM includes: the spike report path, the wall-time number, the disk
  footprint number, and the PASS / SCOPE-CUT / STOP proposal.
