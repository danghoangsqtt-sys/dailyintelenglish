# Phase 20 State — AI thumbnails + consistent characters (ENH-012)

## Metadata

- **Phase:** 20
- **Slug:** `20-ai-thumbnails`
- **Status:** opened 2026-09-30. Task 20.1 is implemented and awaiting owner-machine
  verification and PM acceptance.
- **Source of this file:** the owner's Phase 20 summary, given to Coder on 2026-09-30.
  The 7-task breakdown, the reuse list and the run order below come from that summary.
  **No controlling plan (`docs/implementation/phase-20-*.md`) is in the repo yet.** If a
  PM plan exists in another session and was not pushed, the PM should push it and
  reconcile it with this file. Where they disagree, the PM plan wins.
- **Request card:** `.viepilot/requests/ENH-012.md`, with D25 (thumbnail = A then B), D26
  (local only, no paid image APIs, cartoon/3D characters per topic) and D29 (Phase 20
  comes after Remotion).
- **Ownership of this folder:** PM until handover commit, Coder after.

## Run order (owner, 2026-09-30)

Coder has one session, so the work runs in sequence:

1. Phase 21 spike (21.1b StyleTTS 2) → owner listens and decides. Blocked on a run on
   the owner's machine (see `21-tts-kokoro/tasks/task-21.1b.md`, "Owner-machine run").
2. **Task 20.1 model manager**. It is useful whatever Phase 21 decides, so it goes
   ahead while 21.1b waits for the owner-machine run.
3. Task 20.2 image spike → owner looks at real images and decides.
4. Rest of Phase 20 → Gate B-14.
5. Phase 22 (music from text). A detailed plan is written when Phase 20 is nearly done.
6. Phase 19.9 (flip the Remotion default, currently held) joins the nearest release.

## Reuse (owner's list; Coder to verify each one when its task starts)

- `speakers.avatar_image_path` column plus the image upload service (Task 1.7c). Built
  but not yet used by any project. → 20.4
- The avatar slot in Remotion's speaker chip (Task 19.4 left it ready). → 20.5
- The headline/colour layer of the current thumbnail (Task 1.8b). Only the background
  changes; the text layer stays. → 20.3

## Task status

| Task | Description | Owner | Status |
|---|---|---|---|
| 20.1 | Shared VRAM model manager (foundation) | Coder | **implemented, awaiting owner-machine verification + PM acceptance**. Design `b328fd3`, D20.1-c approved by the owner (Ollama takes the lease too). 30 new tests; 0 new failures vs baseline |
| 20.2 | Image model spike: SDXL / SDXL-Turbo / FLUX.1-schnell + IP-Adapter trial | Coder | **design committed, awaiting approval + owner Q1/Q2** (`tasks/task-20.2.md`). Key finding: both FLUX IP-Adapters are FLUX.1-dev non-commercial, so SDXL + h94 IP-Adapter is the only licence-clean path to consistent characters. The spike run needs the owner's GPU |
| 20.3 | AI thumbnail background replacing the template background (text/colour layer kept) | Coder | provisional |
| 20.4 | Per-character reference image management | Coder | provisional |
| 20.5 | Character image in the video | Coder | provisional |
| 20.6 | Gate B-14: owner reviews real images and approves | PM | provisional |
| 20.7 | Phase close-out | Coder | provisional |

## Evidence log

- **20.1** (2026-09-30, Coder): design `b328fd3`, then the implementation commit. Evidence is in the card's "Implementation" section.
