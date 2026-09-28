# Phase 19 Specification — Animated Learning Videos with Remotion (ENH-013)

The controlling contract is `docs/implementation/phase-19-remotion.md`. Authority: owner
decision **D29** (2026-09-24, `docs/brainstorm/session-2026-09-24.md`) and follow-on **D32**
(2026-09-28, this phase's planning selections — spike-first, `video-renderer/` subdir). The
phase **starts after Phase 18 closes** (Phase 18 closed 2026-09-26, `v1.1.0-beta`).

## Goal

Replace today's static-background + burned-in line-level subtitles (ffmpeg, "Level 2") with a
Remotion-rendered composition that adds **word-level karaoke captions**, an **active-speaker
indicator**, **vocabulary/idiom pop-up cards** timed to the containing line, and
**intro/outro + a chapter/progress bar + a Remotion-rendered thumbnail still**. The ffmpeg
path stays as the tested fallback: any Remotion failure still produces today's video.

## Constraints and risks (from ENH-013)

- **Render time is unproven.** An 8-min 1080p30 video is ~14,400 frames. Local render may take
  several to 10+ min. The **spike (Task 19.1) must measure this on the owner's machine before
  any full-implementation task card is written.**
- **Packaging weight.** Node.js + headless Chromium add roughly 150–300 MB to the packaged
  `.exe`, and TypeScript/React enters the repo. D32 selects a `video-renderer/` subdirectory
  invoked as a subprocess from FastAPI — the Python and Node stacks stay isolated.
- **Licence.** Remotion is free for individuals and organisations of up to 3 employees. The
  owner is solo. A company licence is required if the org grows beyond 3 employees. The
  licence must be re-checked on any structural change and noted in the release notes.
- **Per-word timing does not exist yet.** Today the app stores only line-level timing
  (`AudioService.mix_project` measured per-line start/end seconds, Task 1.6b). Word-level
  karaoke needs per-word timestamps from Edge TTS `WordBoundary` events, plus schema and
  migration work. Captured under **Task 19.2** (opened only after the spike passes).
- **Two-language repo.** Ruff/pytest cover Python; the `video-renderer/` workspace adds its
  own `package.json`, TypeScript config and Node-side tests. `check_dependencies.py` and CI
  will be extended in the wiring task (19.7) — not in the spike.

## Required gates

- **Doc-first.** Every task's design is PM-approved before code (SYSTEM-RULES.md AR-06).
- **Spike-first (Task 19.1).** No implementation task card for 19.2+ is written until
  Task 19.1's measurement report is on disk and PM has decided PASS / SCOPE-CUT / STOP.
- **Fallback invariant (I36, new to this phase).** The Remotion renderer is opt-in at every
  layer that survives past the spike: a request-time flag, a settings toggle, and a hard kill
  switch. A Remotion failure never fails a video — it degrades to the existing ffmpeg path
  and is reported (fallback-rate, same pattern as Phase 18 §I32).
- **Media gate.** Duration, A/V sync and codec checks (already in the media gate framework,
  Phase 14/15) still pass on Remotion output, plus the owner's own visual sign-off on real
  episodes. This becomes Gate B-12 once tasks 19.3–19.6 exist.
- **Key/data safety.** No episode text or audio is sent off-machine by the renderer. Remotion
  runs headless Chromium locally. Same invariants 31/33/35 as Phase 18 apply verbatim to any
  new settings, if the phase adds any.

## Tasks (planned, order fixed by the spike outcome)

Only **19.1** is a real, doc-first task card in `tasks/`. Tasks **19.2–19.9** are provisional
placeholders — the controlling plan may drop or reorder them once the spike report exists.

| Task | Description | Owner | Status |
|---|---|---|---|
| 19.1 | **Spike:** `video-renderer/` scaffold + minimal Remotion composition (background + line-level captions matching today's ffmpeg output, no word-timing yet) rendered for one real 8-min B1 episode from the current DB. Measure render time, packaging footprint, output correctness. Report `docs/operations/phase19-spike-remotion.md`. | Coder | not started (doc-first card ready) |
| 19.2 | Edge TTS `WordBoundary` capture + per-word timestamps storage + additive migration | Coder | provisional |
| 19.3 | Word-level karaoke captions composition (`@remotion/captions`, `createTikTokStyleCaptions`) | Coder | provisional |
| 19.4 | Active-speaker indicator (name/avatar highlight per line) | Coder | provisional |
| 19.5 | Vocabulary/idiom pop-up cards timed to the containing line (from the Learning pack) | Coder | provisional |
| 19.6 | Intro/outro + chapter/progress bar + Remotion-rendered thumbnail still (feeds ENH-012/Phase 20) | Coder | provisional |
| 19.7 | Wire the renderer into `VideoService` behind a request flag + settings toggle + `DIE_VIDEO_RENDERER=remotion\|ffmpeg` kill switch; fallback-rate readout; packaging + `check_dependencies.py` updates | Coder | provisional |
| 19.8 | Gate B-12 (visual sign-off + media gate) on real episodes | PM | provisional |
| 19.9 | Close-out: flip default to `remotion` **only if** Gate B-12 accepted; version bump; CHANGELOG | Coder | provisional |

## Session partition

As in Phase 16 §6 / Phase 18 §Session partition. The Coder owns this folder after the
handover commit. PM runs the spike measurement on the owner's own machine only if the owner
authorises — otherwise the Coder runs it and PM independently re-runs the render command
against the same episode.

## Deliverables at phase close

- A working `video-renderer/` workspace (Node/TypeScript/React/Remotion) invoked by
  `VideoService` as a subprocess when the toggle is on.
- A Remotion composition covering all four ENH-013 scope items.
- The ffmpeg path unchanged and still the default until D-decision at close-out.
- Gate B-12 report accepted by owner.
- `docs/operations/phase19-spike-remotion.md`, `docs/operations/phase19-gate-b12.md`.
- `docs/implementation/phase-19-remotion.md` amended with every measured outcome.
