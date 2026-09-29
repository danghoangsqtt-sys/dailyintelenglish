# Phase 21 State — Better TTS Engine (Kokoro-first with Edge TTS fallback)

## Metadata

- **Phase:** 21
- **Slug:** `21-tts-kokoro`
- **Status:** planning (task 21.1 spike doc-first card ready; awaiting Coder pickup)
- **Planned:** 2026-09-29 (owner Gate B-12 feedback: "giọng nghe không tự nhiên, thiếu
  cảm xúc" — real usability blocker for shipping Remotion default in Phase 19.9)
- **Controlling plan:** `docs/implementation/phase-21-tts-kokoro.md`
- **Authorization:** owner request 2026-09-29 (feature upgrade selection after Gate B-12
  visual sign-off round).
- **Ownership of this folder:** PM until handover commit, Coder after.

## Preflight

- Phase 18 closed (`v1.1.0-beta`, cloud-first AI).
- Phase 19 at 7/9 tasks + Gate B-12 media gate 6/6 PASS but owner PARTIAL decision:
  Remotion visual accepted, Edge TTS voice quality NOT — 19.9 close-out held pending
  Phase 21 ship. Combined `v1.2.0-beta` release when both flip.
- Full suite baseline **1205/1205**, ruff clean.
- Existing `app/services/tts_service.py` has `_synthesize_edge_tts` returning
  `tuple[bytes, list[WordBoundary]]` (Task 19.2 contract). Phase 21 mirrors this shape
  for Kokoro so downstream consumers (AudioService, karaoke composition) work unchanged.
- Owner's RTX 3060 (12 GB VRAM) shared with Ollama qwen (cloud-first fallback, ~7-8 GB
  loaded) and Remotion Chrome Headless (~270 MB). Kokoro's 82M-param model runs
  **real-time on CPU alone** — does NOT compete for GPU. Preflight confirmed via public
  Kokoro README (spike verifies live).

## Task status

| Task | Description | Owner | Status |
|---|---|---|---|
| 21.1 | Spike: install Kokoro + real synth 3 test lines + measure quality/time/RAM + honest Kokoro-vs-EdgeTTS listening comparison. Report `docs/operations/phase21-spike-kokoro.md`. | Coder | **ready** (doc-first card `tasks/task-21.1.md`) |
| 21.2 | `KokoroProvider` mirroring `_synthesize_edge_tts` tuple contract | Coder | provisional |
| 21.3 | TTS router refactor (engine-agnostic) | Coder | provisional |
| 21.4 | Step 4 UI per-speaker engine toggle | Coder | provisional |
| 21.5 | Gate B-13 (PM: media gate + owner listening sign-off) | PM | provisional |
| 21.6 | Close-out: combined `v1.2.0-beta` release with Phase 19.9 default flip | Coder | provisional |

## Evidence log

(Coder and PM append per task once execution starts.)
