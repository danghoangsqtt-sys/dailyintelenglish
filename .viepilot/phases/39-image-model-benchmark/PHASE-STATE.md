# PHASE-STATE — Phase 39: Image model benchmark — RealVisXL vs Qwen-Image (D110–D116)

- **Status:** 39.1–39.3 done 2026-10-13 (report `docs/operations/phase39-image-benchmark.md`); owner chose per task (D118); 39.4 built 2026-10-14, Gate B-26 pending. Downloads: ~72 GB + 1.6 GB of 4-step LoRAs (owner approved). Brainstorm:
  `docs/brainstorm/session-2026-10-13-qwen-image.md`.

| Task | Description | Status |
|---|---|---|
| 39.1 | Benchmark harness (separate `.venv-qwen`, diffusers 0.41 + gguf) and prompts per task | done |
| 39.2 | Four system tasks × engines: activity illustration (generic people), scene plate (no people), thumbnail/topic picture, character shot (Alex/Lina: RealVisXL IP-Adapter vs Qwen-Image-Edit-2511) | done |
| 39.3 | Report: time (warm/cold), VRAM, defects; blind sheets for the owner to score; decision per task (D113) | done |
| 39.4 | Apply the winner per task (engine switch with RealVisXL fallback), tests, Gate B-26 | in_progress |

Engines: RealVisXL V5.0 (baseline), Qwen-Image-2512 GGUF Q4_K_S + Lightning 8-step (Apache 2.0), Qwen-Image-Edit-2511
GGUF Q4_K_S + Lightning (Apache 2.0, character shots), Qwen-Image-2.1-Turbo GGUF Q8 (**evaluation only**, research licence).

## D118 (owner, 2026-10-13) and the 39.4 plan

Choices: **Qwen-Image-2.1-Turbo** for activity illustrations, thumbnail/topic pictures and new scene plates; **Qwen-Image-Edit-2511
(4-step Lightning)** for character inserts; RealVisXL stays as the automatic fallback and for everything else (character sheets,
duo shots with ControlNet, hand repair). Qwen-Image-2512 is removed afterwards (its text encoder stays: Edit-2511 uses it).

Implementation notes (before coding):
- **One image environment:** `.venv-image` gets diffusers 0.41 + gguf + bitsandbytes + peft (SDXL verified on 0.41: 22 s, same
  as before); `.venv-qwen` is then removed. Pins in `backend/ai/image/requirements.txt`.
- **Worker** (`backend/ai/image/image_worker.py`): a new command `qwen_generate` with a list of items. Text-to-image (2.1-Turbo):
  phase 1 the 4-bit text encoder encodes every prompt and is freed, phase 2 the Q8 GGUF transformer renders on the GPU (the
  benchmark's proven path, 31 s/picture; the GGUF BF16 non-Linear fix). Reference edit (Edit-2511): one phase, 4-bit text
  encoder on the GPU, transformer streamed from RAM, 4-step Lightning (56 s). Model folders resolved from the HF cache;
  `unavailable` when a model is missing.
- **App** (`backend/ai/image/engine.py`, `pipelines.py`, `recipes.py`, `core/config.py`): settings `IMAGE_ILLUSTRATION_ENGINE`
  (`qwen21` | `realvisxl`) and `IMAGE_CHARACTER_ENGINE` (`qwen_edit` | `realvisxl`), default Qwen when its files exist;
  `engine.qwen_batch(items)` leases the GPU and runs one worker; natural-language prompts in `recipes` (D110: a few ordinary
  people); activity illustrations, scene previews and single-character inserts use it; any Qwen failure falls back to the
  RealVisXL path for the remaining items (logged). Fake engine supports the new command for tests.
- **Thumbnail topic picture:** Step 6 "Draw with local AI" draws the topic picture (2.1-Turbo, the headline on a sign) into the
  existing outside-AI picture slot (`thumbnail_service`), so composition and download are unchanged.
- **Tests:** prompt builders, engine selection and fallback, worker command validation (no GPU), thumbnail endpoint with the
  fake engine. Then a real run on the sandbox, and **Gate B-26** (owner reviews new pictures on a real episode).

## 39.4 as built (2026-10-14)

- Worker: `qwen_generate` / `qwen_installed` (`backend/ai/image/qwen_runner.py`), real GPU check: 2.1-Turbo 30 s/picture
  (9.0 GB peak), Edit-2511 57 s/picture (8.7 GB peak); local cache only (`try_to_load_from_cache`, since the snapshots are
  partial by design).
- App: `engine.qwen_batch` + `QwenUnavailable` fallback; activity illustrations, scene preview, missing plates and
  single-character inserts use Qwen by default; Step 6 topic picture. Settings `IMAGE_ILLUSTRATION_ENGINE`,
  `IMAGE_CHARACTER_ENGINE`.
- Full suite 1,697 passed. Removed: Qwen-Image-2512 GGUF + LoRAs (13.6 GB; its text encoder stays for Edit-2511) and
  `.venv-qwen` (4.8 GB; `.venv-image` now has diffusers 0.41 + gguf + bitsandbytes + peft).
- Next: restart the real app (owner OK), then **Gate B-26** on a real episode.
