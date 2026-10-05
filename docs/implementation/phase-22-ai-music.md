# Phase 22 — AI background music (ENH-016) — controlling plan

**Status:** planned 2026-10-05 (`/vp-evolve`, Add Feature, complexity L) from the brainstorm
`docs/brainstorm/session-2026-10-05.md` (owner decisions D43–D49).
**Version:** enters at 1.2.0-beta. It closes at **1.3.0-beta** if Gate B-17 passes (MINOR: a new
user-visible feature; uploaded tracks keep working).

## 0. Owner decisions

| ID | Decision |
|---|---|
| D43 | ACE-Step 1.5 (MIT; commercial use stated; licensed/royalty-free training data; <4 GB VRAM), local, in its own venv and subprocess worker under the Task 20.1 GPU lease |
| D44 | One instrumental bed per episode + intro/outro emphasis |
| D45 | The AI writes a music brief, the owner edits it, 3 previews are made, the owner picks one, then the full-length track is generated |
| D46 | Tracks go into the Music Library with a provenance record; YouTube description music credit |
| D47 | The spike decides between full-length generation and a loop with crossfades (owner listens) |
| D48 | Speech-aware ducking from line timestamps |
| D49 | Style families: lofi/chill, acoustic/piano warm, upbeat/corporate bright |

## 1. Architecture (fits the existing pattern)

- **`venv-music/`**, isolated like `venv-image/`: never in `requirements.txt`, never bundled in the
  .exe, and the worker process exit returns all VRAM.
- **`scripts/music_worker.py`:** the same line-delimited JSON protocol as `image_worker.py`
  (handshake / load / generate / unload / stats).
- **`app/services/music/`:**
  - an engine with a worker and a deterministic fake for tests;
  - a background job runner, reusing the visuals job pattern;
  - a brief writer that goes through the AI gateway.
- **Data:** an additive migration `music_tracks` with these columns:
  - id, filename, source (upload | ai), style family, brief/prompt, seed, duration, model,
    licence, app version, created at.

  Uploaded files stay as they are; the table is only provenance + listing metadata.
- **Mix:** `audio_service` gains a timestamp-driven gain envelope (D48). Remotion intro/outro get
  the music at a fuller level. The −16 LUFS master target is unchanged.

## 2. Tasks

| Task | What | Accept when |
|---|---|---|
| 22.1 | **Spike** (GPU): install ACE-Step 1.5 in `venv-music`; measure VRAM, speed and quality for the 3 style families × 2 length strategies; the owner listens. The owner also uploads one track unlisted to YouTube to check Content ID | owner picks the length strategy and confirms the quality bar; VRAM < 8 GB, leaving headroom for the lease |
| 22.2 | Music worker + engine + jobs + `music_tracks` migration + Library UI v2 (source, provenance, standalone "Generate from a brief") | tests green; a real generation lands in the library with provenance |
| 22.3 | AI music brief (gateway, validated, genre→family fallback); Step 4 "AI music" card: edit the brief → 3 previews → pick → full-length → attach to the project | tests green; real run on 1 project |
| 22.4 | Speech-aware ducking + intro/outro levels (ffmpeg and Remotion) | LUFS within ±1 dB; envelope unit-tested; real mix listened to |
| 22.5 | YouTube description credit line + provenance export | tests green |
| 22.6 | **Gate B-17**: owner listening test on 3 real episodes (one per family) | owner PASS → 1.3.0-beta, tag `die-vp-p22-complete` |

## 3. Risks

- **Python/torch compatibility** of ACE-Step 1.5 on Windows. The spike pins a working set, as
  Task 20.2 did.
- **Long-form stability vs loop seams** (D47). The spike measures both.
- **Content ID on AI music.** This is empirical (owner upload in 22.1). The provenance record is
  the fallback for disputes.
- **Download size.** The DiT + LM + VAE are likely several GB, cached under `models/music/`, which
  is gitignored like `models/image/`.
