# Phase 21 Implementation Plan — Better TTS Engine (Kokoro-first with Edge TTS fallback)

**Status:** OPEN 2026-09-29 (planning; task 21.1 spike doc-first ready).
**Controlling plan.** PM, 2026-09-29. **Runs in parallel with Phase 19.9 hold** (Phase 19
close-out waits until Phase 21 ships, so `v1.2.0-beta` single version bump captures both).
**Authority:** owner Gate B-12 feedback (2026-09-29): "giọng nghe không tự nhiên, thiếu
cảm xúc" — real-user finding that Edge TTS voice quality is a blocker for shipping
Remotion default.
**Evidence baseline:** Gate B-12 media gate 6/6 PASS
(`docs/operations/gate-b12-evidence/gate-b12-runs.json`), Remotion visual composition
accepted; only TTS voice quality gates 19.9 default flip.

## 1. Goal

Replace Edge TTS neural voices (Microsoft's, limited prosody/emotion) with a modern
open-source TTS engine, keeping Edge TTS as automatic fallback for resilience.

**PM recommends Kokoro** (`hexgrad/Kokoro-82M`, Apache 2.0, 82M params, ~1 GB model,
real-time on CPU, near-ElevenLabs quality) as primary. Reasons:
- Does NOT compete for GPU with Ollama qwen (cloud-first fallback) or Remotion Chrome
  Headless — Kokoro runs real-time on CPU alone
- Apache 2.0 = safe commercial use, matches owner's non-paid preference
- Small footprint (~1 GB) fits packaged `.exe` bundling if desired later
- Native English (matches learner podcast use case)

**Alternative** if Kokoro proves insufficient at spike stage: StyleTTS 2 (research-grade,
GPU 4-6 GB, top open-source quality). Documented as fallback recommendation in spike
report.

## 2. Invariants (in addition to Phases 13–19)

41. **Fallback is always available.** Kokoro missing/failing/timeout → Edge TTS runs
    within its own budget. A no-Kokoro install behaves exactly like today's Edge-TTS-only.
42. **Kill switch.** `DIE_TTS_ENGINE=edge_tts` (or unset) forces Edge TTS regardless of
    per-speaker choice. Tested.
43. **Thresholds unchanged.** All audio mix thresholds (loudness -16 LUFS, silence gaps
    300/500 ms, A/V drift ≤1s in downstream video) stay pinned. This phase changes *who*
    speaks, never *what passes* the audio/media gate.
44. **Licence.** Kokoro is Apache 2.0. Re-verified at every phase gate. If a future
    Kokoro version changes licence, revert to Edge TTS default.
45. **Model local-only.** Kokoro runs offline post-download. Model cached at
    `models/kokoro/`, gitignored. No API keys, no cloud calls, no data leaves machine.

## 3. Tasks

Order: **21.1 (spike, Coder) → 21.2 (KokoroProvider, Coder) → 21.3 (TTS router refactor,
Coder) → 21.4 (Step 4 UI toggle, Coder) → 21.5 (Gate B-13, PM) → 21.6 (close-out, Coder)
→ then Phase 19.9 close-out (Coder, single `v1.2.0-beta` bump).**

### 21.1 — Spike: install Kokoro + measure quality/time/RAM (Coder, P0)

**See:** `.viepilot/phases/21-tts-kokoro/tasks/task-21.1.md` (doc-first card, fully
expanded).

**Deliverable:** `docs/operations/phase21-spike-kokoro.md` — real measurement on owner's
machine + PASS / SCOPE-CUT / STOP proposal + honest owner-side listening comparison
sample (3 Kokoro clips + 3 Edge TTS clips of the same 3 script lines, owner listens and
judges).

### 21.2 — `KokoroProvider` (Coder, provisional, opens on 21.1 PASS)

New `app/services/tts/kokoro_provider.py` mirroring `_synthesize_edge_tts` shape:
- `synthesize(text: str, voice: str, speed: float) -> tuple[bytes, list[WordBoundary]]`
- Same tuple return contract Task 19.2 established for Edge TTS
- Retry-once-on-empty-audio (mirror `EDGE_TTS_MAX_ATTEMPTS = 2`)
- Configuration errors (model missing) fail fast → router falls back to Edge TTS
- WordBoundary emission from Kokoro's own phoneme timings (Kokoro exposes per-token
  timing natively — spike confirms exact API)

### 21.3 — TTS router refactor (Coder, provisional)

Refactor `tts_service.py` to engine-agnostic dispatch (mirror `app/services/ai/router.py`
from Phase 18):
- New `TTS_ENGINE_ORDER: list[str]` from env (default `kokoro,edge_tts`)
- Per-engine circuit breaker + timeout budget
- Fallback rate readout on `GET /api/tts/health`
- Existing `_synthesize_edge_tts` stays as fallback engine, unchanged

### 21.4 — Step 4 UI per-speaker engine toggle (Coder, provisional)

- Add "Voice engine" dropdown per speaker card: `Kokoro (recommended)` / `Edge TTS
  (fallback)`
- Default to Kokoro if `check_dependencies` reports available; Edge TTS if not
- Persist via existing per-speaker PATCH pattern (Task 1.6c's
  `PATCH /api/projects/{id}/speakers/{speaker_id}`)
- Voice list per engine (Kokoro has ~50 voices, Edge TTS has 30 — different pools)

### 21.5 — Gate B-13: media gate + owner listening sign-off (PM)

Real end-to-end test on ≥3 real episodes:
- Full pipeline: script → Kokoro synth → audio mix → video (Remotion path)
- Media gate: loudness (-16 LUFS ±1 dB), silence gaps, A/V drift, codec — same
  thresholds as Gate B-11/B-12
- Owner listens to ≥1 full episode end-to-end and judges "shippable quality"
- Fallback invariant I41 verified (rename Kokoro model away → Edge TTS runs)

Report: `docs/operations/phase21-gate-b13.md`.

### 21.6 — Close-out (Coder)

- Flip `DIE_TTS_ENGINE` default from `edge_tts` to `kokoro` (only on Gate B-13 PASS)
- Version bump to `1.2.0-beta` **combined with Phase 19.9 flip in the same release**
- CHANGELOG entry
- Tags: `die-vp-p19-complete`, `die-vp-p21-complete`, `v1.2.0-beta`

### Phase 19.9 dependency

Phase 19.9 (flip `DIE_VIDEO_RENDERER=remotion` default + version bump) **holds** until
Phase 21 close-out. Owner's Gate B-12 PARTIAL decision explicitly deferred 19.9 pending
TTS quality upgrade — flipping Remotion default while voice quality is still the
complaint would ship 2 UX issues (rough visual UX + rough voice). Combining both into
one `v1.2.0-beta` release makes the version bump meaningful.

## 4. Session partition

Same as Phase 16 §6 / Phase 18 §Session partition. PM plans + reviews + gate. Coder
implements. Live channel `SendMessage`. Git as source of truth. Coder standby extends
into Phase 21 without gap.

## 5. Version

Enters at `1.1.0-beta`. Closes at **`1.2.0-beta`** iff Gate B-13 PASS AND Phase 19.9
flips default. Any FAIL closes each phase separately at accepted subset.

## 6. Amendments

### Amendment A — 2026-09-29: Kokoro STOP → pivot to StyleTTS 2

Task 21.1 spike report (`docs/operations/phase21-spike-kokoro.md`, sha `8441f5b`)
established technical viability for Kokoro (12 real clips + full measurement) but
owner's listening decision (2026-09-29) was **STOP**:

> *"chất lượng cực kỳ tệ, và có rất nhiều echo tiếng vang trong giọng nói nghe như robot
> đang nói chuyện trong phim star war vậy"*

Coder diagnostic proved genuine Kokoro character (autocorrelation 0.198 @ 5ms reference
vs. 0.1977 @ 11ms our output — essentially identical to Kokoro's own published sample;
Kokoro's ISTFT vocoder `istftnet.py` has known metallic/buzzy tendency). No code fix
possible. Kokoro path closed as STOP; `venv-kokoro/` + `models/kokoro/` left on disk as
historical reference.

**Pivot direction (owner decision 2026-09-29): StyleTTS 2** (research-grade, MIT
license, ~1 GB model, GPU 4-6 GB VRAM). Documented in §1 of this plan as fallback
alternative — now the primary.

**Key new design question this pivot surfaces (vs. Kokoro's CPU-only):** GPU sharing
with Ollama qwen (7-8 GB VRAM when cloud fallback fires). RTX 3060 12 GB total leaves
4-5 GB free with qwen loaded. StyleTTS 2 needs 4-6 GB — tight. Task 21.1b design must
propose a load-on-demand or free-memory-check strategy (see D21.1b-e).

**Task shape:**
- New `.viepilot/phases/21-tts-kokoro/tasks/task-21.1b.md` doc-first card written.
- Same 12-clip spike + comparison MP3 pattern (Line 0, Line 24 idiom, Line 29 — same
  as 21.1 for direct A/B).
- Same PASS/SCOPE-CUT/STOP owner-listening gate.
- If PASS: Task 21.2 re-opens with StyleTTS 2 provider instead of Kokoro.
- If STOP again: Phase 21 closes wontfix; Phase 19.9 flips Remotion default alone at
  `v1.2.0-beta` (accept Edge TTS voice ceiling as-is).

**Phase name stays `21-tts-kokoro`** for git-history continuity even though scope has
pivoted. Anyone reading the SPEC.md/PHASE-STATE.md sees the STOP + pivot recorded
explicitly.
