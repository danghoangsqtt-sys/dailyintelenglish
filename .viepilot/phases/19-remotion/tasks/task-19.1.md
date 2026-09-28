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
