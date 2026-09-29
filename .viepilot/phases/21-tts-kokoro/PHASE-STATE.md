# Phase 21 State — Better TTS Engine (Kokoro-first with Edge TTS fallback)

## Metadata

- **Phase:** 21
- **Slug:** `21-tts-kokoro`
- **Status:** Task 21.1 Kokoro spike accepted + **owner STOP decision 2026-09-29** ("chất lượng cực kỳ tệ ... nghe như robot trong Star Wars"). Coder diagnostic confirmed genuine ISTFT-vocoder character, not pipeline bug. **Amendment A landed**: pivot to StyleTTS 2 (owner decision). New Task 21.1b spike doc-first card ready. `venv-kokoro/` + `models/kokoro/` kept on disk as historical reference (not deleted).
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
| 21.1 | Spike: Kokoro + 12-clip listening test | Coder | **accepted + STOP** -- PM task-level 2026-09-29, sha `8441f5b`; technical viability confirmed (RTF 0.28, CPU-only, real tokens for WordBoundary, 1.51 GB footprint), owner listening STOP ("chất lượng cực kỳ tệ ... robot Star Wars"); Coder diagnostic (autocorrelation vs Kokoro's own published `af_heart_0.wav` reference: 0.198 @ 5ms vs 0.1977 @ 11ms, essentially identical) confirms genuine ISTFT-vocoder character, not pipeline bug |
| 21.1b | Spike: StyleTTS 2 + 12-clip listening test (Amendment A pivot after Kokoro STOP) | Coder | **ready** (doc-first card `tasks/task-21.1b.md`, new spike after owner pivot decision 2026-09-29) |
| 21.2 | `TTSProvider` mirroring `_synthesize_edge_tts` tuple contract (engine determined by 21.1b PASS) | Coder | provisional |
| 21.3 | TTS router refactor (engine-agnostic) | Coder | provisional |
| 21.4 | Step 4 UI per-speaker engine toggle | Coder | provisional |
| 21.5 | Gate B-13 (PM: media gate + owner listening sign-off) | PM | provisional |
| 21.6 | Close-out: combined `v1.2.0-beta` release with Phase 19.9 default flip | Coder | provisional |

## Evidence log

- **21.1** (2026-09-29, Coder): design `be94496` (PM APPROVED, subprocess-isolation
  direction) → implementation in this task's own commit (see handover message for sha).
  Real, hard finding: no published Kokoro version supports this project's own Python
  3.14 -- `kokoro==0.9.4` declares `Requires-Python <3.13,>=3.10`; the newest
  3.14-visible release, `0.7.16`, needs `numpy==1.26.4` exactly and drags
  `misaki[en] -> spacy -> thinc -> blis`, and `blis` fails to build from source on 3.14
  (no prebuilt wheel, real Cython/GIL compile error, reproduced in two independent
  isolated 3.14 venvs). Resolved via a new subprocess-isolated Python 3.11 environment
  (`venv-kokoro/`, mirroring `video-renderer/`'s Phase 19 precedent) -- confirmed working
  end-to-end. Real bug found + fixed: `huggingface_hub`/`misaki` both write raw warnings
  to stdout (not `logging`), corrupting the JSON worker protocol -- fixed via a
  stdout-isolation pattern in `kokoro_worker.py`. All 12 real clips (3 lines x 2 Kokoro
  voices + 3 lines x 2 Edge TTS voices) synthesized successfully, SHA-256-confirmed
  non-duplicate, ffprobe-validated playable audio; `spike_comparison.mp3` 57.17s
  (ffprobe-confirmed exact). Real per-word timing confirmed via Kokoro's own
  `Result.tokens` (model-derived, not estimated), maps cleanly onto the existing
  `WordBoundary` shape. Real measured footprint: `venv-kokoro/` 1.2 GB + `models/kokoro/`
  314 MB (~1.51 GB total, ~5.6x Phase 19.7's Chrome Headless Shell cost) -- stated
  explicitly in the decision proposal alongside the quality finding. Mean Kokoro RTF
  ~0.28 (CPU-only, zero VRAM use confirmed architecturally). One real wall-time anomaly
  investigated (first-ever voice use in a worker's lifetime pays a one-time lazy-load
  cost) -- not a red flag, flagged as a 21.2 pre-warm recommendation. Full Python suite
  1205/1205 unchanged (no `app/`/`tests/` touched), `ruff check .` clean on this task's
  own files. Decision proposal (PASS/SCOPE-CUT/STOP) deferred to the owner's real
  listening judgment per the card's own framing -- not pre-decided. Report:
  `docs/operations/phase21-spike-kokoro.md`.
