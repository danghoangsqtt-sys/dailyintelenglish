# Task 21.1 — Spike: install Kokoro locally + real quality/time/RAM measurement

- **Status:** not started (doc-first card, awaiting Coder pickup)
- **Owner:** Coder
- **Priority:** P0 (blocks every other Phase 21 task card)
- **Dependency:** none (independent of Phase 19 remaining work)
- **Controlling detail:** `docs/implementation/phase-21-tts-kokoro.md` §3 "21.1"; Phase 21
  invariants 41-45; existing `_synthesize_edge_tts` shape in `app/services/tts_service.py`
  (`tuple[bytes, list[WordBoundary]]` return contract from Task 19.2)

## Goal

Prove Kokoro can synthesize this project's real B1 English podcast lines with
noticeably better voice quality than Edge TTS on owner's own machine, at a speed and
memory footprint compatible with running alongside Ollama qwen + Remotion Chrome, before
any full-implementation task card (21.2+) is written.

This is a **spike**, not a production task. Owner-side subjective listening is the
gate signal, not just numeric metrics.

## Real preflight (verified before Coder starts)

- Owner's machine: RTX 3060 12 GB, i7-12700, 32 GB RAM, Windows 11 Pro (per Phase 19.1
  environment section).
- Existing VRAM budget: ~7-8 GB for Ollama qwen (loaded when cloud-first falls to local),
  ~270 MB for Remotion Chrome Headless. **Kokoro is CPU-first per its published
  benchmarks**, so should not fight for GPU.
- Kokoro upstream: `hexgrad/Kokoro-82M` on HuggingFace, Apache 2.0. Model ~1 GB. 82M
  params. Real-time factor RTF < 1.0 on modern CPU per README (spike measures actual).
- Existing Edge TTS baseline: `_synthesize_edge_tts` at
  `app/services/tts_service.py:78-113`, returns `tuple[bytes, list[WordBoundary]]` per
  Task 19.2.

## Allowed files

- **New** `models/kokoro/` — model cache directory (gitignored via existing
  `models/**` .gitignore rule — verify). Downloaded ONCE via
  `huggingface_hub.snapshot_download`.
- **New** `scripts/spike_kokoro.py` — standalone runner: installs the `kokoro`
  pip package (into venv), downloads the model into `models/kokoro/`, synthesizes 3
  real B1 lines with 2 voices each (6 clips total), measures wall time + peak RAM +
  peak VRAM (should stay flat) + output audio duration. Also synthesizes the same 3
  lines via existing `_synthesize_edge_tts` for comparison. Saves all 12 clips as
  numbered WAV/MP3 files under `data/tmp/phase21_spike/`.
- **New** `docs/operations/phase21-spike-kokoro.md` — the spike report (see Evidence
  below for structure).
- **Modify** `requirements.txt` — add `kokoro>=<X.Y>` (spike determines exact minimum
  version compatible with the project's Python 3.14). If Kokoro isn't yet published on
  PyPI for Python 3.14, install from git URL and document the pin.
- `CHANGELOG.md` — one bullet under `[Unreleased]` after the report lands.

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `docs/implementation/`,
`video-renderer/`. `data/app.db` is `mode=ro` from Coder side (spike doesn't touch DB
at all). Prior Phase 19 reports remain immutable.

## Design decisions (Coder, doc-first — commit these under `docs(review)` before code)

The Coder writes a design section here answering each of the following, PM approves,
then code lands in a separate commit. Same pattern as Task 19.1 spike.

### D21.1-a: Kokoro Python package + version + install path

- Which pip package name (`kokoro` vs `kokoro-onnx` vs
  `kokoro-tts`)? Cite exact PyPI listing.
- Which minimum version compatible with this project's Python 3.14? (Task 19.2 already
  ran into Python 3.14 quirks — audiop-lts, etc.)
- If not on PyPI for 3.14, install from GitHub main. Document the exact URL + pin
  commit sha.
- Runtime deps: does Kokoro need `torch`? (The project already has
  `torch==2.11.0+cu128` from the abandoned OmniVoice investigation, so torch install
  cost is zero — verify Kokoro is compatible with that torch version.)

### D21.1-b: Model download path + caching

- `models/kokoro/` (matches `models/omnivoice/` precedent). Confirm
  `huggingface_hub.snapshot_download(repo_id="hexgrad/Kokoro-82M", local_dir="models/
  kokoro")` works.
- First-download size (expected ~1 GB — measure real).
- Verify `models/**` is gitignored so the download doesn't accidentally commit.

### D21.1-c: 3 test lines to synthesize

Pick 3 real lines from the demo project `b330d37f...`'s script — same content as
Phase 19 spikes, so owner can compare against Edge TTS versions they already know:
- Line 0: `"Hey Maya, are you an early bird or a night owl?"` (Alex, male, US)
- Line 5 (or similar): a longer descriptive sentence with idiom
- Line 29 (last): `"I will! Wish me luck!"` (Maya, female, US)

For each line, synthesize:
- Kokoro voice A (male US, closest match to "Alex" style)
- Kokoro voice B (female US, closest match to "Maya" style)
- Edge TTS existing baseline (male US Aria / male US Guy)

= 6 Kokoro clips + 6 Edge TTS clips = 12 files.

### D21.1-d: WordBoundary equivalent

- Confirm Kokoro emits per-token phoneme timings natively. Cite the exact API method +
  return shape.
- If it does: spike verifies the shape maps cleanly to the `WordBoundary` NamedTuple
  Task 19.2 defined (`text: str`, `offset_sec: float`, `duration_sec: float`).
- If it doesn't (Kokoro returns different granularity): document what shape it does
  emit + propose adaptation in 21.2 design. NOT a spike blocker.

### D21.1-e: Measurement methodology

Report exact numbers (not adjectives) for:
- **Wall time per line** (mean + stdev over the 3 lines, per voice, per engine)
- **Real-time factor RTF** (`wall_seconds / audio_duration_seconds`); < 1.0 = faster
  than real-time (streamable)
- **Peak RAM** during synthesis, process-scoped (subprocess measurement, don't count
  the whole machine)
- **Peak VRAM** during synthesis (should be near zero if CPU-only per README)
- **Model load time** (one-time cost, separate from per-line synthesis)
- **Model file size on disk** (`du -sh models/kokoro/`)

### D21.1-f: Owner-side listening comparison protocol

The subjective gate matters here more than in Phase 19's mostly-visual spikes.

- Save all 12 WAV files with self-describing filenames: `kokoro_alex_line0.wav`,
  `edge_alex_line0.wav`, etc.
- Sample 1 combined MP3 (concatenated with 1s silence between clips) as a quick
  listening file: `spike_comparison.mp3`.
- The spike report §7 explicitly asks owner to listen to at least the combined MP3
  and answer: "Is Kokoro noticeably better than Edge TTS on emotion/prosody, on par,
  or worse?" Owner's answer is the gate signal.

### D21.1-g: Decision proposal

The spike report §8 must include one paragraph: PASS / SCOPE-CUT (which of 21.2-21.6
to drop or defer, e.g. skip per-speaker engine toggle if Kokoro is universally better)
/ STOP (if Kokoro is same-or-worse quality and no reason to add complexity).

**If STOP**: propose either StyleTTS 2 (GPU 4-6 GB, top open-source) or F5-TTS as
alternative. Document real-numbers reasoning.

## Verification

- All 12 clips render successfully; no crashes.
- `spike_comparison.mp3` exists and plays.
- Full suite: **1205/1205** (this task adds no tests). `ruff check .` clean.
- No `app/`, `frontend/`, `tests/`, `video-renderer/`, `data/app.db` touched.
- Owner can play `spike_comparison.mp3` and answer the listening question.

## Evidence (spike report structure)

The `docs/operations/phase21-spike-kokoro.md` deliverable is the gate signal. Structure:

1. **Environment** (Python, torch, kokoro package version, Kokoro model version + digest,
   RAM, CPU, GPU, OS)
2. **Install footprint** (model on disk, node_modules-equivalent for Kokoro's own deps,
   torch already-installed baseline)
3. **3 test lines** (verbatim text + speaker attribution from `b330d37f...`)
4. **Kokoro measurements** (per-line wall time, RTF, RAM, VRAM, output duration)
5. **Edge TTS baseline measurements** (same lines, same metrics for comparison)
6. **Side-by-side comparison table** (rows = lines × voices, cols = Kokoro vs Edge TTS
   for each metric)
7. **Owner listening protocol** (path to `spike_comparison.mp3`, listening question,
   owner's answer verbatim)
8. **Decision proposal** (PASS / SCOPE-CUT / STOP + reasoning)

## Definition of done

- All allowed files created, no disallowed files touched.
- Design commit lands **before** the implementation commit.
- 12 real clips on disk under `data/tmp/phase21_spike/`.
- `spike_comparison.mp3` on disk.
- Spike report on disk with every "Evidence" item filled from real measurement.
- Handover message to PM includes: report path, RTF number, owner-question link, PASS/
  SCOPE-CUT/STOP proposal.
- Owner listens + answers the listening question. PM records answer as gate signal.
