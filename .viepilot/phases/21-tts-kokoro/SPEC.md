# Phase 21 Specification — Better TTS Engine (Kokoro-first with Edge TTS fallback)

The controlling contract is `docs/implementation/phase-21-tts-kokoro.md`. Authority:
owner Gate B-12 feedback 2026-09-29 ("giọng nghe không tự nhiên, thiếu cảm xúc").
Runs in parallel with Phase 19.9 hold — combined `v1.2.0-beta` release ships both.

## Goal

Modern open-source TTS (Kokoro, 82M, Apache 2.0, near-ElevenLabs quality, real-time on
CPU) is the primary voice engine. Edge TTS becomes automatic fallback. A no-Kokoro
install behaves exactly like today.

## Required gates

- **Doc-first.** Every task's design is PM-approved before code (SYSTEM-RULES.md AR-06).
- **Spike-first (Task 21.1).** No 21.2+ task card is written until 21.1 spike report is
  on disk with real Kokoro-vs-EdgeTTS listening comparison + PM's PASS/SCOPE-CUT/STOP.
- **Fallback invariant (I41).** Kokoro failure never fails a synthesis — degrades to
  Edge TTS. Fallback rate reported.
- **Audio gate.** Loudness (-16 LUFS ±1 dB), silence gaps, A/V drift stay pinned. Gate
  B-13 measures on real episodes.
- **Model safety.** Kokoro Apache 2.0; local-only cache; no cloud calls.

## Tasks (planned, order fixed by spike outcome)

| Task | Description | Owner | Status |
|---|---|---|---|
| 21.1 | **Spike:** install Kokoro + real synthesize 3 test lines + measure quality/time/RAM + honest listening comparison. Report `docs/operations/phase21-spike-kokoro.md`. | Coder | ready (doc-first card) |
| 21.2 | `KokoroProvider` (mirroring `_synthesize_edge_tts` shape, tuple return with WordBoundary) | Coder | provisional |
| 21.3 | TTS router refactor (engine-agnostic dispatch, mirror `ai/router.py` from Phase 18) | Coder | provisional |
| 21.4 | Step 4 UI per-speaker engine toggle | Coder | provisional |
| 21.5 | Gate B-13 (media gate + owner listening sign-off) | PM | provisional |
| 21.6 | Close-out: flip default + combined `v1.2.0-beta` release with Phase 19.9 | Coder | provisional |

## Session partition

As in Phase 16 §6 / Phase 18 §Session partition. Coder owns this folder after handover
commit. PM runs Gate B-13.

## Deliverables at phase close

- Working `KokoroProvider` with Edge TTS fallback verified
- Per-speaker engine toggle in Step 4 UI
- Gate B-13 report accepted by owner
- Combined `v1.2.0-beta` release with Phase 19.9 default flip (Remotion + Kokoro both)
- Tags `die-vp-p21-complete` + `die-vp-p19-complete` on same commit
