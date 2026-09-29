# Phase 20 State — AI Visual Generation (thumbnails + consistent characters)

## Metadata

- **Phase:** 20
- **Slug:** `20-ai-visuals`
- **Status:** planning (task 20.1 doc-first card ready; **starts after Phase 21 spike
  resolves** — Coder is single-session)
- **Planned:** 2026-09-29 (owner priority statement: natural voice → thumbnail + character
  images → music from text)
- **Controlling plan:** `docs/implementation/phase-20-ai-visuals.md`
- **Authorization:** owner decision D26 (2026-09-24, ENH-012: local AI thumbnails on the
  RTX 3060, cartoon/3D characters per topic) extended by owner's 2026-09-29 requirement
  that the same character stays recognizable across every image in an episode. Owner chose
  **IP-Adapter** for consistency and **shared VRAM model manager built first**.
- **Ownership of this folder:** PM until the handover commit, Coder after.

## Preflight

- Phase 19 at 7/9 + Gate B-12 PARTIAL (Remotion accepted, 19.9 default flip held).
- Phase 21 TTS in progress (StyleTTS 2 spike after Kokoro STOP).
- Full suite baseline **1205/1205**, ruff clean.
- Existing thumbnail path: 5 Pillow templates + Gemini headline/palette fill
  (Task 1.8a/1.8b). Working, shipped, and stays as the fallback (invariant 47).
- Existing avatar path: `speakers.avatar_image_path` column + upload/serve/delete service
  (Task 1.7c). Currently unused by any real project — **Task 20.4 reuses this rather than
  building a parallel path**, and Task 19.4's speaker chip already has an avatar render
  slot waiting for it.
- Real VRAM budget on the owner's RTX 3060 (12288 MiB total), measured by Coder in Task
  21.1b D21.1b-e with real `nvidia-smi`: **3916 MiB free with Ollama qwen3.5:9b loaded**,
  10286 MiB free at idle. Any image model above ~4 GB cannot coexist with qwen.

## Task status

| Task | Description | Owner | Status |
|---|---|---|---|
| 20.1 | Shared GPU model manager (load / free-VRAM check / unload, used by TTS + images + music) | Coder | **ready** (doc-first card `tasks/task-20.1.md`) |
| 20.2 | Image model spike (SDXL vs SDXL-Turbo vs FLUX.1-schnell) + IP-Adapter consistency demo | Coder | provisional |
| 20.3 | Thumbnail AI path behind opt-in toggle, Pillow templates as fallback | Coder | provisional |
| 20.4 | Character reference management (reuse `speakers.avatar_image_path` from Task 1.7c) | Coder | provisional |
| 20.5 | In-video character images (populate Task 19.4's existing avatar slot) | Coder | provisional |
| 20.6 | Gate B-14 (owner visual sign-off on thumbnails + character consistency) | PM | provisional |
| 20.7 | Close-out | Coder | provisional |

## Evidence log

(Coder and PM append per task once execution starts.)
