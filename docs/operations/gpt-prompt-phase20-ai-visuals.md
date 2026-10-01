# Implementation prompt — Phase 20 AI Visuals (for the owner's GPT coding agent)

The owner pastes the block below into the coding agent. `PINNED_SHA` is filled in by the
Claude session in its chat reply. The prompt is deliberately strict, so the implementer
and the reviewer never diverge.

```
ROLE
You are the IMPLEMENTER for Phase 20 "AI Visuals" of the Daily Intel English Studio repo.
A separate reviewer (the Claude Code session, acting as PM) reviews your work; you never
self-approve (project rule AR-06). The owner relays messages between you.

REPO AND BASE
- Repository: danghoangsqtt-sys/dailyintelenglish
- Base commit: PINNED_SHA (on branch claude/admiring-knuth-r1d8vc)
- Create your branch from exactly that commit:  feature/phase20-ai-visuals
  (git fetch origin; git switch -c feature/phase20-ai-visuals PINNED_SHA)
- Push only that branch. Never push to main or claude/admiring-knuth-r1d8vc. Never force-push,
  rebase, or rewrite history.

SOURCE OF TRUTH (read fully before writing code)
1. docs/implementation/phase-20-ai-visuals-feature-spec.md   <- THE spec. Follow it exactly.
2. Reference implementations to PORT (copy the logic; do not import from scripts/ in app code):
   scripts/spike_character_v6.py (person_pose, draw_people, half_masks, shot geometry, card/duo flow)
   scripts/spike_character_v5.py (hand_boxes, hand_mask, paste_hand, hand repair loop)
   scripts/spike_character_v2.py (draw_pose_pixels, _UPPER_BODY, _KEYS, silhouette_mask)
   scripts/spike_images.py (_WorkerClient subprocess protocol)
   scripts/image_worker.py (the GPU worker the app must drive; its JSON commands)
3. Existing conventions: app/services/thumbnail_service.py, video_renderer_remotion.py,
   ai_worker.py (in-process loop pattern), app/db/database.py (migrations), app/api/*.py
   (ok() envelope, AppError subclasses), frontend/static/js/api.js + step5_video.js
   (vanilla JS patterns), tests/conftest.py (fixtures, live_server for Playwright).
The scripts/spike_* files are READ-ONLY references. Do not edit them.

WORK ORDER (spec section 11) -- do the tasks strictly in order, one at a time:
  20.3 foundation -> 20.4 library backend -> 20.5 library UI -> 20.6 project visuals
  -> 20.7 Remotion + thumbnail -> 20.8 smoke script + docs
For EACH task:
  a) Implement exactly the spec scope for that task. Additive changes only.
  b) Write the tests the spec section 10 lists for that task (all tests use DIE_IMAGE_ENGINE=fake;
     no GPU needed).
  c) Run, and paste the exact final summary lines into your handover:
       ruff check app tests scripts/smoke_ai_visuals.py      (only the paths you touched + new ones)
       python -m pytest -q                                    (FULL suite, not a subset)
       cd video-renderer && npx tsc --noEmit && npx vitest run   (whenever video-renderer/ changed)
     The full suite must have NO NEW failures versus the base commit. If the base already has
     failures in your environment, record them once (before your first change) and compare.
  d) Commit with explicit paths only (NEVER `git add .` or `git add -A`), message:
       feat(visuals): Task 20.X <short summary>
     Do not commit data/, models/, venv*/, node_modules/, *.log, or any MP4/PNG output.
  e) Create/append .viepilot/phases/20-ai-visuals/tasks/task-20.X.md with a "Handover" section:
       - files added/changed (paths)
       - what was implemented, mapped to spec sections
       - tests added (names) + the verbatim test summary lines from step c
       - deviations from the spec (should be none; each one with a reason)
       - open questions for the PM
  f) git push -u origin feature/phase20-ai-visuals
Then continue with the next task. Do not wait between tasks unless a STOP condition hits.

STOP CONDITIONS (stop, push what is done, write the question in the current handover)
- The spec is contradictory, impossible, or would require changing a section-2 number,
  a prompt string, an existing table shape, or an existing endpoint contract.
- A required change falls outside the files the spec's section 3 lists (other than small,
  necessary wiring such as app/main.py router/lifespan registration, project_service's
  artifact category list, app/core/config.py settings, frontend/pages/dashboard.html link,
  CHANGELOG.md, and the new docs) -- ask first.
- The full test suite gains a failure you cannot fix within the task's scope.

NON-NEGOTIABLE RULES (spec section 12, repeated)
1. Never put a studio/franchise/artist/real-person name in any prompt, default, fixture or UI hint.
2. Never change the section-2 recipe numbers or prompt wording. Prompts must stay <= 75 CLIP tokens
   (spec 2.3 table); never lengthen a template.
3. Additive only: no change to existing table shapes or existing endpoint contracts; ffmpeg path and
   template thumbnails behave byte-identically when a project has no visuals.
4. No new Python dependency in the main venv; no new npm dependency.
5. All GPU work only via get_gpu_manager().lease(...) + the scripts/image_worker.py subprocess
   (venv-image). The app process never imports torch/diffusers/transformers.
6. Blocking I/O and subprocess calls via asyncio.to_thread.
7. Content endpoints validate that served paths resolve under their own DATA_DIR sub-tree.
8. Match existing style (ruff clean, ok() envelopes, AppError subclasses, read_/write_transaction,
   vanilla JS Api client). UI text in English.

GPU SMOKE (task 20.8 only)
- Always run: python scripts/smoke_ai_visuals.py --fake   (must pass)
- Only if this machine has an NVIDIA GPU, venv-image\ exists, and no app is running on port 8000:
  also run the real smoke per docs/operations/owner-runbook-gate-b14.md section "smoke"; otherwise
  write "real smoke: not run (reason)". Never install anything for it.

FINAL REPORT (print exactly this shape when 20.8 is pushed, or when you stop)
PHASE 20 AI VISUALS -- IMPLEMENTER REPORT
base: PINNED_SHA
branch: feature/phase20-ai-visuals @ <head sha>
tasks: 20.3 <done|stopped>, 20.4 <...>, 20.5 <...>, 20.6 <...>, 20.7 <...>, 20.8 <...>
tests: pytest <passed>/<failed> (base had <n> pre-existing failures: <names or none>); vitest <n>; tsc <clean|errors>; ruff <clean|errors>
smoke: fake <pass|fail>; real <pass|fail|not run (reason)>
deviations: <none | list with task ids>
open questions: <none | list>
```
