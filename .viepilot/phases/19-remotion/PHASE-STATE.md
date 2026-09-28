# Phase 19 State — Animated Learning Videos with Remotion (ENH-013)

## Metadata

- **Phase:** 19
- **Slug:** `19-remotion`
- **Status:** 19.1 accepted (PM + owner **D33**, 2026-09-28, spike PASS); 19.2 doc-first card ready, awaiting Coder pickup
- **Planned:** 2026-09-28 (`/vp-evolve ENH-013`)
- **Controlling plan:** `docs/implementation/phase-19-remotion.md`
- **Authorization:** owner decision **D29** (2026-09-24, brainstorm
  `docs/brainstorm/session-2026-09-24.md`); planning-shape decision **D32** (2026-09-28,
  spike-first + `video-renderer/` subdir).
- **Ownership of this folder:** PM until the handover commit, Coder after it.

## Preflight (to be completed when the spike starts)

- Phase 18 closed 2026-09-26 (`v1.1.0-beta`, tag `die-vp-p18-complete`).
- Full suite baseline **1175/1175**, `ruff` clean, real DB has 7 projects (see
  `.viepilot/TRACKER.md` Current Status).
- The current video pipeline (ffmpeg, `VideoService.generate_video`) is the fallback the
  spike must not touch — every `app/services/video_service.py` behaviour under the default
  `DIE_VIDEO_RENDERER` value must survive byte-for-byte.
- Node.js **v24.20.0** is already installed on the owner's machine (verified 2026-09-28;
  npm v11.19.0) — corrects this note's earlier assumption that Node was not installed. Node
  24 has been the active LTS line since October 2025. The spike still documents the pinned
  version and install path in `docs/operations/phase19-spike-remotion.md` before rendering.
- Owner has one real B1 8-min episode already in `data/app.db` with completed audio (Task
  1.6b measured timestamps) — the spike renders against that episode only. PM authorises the
  read-only DB access; Coder never mutates the real DB (write invariant, TRACKER §Bảo mật).
  **Found stale during the spike (2026-09-28):** the real DB has no project with
  `duration_minutes = 8` and a completed audio mix -- only one project anywhere in the DB has
  a completed `audio_jobs` row (`b330d37f...`, B1, 2:56 actual). The spike rendered that
  episode instead and extrapolates linearly to 8 minutes for the render-time conclusion; see
  `docs/operations/phase19-spike-remotion.md` for the full finding.

## Task status

| Task | Description | Owner | Status |
|---|---|---|---|
| 19.1 | Spike: `video-renderer/` scaffold + minimal Remotion composition (background + line-level captions, matching today's ffmpeg output) rendered for one real B1 episode (2:56 actual — see preflight caveat). Measure render time / packaging footprint / output correctness. Report `docs/operations/phase19-spike-remotion.md`. | Coder | **accepted** -- PM + owner D33 2026-09-28, PASS, sha `4dd325b`, full suite 1175/1175 re-verified by PM |
| 19.2 | Edge TTS `WordBoundary` capture + per-word timestamps storage + additive migration | Coder | **ready** (doc-first card `tasks/task-19.2.md`, awaiting Coder pickup) |
| 19.3 | Word-level karaoke captions composition | Coder | provisional |
| 19.4 | Active-speaker indicator | Coder | provisional |
| 19.5 | Vocab/idiom pop-up cards | Coder | provisional |
| 19.6 | Intro/outro + chapter/progress bar + Remotion thumbnail still | Coder | provisional |
| 19.7 | `VideoService` wire-up, toggle, kill switch, packaging, `check_dependencies.py` | Coder | provisional |
| 19.8 | Gate B-12 (visual sign-off + media gate) | PM | provisional |
| 19.9 | Close-out: flip default to `remotion` (only on Gate B-12 PASS); version bump | Coder | provisional |

## Evidence log

- **19.1** (2026-09-28, Coder): `docs/operations/phase19-spike-remotion.md`. ~61 s wall time
  (3 real renders) for a 2:56 B1 episode, ~166 s extrapolated for 8 min. Output correctness
  confirmed (A/V sync 0.01-0.04s, per-line timing exact, 1280x720 no-upscale). ~660 MB Node
  workspace, +575-840 MB estimated packaged-app growth. Full suite 1175/1175, ruff clean,
  `tsc --noEmit` clean, `test_video_studio_browser.py` 10/10 unchanged. Coder proposed
  **PASS**; PM independently re-verified full suite (1175 passed, 401.33s) + ruff clean +
  git-log-scoped confirmation that `app/services/video_service.py` was untouched across the
  entire Phase 19 commit range. Real-DB gap found (no 8-min B1 project with completed audio
  currently exists) -- documented, not hidden. **PM + owner (D33, 2026-09-28) accept PASS**
  with the two carry-over conditions: (1) opportunistic 8-min re-confirm once the owner
  generates one, non-blocking; (2) 19.7 must treat the Chrome Headless Shell ~270 MB as a
  hard floor. Commit sha `4dd325b`.
