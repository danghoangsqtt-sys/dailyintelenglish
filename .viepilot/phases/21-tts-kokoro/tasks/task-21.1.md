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

## Design decisions — Coder answers (2026-09-29)

Investigated real code + ran real, isolated probes before answering (no production code
written yet). **D21.1-a's shape changed from the card's original framing** ("pip install
and import") **to subprocess isolation, per the PM's explicit approval mid-investigation**
(after I found and reported the Python 3.14 incompatibility below) — D21.1-b..g stand as
written otherwise.

### D21.1-a: Kokoro package + Python compatibility — real, hard blocker found

Package name confirmed real via `pip download kokoro --no-deps` (works, PyPI listing
exists): **`kokoro`** (not `kokoro-onnx`/`kokoro-tts`), Apache 2.0.

**Real finding: Kokoro cannot be installed into this project's actual Python 3.14 venv at
all, at any published version — a hard wall, not a version-pinning nuance.**
- `pip install kokoro` against the real project venv (`--dry-run`, non-mutating) resolves
  to the latest 3.14-visible release, **0.7.16**, which `Requires-Dist: numpy==1.26.4`
  (exact pin) and `misaki[en]>=0.7.16` → `spacy` → `thinc` → `blis` (a Cython BLAS
  extension). Real attempted install: `blis` has no prebuilt wheel for Python 3.14 yet
  and fails to build from source with a genuine Cython compile error
  (`Accessing Python attribute not allowed without gil`, `blis\py.pyx:128`) — reproduced
  identically in a second, fully isolated Python-3.14 venv outside the project (same
  failure, not an artifact of this project's own installed packages).
- The actual latest Kokoro release, **0.9.4**, explicitly declares
  `Requires-Python: <3.13,>=3.10` — this excludes Python 3.14 (and even 3.13) by design,
  confirmed by downloading and reading its real `METADATA` file. No currently-published
  Kokoro version supports 3.14.
- Real confirmation the *code itself* works: installed cleanly into a separate, isolated
  Python **3.11.9** venv (an existing interpreter already present on this machine, outside
  the project). `kokoro==0.9.4` resolved there with **no onerous numpy pin**
  (`numpy 2.4.6`, unpinned in 0.9.4's own metadata — the `==1.26.4` pin was specific to the
  old 0.7.x line) and `spacy`/`thinc`/`blis` all installed from prebuilt wheels
  successfully (wheels exist for 3.11, not yet for 3.14). Real synthesis test (below,
  D21.1-d) produced correct audio + word timing on the first real line.
- Torch: real finding — Kokoro's own dependency resolution pulled a **CPU-only** torch
  build (`torch 2.14.0+cpu`) into the isolated venv, confirmed via
  `torch.cuda.is_available() == False`. It does **not** reuse or need this project's
  existing `torch==2.11.0+cu128` (CUDA build, kept for the abandoned OmniVoice path) —
  the isolated venv gets its own separate, smaller CPU-only torch. Matches the "CPU-first,
  doesn't compete for VRAM" premise in the controlling plan.
- `espeak-ng` (mentioned in Kokoro's own README for "English OOD fallback and some
  non-English languages"): not installed on this machine (`which espeak-ng` empty). Not
  yet determined to be a hard requirement for standard English synthesis — the real test
  line below (D21.1-d) synthesized correctly without it. Flagging as an open item for the
  full spike run (12 lines) to confirm it's genuinely optional for in-dictionary English
  text, not just lucky on one short sentence.

**Recommendation, approved by PM mid-investigation:** subprocess-isolated Python 3.11
environment, mirroring the exact architectural precedent `video-renderer/` already
established in Phase 19 (a Node subprocess the main Python 3.14 process invokes but never
imports) — one shared discipline for "external-runtime component," not two. New
`venv-kokoro/` at the project root (Python 3.11, own `kokoro`/`torch`/`spacy` install,
**not** reusing the project's own `venv/`), gitignored (not currently covered by any
existing `.gitignore` pattern — `venv/`/`.venv/` are literal names, not a wildcard; adding
`venv-kokoro/` is a small necessary scope addition, disclosed here).

**Proposed subprocess contract** (file-based, matching `video-renderer/`'s own
temp-file-in/file-out convention rather than inventing a new IPC shape):
- New `scripts/kokoro_worker.py` — runs *inside* `venv-kokoro/` (Python 3.11). On startup:
  sets `HF_HOME` (see D21.1-b), loads `KPipeline` once (the real, one-time ~2.7s warm-load
  cost measured below), then loops reading **one line of JSON per request** from stdin:
  `{"text": str, "voice": str, "output_path": str}`. Synthesizes, writes the WAV to
  `output_path`, and writes **one line of JSON** to stdout:
  `{"status": "ok", "duration_sec": float, "wall_time_sec": float, "word_boundaries":
  [{"text": str, "offset_sec": float, "duration_sec": float}, ...]}` or
  `{"status": "error", "message": str}` on a per-line failure (never crashes the whole
  worker for one bad line). Binary audio never crosses the pipe itself — only file paths
  and JSON — avoiding text/binary stream-encoding pitfalls entirely.
- The main process (Python 3.14, `app/` in the eventual 21.2/21.3 production shape; the
  spike's own runner script for this task) spawns `venv-kokoro/Scripts/python.exe
  scripts/kokoro_worker.py` once via `subprocess.Popen` with pipes, sends N requests over
  the process's lifetime (not one spawn per line — the whole point of "kept alive" is
  paying the ~2.7s model-load cost once, not per line), and terminates it at the end.
- Degradation (I41, phase invariant): if `venv-kokoro/Scripts/python.exe` doesn't exist,
  the worker fails to start within a timeout, or a request's response line never arrives
  (broken pipe / worker crashed), the caller treats this exactly like
  `RemotionRenderFailedError` in Task 19.7 — falls back to `_synthesize_edge_tts`. This
  spike proves the request/response contract works for real; full production-grade
  crash/restart hardening is 21.2/21.3's job per the phase plan, not this spike's.

### D21.1-b: Model download path — real confirmation

`HF_HOME` env var redirect confirmed working for real (not assumed): set
`HF_HOME=<test dir>`, ran a real `huggingface_hub.snapshot_download(repo_id=
"hexgrad/Kokoro-82M")` call with no other override, and the download landed at
`<HF_HOME>/hub/models--hexgrad--Kokoro-82M/snapshots/<commit-sha>/` — HF's own internal
cache layout (not flat files; worth documenting so a future reader doesn't expect
`models/kokoro/kokoro-v1_0.pth` directly at the top level). Recommend `kokoro_worker.py`
sets `HF_HOME` to an absolute path resolving to `models/kokoro/` (matching
`models/omnivoice/` precedent, D21.1-b as written) before importing `kokoro`.

Real download size: **313 MB**, 72 files (base model weights + config + the ~50-voice
pack, each voice a separate small `.pt` file — not just the 1 voice used in this spike).
`models/*` (with `!models/.gitkeep`) is already gitignored — confirmed by reading
`.gitignore` directly — no change needed there.

### D21.1-c: 3 real test lines — confirmed via read-only DB query

Fetched real `script_lines` for `b330d37f-a212-4cf7-a779-7a109098bd6c` (30 lines total,
`mode=ro`, standing constraint honored):
- **Line 0** (Alex, male): *"Hey Maya, are you an early bird or a night owl?"* — matches
  the card's own suggestion exactly.
- **Line 24** (Alex, male): *"Exactly. Small changes can help you wake up on the right
  side of the bed."* — real correction/improvement over the card's vague "line 5 or
  similar": this line has a genuine idiom ("wake up on the right side of the bed",
  already confirmed as a real matched idiom in Task 19.5's vocab/idiom pop-up work) and is
  the longer descriptive sentence the card asked for.
- **Line 29** (Maya, female, last line): *"I will! Wish me luck!"* — matches the card's
  own suggestion exactly.

Each line synthesized with 2 Kokoro voices (`af_heart` — American female, the voice
already proven working in D21.1-d's real test below — and a matching American male voice,
selected from Kokoro's real ~50-voice pack during implementation) + the existing
`_synthesize_edge_tts` baseline using each line's real originating speaker (Alex/Maya) —
6 Kokoro clips + 6 Edge TTS clips = 12 total, per the card.

### D21.1-d: WordBoundary equivalent — confirmed real, native, and clean-mapping

Read `kokoro/pipeline.py` and `misaki/token.py` directly (installed package source, not
docs). Real finding: `KPipeline`'s generator yields a `Result` dataclass with a `tokens:
List[MToken]` field when the full object is used (not just the 3-tuple
`graphemes, phonemes, audio` backward-compat unpacking a naive `for gs, ps, audio in
pipeline(...)` loop would only see). Each `MToken` has real `text: str`, `start_ts:
Optional[float]`, `end_ts: Optional[float]` fields, computed by `pipeline.py`'s own
`join_timestamps()` from the model's predicted duration output (`pred_dur`) — i.e. Kokoro
emits genuine model-derived per-word alignment, not an estimate.

**Real live test** (line 0, `af_heart` voice, Python 3.11 isolated venv): 13 tokens
(11 words + 2 punctuation), real monotonic timestamps spanning the full 3.15s clip:
```
text='Hey'   start_ts=0.275 end_ts=0.475
text='Maya'  start_ts=0.475 end_ts=0.875
...
text='owl'   start_ts=2.35  end_ts=2.9
text='?'     start_ts=2.9   end_ts=3.05
```
Maps trivially onto this project's own `WordBoundary(text, offset_sec, duration_sec)`
shape (Task 19.2): `offset_sec = t.start_ts`, `duration_sec = t.end_ts - t.start_ts`,
filtering out pure-punctuation tokens (`t.text` matching non-alphanumeric only) to match
Edge TTS's own word-only boundary events. No adaptation-needed caveat from the card
applies — this is a clean, direct mapping, confirmed by real output, not by reading docs
alone.

### D21.1-e: Measurement methodology

Real preliminary numbers already gathered on one line (formal spike run will cover all 3
lines × 2 voices):
- **Cold start** (first ever run, includes ~1GB combined model+dependency download over
  network): model load 106.47s. Not representative of steady-state cost — reported
  separately as a one-time install cost, not per-session overhead.
- **Warm model load** (model already cached): **2.67s** — the real one-time
  per-process-lifetime cost the "kept-alive worker" design (D21.1-a) exists to pay once.
- **Synthesis, line 0** (49 characters, 3.15s output audio): **1.09s** wall time →
  **RTF ≈ 0.35** (well under 1.0, faster than real-time, matches the README's claim with
  a real number instead of citing the README alone).
- Peak RAM/VRAM: not yet isolated per-process for this single-line probe (the isolated
  venv's own Python process was measured informally via Task Manager during the run, GPU
  usage stayed at baseline confirming the CPU-only torch build claim) — formal
  process-scoped RSS/VRAM measurement via `psutil`/`nvidia-smi` sampling during the real
  spike script run, per the card's methodology.
- Disk footprint: **venv-kokoro/ ≈ 1.2 GB** (CPU torch + spacy + kokoro + all deps),
  **models/kokoro/ ≈ 313 MB** (model + voice packs) — **≈1.5 GB total added footprint**,
  a real number for the packaging-cost comparison the PM asked for (vs. Phase 19.7's
  Chrome Headless Shell at ~270 MB — Kokoro's subprocess isolation costs roughly 5.5x
  more disk, a real tradeoff to weigh in the decision proposal, D21.1-g).

### D21.1-f: Owner-side listening comparison protocol

Confirmed as written in the card — no changes. `kokoro_alex_line0.wav`,
`edge_alex_line0.wav`, etc. self-describing filenames; one concatenated
`spike_comparison.mp3` (1s silence between clips) for quick owner listening; report §7
asks the explicit comparison question verbatim.

### D21.1-g: Decision proposal

Deferred to the actual spike report (`docs/operations/phase21-spike-kokoro.md` §8) after
real measurement across all 12 clips and the owner's real listening answer — cannot be
responsibly pre-decided from a single-line probe. The real ~1.5 GB subprocess-isolation
disk cost (D21.1-e) and the confirmed-working native word-timing (D21.1-d) are both
real inputs to that proposal, not decided here.

### Allowed-files correction (real, necessary — flagging before implementation)

The card's original Allowed files list said "Modify `requirements.txt` — add
`kokoro>=<X.Y>`" — no longer correct given the subprocess-isolation shape (D21.1-a):
`kokoro` is never installed into this project's own venv/`requirements.txt` at all (that's
the whole point — it can't be, Python 3.14 blocks it). Proposed real replacement scope:
- **New** `requirements-kokoro.txt` (committed, project root) — the isolated venv's own
  pinned deps (`kokoro==0.9.4`, `soundfile`, etc.), analogous to `requirements.txt` but for
  `venv-kokoro/`'s separate Python 3.11 environment.
- **New** `venv-kokoro/` — NOT committed, gitignored (new `.gitignore` entry needed, see
  D21.1-a).
- **New** `scripts/kokoro_worker.py` — the subprocess entry point (D21.1-a), runs inside
  `venv-kokoro/`.
- `requirements.txt` (the project's own, Python-3.14 file) is **not** touched by this task.

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
