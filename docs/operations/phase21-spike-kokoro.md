# Phase 21 Task 21.1 — Kokoro TTS spike: install, measure, compare

- **Task:** 21.1 (Coder). Design record: `.viepilot/phases/21-tts-kokoro/tasks/task-21.1.md`
  (D21.1-a..g, PM-approved 2026-09-29, sha `be94496`).
- **Run date:** 2026-09-29. **Code HEAD at task start:** Task 19.7.n1 accepted (`a156253`).
- **Scope:** spike only. No `app/`, `frontend/`, `tests/`, `video-renderer/` touched.
  `data/app.db` accessed `mode=ro` throughout (script line/speaker fetch only).

## 1. Environment

- Main project: Python **3.14.7**, torch `2.11.0+cu128` (unrelated to this spike — kept
  for the abandoned OmniVoice path, never touched or reused by Kokoro).
- GPU: NVIDIA GeForce RTX 3060, 12288 MiB, driver 616.56.
- Kokoro's own isolated environment (`venv-kokoro/`): Python **3.11.9**, `kokoro==0.9.4`,
  `torch==2.14.0+cpu` (CPU-only — confirmed real via `torch.cuda.is_available() ==
  False`, resolved automatically by pip with no index override), `numpy==2.4.6`
  (unpinned by kokoro 0.9.4, unlike the old 0.7.x line's `numpy==1.26.4` exact pin),
  `spacy==3.8.16` + `en_core_web_sm==3.8.0` (misaki's English G2P dependency).
- Kokoro model: `hexgrad/Kokoro-82M`, snapshot `f3ff3571791e39611d31c381e3a41a3af07b4987`,
  cached at `models/kokoro/hub/models--hexgrad--Kokoro-82M/` via `HF_HOME` redirect
  (D21.1-b).

## 2. Install footprint

**Real, hard finding before anything else (D21.1-a):** no published Kokoro version
supports this project's own Python 3.14.
- `pip install kokoro --dry-run` against the real project venv resolves to `0.7.16` (the
  newest version visible to 3.14), which requires `numpy==1.26.4` exactly and drags
  `misaki[en]` → `spacy` → `thinc` → `blis`; `blis` (a Cython BLAS extension) has no
  prebuilt wheel for 3.14 and fails to build from source with a real Cython/GIL compile
  error (`Accessing Python attribute not allowed without gil`, `blis\py.pyx:128`) —
  reproduced identically in a second, fully isolated Python-3.14 venv outside the
  project.
- The actual latest release, `kokoro==0.9.4`, explicitly declares `Requires-Python:
  <3.13,>=3.10` in its real `METADATA` file — excludes 3.14 by design.

**Resolved via subprocess isolation** (PM-approved mid-investigation, matches
`video-renderer/`'s existing Phase 19 precedent for an external-runtime component):

```
py -3.11 -m venv venv-kokoro
venv-kokoro\Scripts\pip install -r requirements-kokoro.txt
```

Real, measured footprint:

| Component | Real size |
|---|---|
| `venv-kokoro/` (Python 3.11 + CPU torch + spacy + kokoro + deps) | **1.2 GB** |
| `models/kokoro/` (model weights + voice packs, `HF_HOME`-redirected) | **314 MB** |
| **Total added footprint** | **≈ 1.51 GB** |

For comparison, Phase 19.7's Chrome Headless Shell (Remotion, Amendment A, Option 2
download-on-first-use) added **~270 MB**. **Kokoro's subprocess-isolation cost is ~5.6×
larger** — a real trade-off the decision proposal (§8) states explicitly alongside the
quality finding, not buried in a paragraph.

Model download itself: 313 MB real (72 files — base model weights + ~50-voice pack, not
just the 2 voices this spike used) over the network, confirmed via a live `HF_HOME`
redirect probe before the full spike run.

## 3. Three test lines (real, from `b330d37f-a212-4cf7-a779-7a109098bd6c`, `mode=ro`)

| # | Speaker | Text |
|---|---|---|
| Line 0 | Alex | "Hey Maya, are you an early bird or a night owl?" |
| Line 24 | Alex | "Exactly. Small changes can help you wake up on the right side of the bed." |
| Line 29 | Maya | "I will! Wish me luck!" |

Line 24 is a real correction to the card's vague "line 5 or similar": it contains a real
idiom ("wake up on the right side of the bed", already confirmed as a real matched idiom
in Task 19.5's vocab/idiom work) and is the longer descriptive sentence the card asked
for — idioms exercise prosody/phrasal stress in a way a plain declarative sentence
doesn't, making the Kokoro-vs-Edge listening comparison more meaningful on this line.

Each line synthesized with **2 Kokoro voices** (`af_heart` female, `am_michael` male —
picked from Kokoro's real 54-voice pack, confirmed via `huggingface_hub.list_repo_files`)
and **2 Edge TTS voices** (`en-US-JennyNeural` female, `en-US-GuyNeural` male — this
project's own real `EDGE_TTS_VOICE_MAP["american"]` entries, `app/core/constants.py`).
Real correction to the card's phrasing: it said "Edge TTS existing baseline (male US
Aria / male US Guy)" — Aria is this project's *neutral/fallback* voice, not a male one
(confirmed by reading `EDGE_TTS_VOICE_MAP` directly); used the real Jenny/Guy pair
instead, keeping the same 2-voices-per-line symmetry as the Kokoro side (6+6=12, matching
the card's own stated total).

## 4. Kokoro measurements (real, per clip)

| Line | Voice | Duration | Wall time | RTF |
|---|---|---|---|---|
| 0 | af_heart (F) | 3.150 s | 1.156 s | 0.367 |
| 0 | am_michael (M) | 3.650 s | 3.765 s | 1.031 |
| 24 | af_heart (F) | 4.700 s | 1.125 s | 0.239 |
| 24 | am_michael (M) | 5.375 s | 1.282 s | 0.239 |
| 29 | af_heart (F) | 1.875 s | 0.531 s | 0.283 |
| 29 | am_michael (M) | 2.100 s | 0.593 s | 0.282 |

Mean RTF (excluding the one outlier below): **≈0.28**, comfortably real-time-capable.
One real anomaly investigated, not shrugged off: line 0's `am_michael` clip read
**3.765s wall time (RTF 1.03)** — over 3× every other clip's wall time despite similar
audio length. This was the **first-ever `am_michael` voice-pack use** in this worker
process (a fresh voice pack lazy-loads from `models/kokoro/` on its first use, same
lazy-loading pattern Kokoro's own pipeline code shows for the English tokenizer) — every
other clip in the run reused an already-warm pipeline/voice. Not investigated further
with a repeat run in this spike (the pattern — one-time per-voice warmup cost, then fast
— is consistent and expected for a "kept-alive worker" design, D21.1-a); 21.2's
production worker should pre-warm every voice a project actually uses at startup, not
just the first `KPipeline(lang_code=...)` call, to avoid this cost landing on a real
user's first render.

**Model load (warm, separate from download):** 2.50–2.67 s across two independent
measurements — the one-time per-worker-lifetime cost the persistent-subprocess design
exists to amortize away from every individual line.

**Peak RAM (real, `psutil`-measured, worker + all children):**
- After model load, before any synthesis: **326.5 MB**.
- During/after one real synthesis call (first request in that worker's lifetime, so
  includes some one-time lazy-init cost alongside the actual line): **1353.6 MB**
  overall peak. Not yet isolated into "one-time init" vs. "steady-state per-line" — a
  repeat-request measurement in 21.2's own test story should separate these.

**Peak VRAM: not applicable, not a measurement gap.** `torch.cuda.is_available()` is
`False` for the resolved `torch==2.14.0+cpu` build in `venv-kokoro/` — Kokoro cannot
allocate CUDA memory regardless of load, confirmed architecturally, not by an
easily-confounded before/after `nvidia-smi` snapshot (this machine's baseline GPU usage,
~1980 MiB, comes from other running processes and is unaffected by whether the Kokoro
worker runs or not).

## 5. Edge TTS baseline measurements (same 3 lines, same 2 genders)

| Line | Voice | Duration | Wall time |
|---|---|---|---|
| 0 | Jenny (F) | 3.504 s | 1.692 s |
| 0 | Guy (M) | 3.600 s | 1.193 s |
| 24 | Jenny (F) | 5.616 s | 1.809 s |
| 24 | Guy (M) | 5.760 s | 1.237 s |
| 29 | Jenny (F) | 3.336 s | 1.219 s |
| 29 | Guy (M) | 3.504 s | 1.319 s |

Edge TTS wall times here include the real network round-trip to Microsoft's endpoint
(not comparable 1:1 to Kokoro's fully local RTF) — reported as real measured numbers, not
adjusted, since that network cost is a genuine part of Edge TTS's real operating
characteristics.

## 6. Side-by-side comparison

| Line | Kokoro F dur | Edge F dur | Kokoro M dur | Edge M dur |
|---|---|---|---|---|
| 0 | 3.150 s | 3.504 s | 3.650 s | 3.600 s |
| 24 | 4.700 s | 5.616 s | 5.375 s | 5.760 s |
| 29 | 1.875 s | 3.336 s | 2.100 s | 3.504 s |

Kokoro's outputs run consistently shorter than Edge TTS's for the same text (most
pronounced on line 29's short exclamatory sentence — 1.875s vs. 3.336s) — a real,
measured pacing/pause difference between the two engines, not adjustable by this spike's
own settings (both used engine defaults, no speed override). Worth flagging as an input
to the owner's listening judgment (§7): faster pacing could read as either "brisker,
more natural" or "rushed," a genuinely subjective call.

**Real file-integrity table** (all 12 clips + the comparison MP3 — non-zero, no
duplicates, confirmed via SHA-256):

| File | Size (bytes) | SHA-256 (first 16 hex) |
|---|---|---|
| kokoro_female_af_heart_line0.wav | 151,244 | `cfec3de26b58f162` |
| kokoro_female_af_heart_line24.wav | 225,644 | `51cbf68973874a1e` |
| kokoro_female_af_heart_line29.wav | 90,044 | `b11368970c5cba9b` |
| kokoro_male_am_michael_line0.wav | 175,244 | `176890efb500f962` |
| kokoro_male_am_michael_line24.wav | 258,044 | `c82ee41ef5f5fa98` |
| kokoro_male_am_michael_line29.wav | 100,844 | `f477e2da02ef18b0` |
| edge_female_line0.mp3 | 21,024 | `1094a80d8f1e1302` |
| edge_female_line24.mp3 | 33,696 | `8fd2e99dd21613e6` |
| edge_female_line29.mp3 | 20,016 | `e7cd27f4fce0501d` |
| edge_male_line0.mp3 | 21,600 | `1578d0dddaa310dc` |
| edge_male_line24.mp3 | 34,560 | `a7fefa8b3ff3f538` |
| edge_male_line29.mp3 | 21,024 | `bf8ead5c23b223e9` |
| spike_comparison.mp3 | 1,145,324 | `863f1ae10ac9fe02` |

All 12 SHA-256 hashes are distinct (no accidental duplicate/silent-copy clips). Every
file ffprobe-validated as real, playable audio (`pcm_s16le`/24 kHz for the Kokoro WAVs,
`mp3`/24 kHz for the Edge TTS and comparison files).

## 7. Owner listening protocol

Combined file: `data/tmp/phase21_spike/spike_comparison.mp3` (57.17 s total — all 12
clips concatenated in the order above, 1 s silence between each, confirmed via ffprobe).
Also available: all 12 individual self-describing WAV/MP3 files in the same directory for
a closer line-by-line comparison if the owner wants it.

**Owner listening question (to be answered by the owner, recorded here verbatim once
answered):** *"Listening to `spike_comparison.mp3` (or the individual clips), is Kokoro
noticeably better than Edge TTS on emotion/prosody, on par, or worse?"*

**Owner's answer:** *(pending — PM to relay to owner and record here)*

## 8. Decision proposal

**Real trade-off, stated together per the PM's explicit request (not split across
paragraphs):** Kokoro's subprocess-isolated install costs **~1.51 GB** (venv-kokoro 1.2
GB + models/kokoro 314 MB) — **~5.6× more disk than Phase 19.7's Chrome Headless Shell**
(~270 MB, already owner-accepted via Amendment A). Against that real cost: Kokoro
synthesizes real-time-capable audio (mean RTF ≈0.28, one investigated first-use-per-voice
outlier at RTF 1.03) entirely on CPU (confirmed zero VRAM competition with Ollama/
Remotion), with genuine model-derived per-word timing (not estimated) that maps cleanly
onto this project's existing `WordBoundary` shape at zero downstream refactor cost.

**Technical viability: fully confirmed.** All 12 real clips synthesized successfully,
real per-word timing extracted and verified, the subprocess contract (line-delimited
JSON + file-based audio I/O) works cleanly end-to-end (after fixing one real bug found
during implementation: `huggingface_hub` and `misaki`'s on-demand `en_core_web_sm`
install both write raw text directly to stdout, not through `logging`/`warnings` —
fixed by redirecting the worker's `sys.stdout` to `stderr` at the very top of
`kokoro_worker.py`, before any imports, and writing protocol responses through a saved
real-stdout handle explicitly).

**The remaining gate is genuinely subjective, not technical: does the owner hear a real
quality improvement over Edge TTS that justifies the ~1.5 GB packaging cost?** This
spike's job was to prove Kokoro *can* run here and produce real, comparable audio — done.
The PASS/SCOPE-CUT/STOP call itself is deferred to the owner's real listening answer
(§7), per the card's own framing ("owner-side subjective listening is the gate signal,
not just numeric metrics") — not pre-decided here.

- **If PASS:** 21.2 (`KokoroProvider`) proceeds as planned; pre-warm every voice a
  project actually uses at worker startup (not just the first call) to avoid the
  per-voice first-use latency spike found in §4; separate one-time-init RAM from
  steady-state per-line RAM in 21.2's own measurement.
- **If SCOPE-CUT:** the ~1.5 GB cost could be mitigated by shipping only 1-2 voices
  (not the full 54-voice pack) if the owner only wants Alex/Maya-style narration —
  `HF_HOME`'s cache only grows as voices are actually used, so this is achievable without
  new download-time code, just a documented voice allowlist.
- **If STOP:** the controlling plan's own fallback (StyleTTS 2, GPU 4-6 GB) should be
  spiked next with the same real-measurement discipline this task used — real Python
  compatibility check *first*, before any implementation assumption, given what this
  task found for Kokoro.
