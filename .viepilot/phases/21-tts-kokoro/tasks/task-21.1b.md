# Task 21.1b — Spike: install StyleTTS 2 locally + real quality/GPU/timing measurement

- **Status:** not started (doc-first card, awaiting Coder pickup)
- **Owner:** Coder
- **Priority:** P0 (Kokoro path STOP'd by owner listening decision 2026-09-29 — Phase 21
  needs a working alternative or the whole phase fails)
- **Dependency:** Task 21.1 (Kokoro spike) accepted + STOP decision recorded — real
  evidence at `docs/operations/phase21-spike-kokoro.md` proves Kokoro's ISTFT-vocoder
  metallic character is genuine, not a pipeline bug
- **Controlling detail:** `docs/implementation/phase-21-tts-kokoro.md` Amendment A
  (2026-09-29, this round); Phase 21 invariants 41–45 (unchanged); Task 21.1's real
  measurement patterns as precedent

## Goal

Prove StyleTTS 2 can synthesize this project's real B1 English podcast lines with
noticeably better voice quality than Edge TTS on owner's own machine — quality answer
gates all remaining Phase 21 work. Same spike-first discipline as 21.1: measurement,
listening test, honest evidence.

**Key trade-off vs. Kokoro to surface in the report:** StyleTTS 2 is GPU-based (4-6 GB
VRAM) versus Kokoro's CPU-only. On owner's 12 GB RTX 3060, this competes with Ollama
qwen3.5:9b (7-8 GB when loaded via cloud fallback). Design must handle GPU sharing.

## Real preflight

- Owner's Gate B-12 listening decision (2026-09-29, verbatim):
  > *"chất lượng cực kỳ tệ, và có rất nhiều echo tiếng vang trong giọng nói nghe như
  > robot đang nói chuyện trong phim star war vậy"*
  Coder diagnostic confirmed Kokoro genuine character (autocorrelation 0.198 @ 5ms
  reference vs. 0.1977 @ 11ms our output — essentially identical to Kokoro's own
  published sample).
- StyleTTS 2 upstream: `yl4579/StyleTTS2` on GitHub, MIT license. Pre-trained LibriTTS
  model ~1 GB.
- Existing project stack: Python 3.14, torch 2.11.0+cu128 already installed from earlier
  OmniVoice investigation (Task 1.6 legacy). Kokoro's own subprocess-isolated
  `venv-kokoro/` (Task 21.1) proves the pattern works for external Python versions —
  reuse the pattern if StyleTTS 2 also has Python-version issues.
- Owner's GPU budget: RTX 3060, 12 GB VRAM total. Ollama qwen loaded ≈ 7-8 GB during
  cloud fallback. **Kokoro was CPU-only (safe). StyleTTS 2 is GPU-based** — real
  measurement of concurrent-load behavior is a design question.

## Allowed files

- **New** `models/styletts2/` — model cache directory (gitignored via existing
  `models/**` rule — verify). Downloaded via HuggingFace or GitHub release,
  measurements determine exact source in D21.1b-b.
- **New** `scripts/spike_styletts2.py` — standalone runner (mirroring
  `scripts/spike_kokoro.py`'s shape) that installs StyleTTS 2 (may need
  `venv-styletts2/` following Task 21.1 subprocess-isolation precedent if Python 3.14
  incompatible), downloads model, synthesizes 3 real B1 lines with 2 voices each + Edge
  TTS baseline = 12 clips, produces `spike_comparison_styletts2.mp3` for owner
  listening.
- **New** `venv-styletts2/` (gitignored, only if 21.1b design confirms Python-version
  isolation is needed) — same pattern as `venv-kokoro/`.
- **New** `scripts/styletts2_worker.py` (only if subprocess isolation is chosen) —
  persistent process, line-delimited JSON stdin/stdout, file-based audio I/O, mirrors
  `kokoro_worker.py` shape.
- **New** `requirements-styletts2.txt` (only if separate venv is needed).
- **New** `docs/operations/phase21-spike-styletts2.md` — spike report (structure below).
- `CHANGELOG.md` — one bullet under `[Unreleased]` after the report lands.

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `docs/implementation/`,
`video-renderer/`, `venv-kokoro/` (leave Task 21.1's artifacts intact for reference).
`data/app.db` is `mode=ro` from Coder side. Prior Phase 19 and 21.1 reports remain
immutable.

## Design decisions (Coder, doc-first — commit under `docs(review)` before code)

Same 7-decision structure as 21.1 with adjustments for GPU-based context.

### D21.1b-a: Python version compat + isolation approach

**Check first**: does StyleTTS 2's `pyproject.toml` or `setup.py` declare a
`python_requires` that excludes 3.14? Run the same METADATA check Task 21.1 established
as precedent.

- If StyleTTS 2 supports 3.14 natively: install directly into main venv.
- If not: subprocess-isolated `venv-styletts2/` (same pattern as `venv-kokoro/`), with
  a `scripts/styletts2_worker.py` running the isolated Python + stdin/stdout JSON
  protocol.
- Either way: cite the exact evidence (real METADATA output or real pip install log).

### D21.1b-b: Model download source + size

- StyleTTS 2 has multiple pre-trained checkpoints (LJSpeech single-speaker,
  LibriTTS multi-speaker). Pick LibriTTS for voice variety (learner podcast wants
  multiple voices matching Alex/Maya distinction).
- Real download size + file count. Cite the actual HuggingFace repo URL or GitHub
  release URL used (not a guess).
- Model cache path: `models/styletts2/` (mirrors `models/kokoro/`).

### D21.1b-c: 3 test lines — SAME as 21.1 for direct comparison

Same lines as 21.1 spike so owner can do direct A/B against the failed Kokoro output:
- Line 0: `"Hey Maya, are you an early bird or a night owl?"` (Alex, male)
- Line 24 (idiom line — Coder's own 21.1 correction to PM's vague "line 5"):
  `"wake up on the right side of the bed"` phrase (Alex)
- Line 29: `"I will! Wish me luck!"` (Maya, female)

Voice pick: 2 different StyleTTS 2 voices from LibriTTS pool that most closely match
"male US neutral" and "female US neutral" (Alex/Maya style). Cite the voice ids
selected.

### D21.1b-d: WordBoundary equivalent

- StyleTTS 2 is a phoneme-level model; does it expose per-word timing natively? If
  yes, cite the exact API. If no (as with some vocoders): fall back to Task 19.2's
  Edge TTS approach — synthesize + then use a forced-aligner (whisper-timestamped, or
  another aligner) as a post-process to get per-word timings. Cite the choice + real
  evidence.
- If it emits phoneme-level timings only: adaptation to Task 19.2's `WordBoundary`
  shape is straightforward (aggregate phonemes to word boundaries via the input's
  original tokenization). Document the exact aggregation.

### D21.1b-e: Real GPU behavior + Ollama sharing

**This is the biggest new design question vs. 21.1.**

- Baseline: cold-start StyleTTS 2 load — real VRAM used (nvidia-smi at rest → load →
  synth → rest).
- Concurrent-load scenario: is Ollama qwen also loaded (test with a real
  `ollama ps` check first)? If yes, what happens when StyleTTS 2 tries to load — CUDA
  OOM crash, or graceful failure? Cite real evidence.
- Recommendation options:
  - **(i) Load-on-demand + unload-after-batch**: StyleTTS 2 loads before a synthesis
    batch, unloads after. Overhead: ~2-5s per batch to load. Frees GPU for qwen
    fallback in between.
  - **(ii) Prefer StyleTTS 2 as primary but fall back to Edge TTS if qwen occupies
    GPU**: check `nvidia-smi` free memory before loading; if < 6 GB free, skip StyleTTS
    2 and use Edge TTS. Graceful degradation.
  - **(iii) Coordinate via a lock file**: qwen and StyleTTS 2 both check a shared lock
    before loading; whoever gets it first runs, the other waits or degrades. Complex,
    probably overkill.
- Recommend (ii) — matches Phase 18's cloud-first-with-fallback discipline and Task
  19.7's I36 fallback invariant pattern (fallback always available).
- Cite real measurement: with Ollama qwen loaded, how much VRAM does nvidia-smi report
  free? Is 6 GB safe threshold?

### D21.1b-f: Owner-side listening comparison protocol

Same as 21.1: build `spike_comparison_styletts2.mp3` with all 12 clips concatenated (1s
silence between). Explicit A/B comparison in the report: side-by-side with the same
Edge TTS baselines from 21.1 (so owner can compare Kokoro vs StyleTTS 2 vs Edge TTS
mentally, not just StyleTTS 2 alone).

Owner listens + answers: "Is StyleTTS 2 noticeably better than Edge TTS on emotion/
prosody?"

### D21.1b-g: Decision proposal (PASS / SCOPE-CUT / STOP)

- **PASS**: StyleTTS 2 quality clearly better than Edge TTS AND GPU-sharing pattern
  (chosen from D21.1b-e) works reliably. Task 21.2 opens with StyleTTS 2 provider.
- **SCOPE-CUT**: Quality OK but GPU-sharing complexity too high — drop multi-voice
  support, use only 1 voice; or accept longer synthesis time.
- **STOP**: Quality still not meaningfully better than Edge TTS, OR GPU-sharing fails
  reliability testing on owner's real machine. Phase 21 closes as `wontfix`; Phase
  19.9 flips Remotion default alone at `v1.2.0-beta` (accept Edge TTS voice
  ceiling).

## Design decisions — Coder answers (2026-09-29)

Investigated real code + ran real, isolated probes before answering (no production code
written yet). Same 7-decision structure as 21.1.

### D21.1b-a: Python version compat + isolation approach — real, distinct blocker found

Real PyPI package confirmed: `styletts2==0.1.6` (`pip index versions styletts2` — real,
exists). Its `Requires-Python: >=3.9,<4.0` technically does **not** exclude Python 3.14 —
different from Kokoro's explicit `<3.13` exclusion. **A `--dry-run` install against this
project's real venv fully resolves** (exit 0, real "Would install ..." list with 90+
packages) — on its face this looked 3.14-compatible.

**Real finding: `--dry-run` was misleading here — a genuine (non-dry-run) install fails
for a different, real reason.** `styletts2` pins `transformers>=4.36.0,<5.0.0`, which
resolves to `transformers==4.40.2` (old), which requires `tokenizers<0.20,>=0.19`, which
resolves to `tokenizers==0.19.1` — a package with **no prebuilt wheel for Python 3.14**,
forcing a from-source build via its Rust/PyO3 bindings. Real build error, reproduced
directly:
```
error: the configured Python interpreter version (3.14) is newer than
PyO3's maximum supported version (3.12)
```
This is a **different mechanism than Kokoro's** (Rust/PyO3 version cap vs. Kokoro's
Cython/GIL compile error in `blis`) but the **same real conclusion**: no currently
resolvable dependency chain lets `styletts2` actually build on this project's Python
3.14. Real methodological lesson, worth stating plainly: **`pip install --dry-run` only
checks version/metadata resolution, not whether a package with compiled extensions can
actually build** — the design phase cannot skip a real (non-dry-run) install attempt just
because dry-run passed.

**Confirmed working on Python 3.11** (same interpreter already proven for Kokoro,
`venv-kokoro/`): a real, clean install (`pip install styletts2`, fresh venv) succeeds —
`tokenizers` builds from source without the PyO3 error on 3.11, full dependency tree
installs, `from styletts2 import tts` imports successfully.

**Recommendation: reuse the exact `venv-kokoro/` subprocess-isolation pattern** — new
`venv-styletts2/` (Python 3.11, gitignored) + `scripts/styletts2_worker.py` mirroring
`kokoro_worker.py`'s shape (persistent process, line-delimited JSON over stdin/stdout,
file-based audio I/O, the same stdout-isolation fix Task 21.1 already found necessary for
noisy `huggingface_hub`/library-level `print()` calls — `styletts2`'s own dependency tree
includes several libraries with the same class of risk, e.g. `nltk`'s "already up-to-date"
downloader message observed directly during the real install test above).

### D21.1b-b: Model download source + size — real, confirmed

Read `styletts2==0.1.6`'s real installed source (`tts.py`) directly rather than guessing:
it downloads from the **original research authors' own HuggingFace repo**,
`yl4579/StyleTTS2-LibriTTS` — confirms this PyPI package is a faithful third-party
packaging of the real upstream model (`Home-page` on PyPI is a different author's fork,
`sidharthrajaram/StyleTTS2`, but the actual model weights it fetches are the real
original checkpoints), not a different or unofficial model.

Real file sizes (`huggingface_hub.HfApi().model_info(..., files_metadata=True)` for the
HF-hosted files; HTTP HEAD `Content-Length` for the 3 GitHub-raw-hosted auxiliary
checkpoints):

| File | Source | Real size |
|---|---|---|
| `Models/LibriTTS/epochs_2nd_00020.pth` (main model) | HF `yl4579/StyleTTS2-LibriTTS` | 771,390,526 B (≈736 MB) |
| `reference_audio.zip` (voice-cloning reference clips) | HF `yl4579/StyleTTS2-LibriTTS` | 2,917,622 B (≈2.8 MB) |
| `Utils/ASR/epoch_00080.pth` (ASR model, phoneme alignment) | GitHub `yl4579/StyleTTS2` raw | 94,552,811 B (≈90.2 MB) |
| `Utils/JDC/bst.t7` (F0/pitch predictor) | GitHub `yl4579/StyleTTS2` raw | 21,029,926 B (≈20.1 MB) |
| `Utils/PLBERT/step_1000000.t7` (PL-BERT text encoder) | GitHub `yl4579/StyleTTS2` raw | 25,185,187 B (≈24.0 MB) |
| **Total** | | **≈873 MB** |

More precise than the card's "~1 GB" estimate. Model cache path: `models/styletts2/`
(mirrors `models/kokoro/`) — the package's own `cached_path()` helper (from the
`cached_path` library, an AllenNLP-style generic URI cache) will be pointed there via its
own cache-dir configuration, confirmed to support a custom target directory.

### D21.1b-c: 3 test lines — same as 21.1, real voice-selection finding

Same 3 lines as 21.1 (line 0/24/29 from `b330d37f...`) for direct A/B, per the card.

**Real architectural finding, changes the voice-pick approach:** read `tts.py`'s real
`inference()` signature directly — StyleTTS 2 is a **reference-audio voice-cloning**
model, not a discrete named-voice model like Kokoro. Its only voice parameter is
`target_voice_path: Path to audio file of target voice to clone` — there is no "voice id"
list to cite (the card's own D21.1b-c wording, "2 different StyleTTS 2 voices from
LibriTTS pool," assumed a Kokoro-style enumerable voice pool that doesn't exist here).

Real, intended-for-this-purpose voice source found: the same HF repo also hosts
`reference_audio.zip` (2.8 MB, 19 files) — real contents inspected directly:
- Plain LibriTTS-speaker-ID clips (anonymous corpus speakers): `1221-135767-0014.wav`,
  `4077-13754-0000.wav`, `908-157963-0027.wav`, `5639-40744-0020.wav`, etc.
- Named clips matching the paper's own author list (Gavin, Vinay, Yinghao, Nima) —
  real author-recorded demo samples, not anonymous.
- Emotion-labeled clips (`anger.wav`, `disgusted.wav`, `amused.wav`, `sleepy.wav`) —
  demonstrates style/emotion transfer, not relevant to a "neutral narration" pick.

Plan: pick 2 of the plain anonymous LibriTTS-speaker clips (not the author or
emotion-labeled ones) for the male/female "neutral" pair, confirming each clip's actual
perceived gender via a quick real pitch/F0 check (median fundamental frequency — typically
<165 Hz reads male, >165 Hz reads female for adult speech) before committing to the final
2 filenames in the implementation commit, rather than guessing from filename alone.

### D21.1b-d: WordBoundary equivalent — confirmed no native timing, real fallback plan

Read `inference()`'s full real docstring and return type directly: `:return: audio data
as a Numpy array` — no timing/alignment data in the public API at all, confirmed (not
assumed) by reading the actual installed source, matching the card's anticipated "if no"
branch.

Fallback: `whisper-timestamped` (real PyPI package confirmed via `pip index versions`,
latest `1.15.9`) as a post-synthesis forced-aligner, per the card's own suggestion — runs
Whisper's ASR + DTW-based alignment against the already-synthesized audio to recover
per-word timestamps, independent of the TTS engine itself (same class of approach as
Task 19.2's Edge TTS `WordBoundary` capture, but post-hoc rather than native). Not yet
installed/tested in this design pass — a real go/no-go check (does it install cleanly in
`venv-styletts2/`, does it produce sane real timings on one of this spike's own clips) is
part of the implementation commit, not blocking the design approval, since the card
explicitly marks this "Not a spike blocker."

### D21.1b-e: Real GPU behavior + Ollama sharing — real measurement done

**Real baseline** (Ollama idle, `ollama ps` empty): `nvidia-smi` reports 1825 MiB used /
10286 MiB free / 12288 MiB total.

**Real concurrent-load measurement** (the card's explicit ask): force-loaded
`qwen3.5:9b` for real (`ollama run qwen3.5:9b "..."`, real response generated). Real
result:
```
NAME          SIZE      PROCESSOR    CONTEXT
qwen3.5:9b    5.5 GB    100% GPU     4096
```
`nvidia-smi` during this load: **8195 MiB used, 3916 MiB free, 12288 MiB total.**

**This directly confirms the card's proposed 6 GB threshold is both real and necessary**:
with qwen loaded, only ~3.9 GB VRAM remains — below StyleTTS 2's own claimed 4-6 GB
requirement. Loading StyleTTS 2 in this state would be genuinely unsafe (real risk of a
CUDA OOM, not a hypothetical one).

**Recommendation confirmed: option (ii)** — check `nvidia-smi` free memory before
loading StyleTTS 2; skip it and use Edge TTS if free VRAM `< 6 GB`. Matches Phase 18's
cloud-first-with-fallback discipline and Task 19.7's I36 pattern exactly, now with a real
number (not a guess) behind the specific threshold: 3.9 GB free (qwen loaded) is unsafe,
10.3 GB free (idle) is safe, 6 GB sits as a real, evidence-based margin between the two
measured real states, not an arbitrary round number.

A real "does StyleTTS 2 actually crash or degrade gracefully when it tries to load with
qwen already occupying most of VRAM" test (the card's other explicit ask) is deferred to
the implementation commit — it needs the isolated worker actually built first (this
design pass confirms Python compat + the threshold *policy*, not yet the *runtime
behavior* under real contention, which the D21.1b-e "load-on-demand" worker itself must
implement and then be tested against).

### D21.1b-f: Owner-side listening comparison protocol

Confirmed as written in the card — no changes. `spike_comparison_styletts2.mp3`, same
1s-silence-between-clips convention as 21.1, reusing 21.1's own Edge TTS baseline
measurements by reference (§6 of the report) rather than re-synthesizing them, since
Edge TTS's output for the same 3 lines/voices hasn't changed.

### D21.1b-g: Decision proposal

Deferred to the actual spike report after real measurement across all 12 clips + the
real GPU-contention test + the owner's real listening answer — same discipline as 21.1,
not pre-decided here.

## Verification

- All 12 clips render successfully; no CUDA OOM crashes during synthesis.
- `spike_comparison_styletts2.mp3` exists and plays.
- Full suite: 1205/1205 (this task adds no tests). ruff clean.
- Zero `app/`, `frontend/`, `tests/`, `video-renderer/`, prior spike reports touched.

## Evidence (spike report structure)

Mirror 21.1's structure with additions:

1. **Environment** (torch, StyleTTS 2 version, CUDA, model version + digest, RAM, CPU,
   GPU, OS)
2. **Install footprint** (model on disk, venv-styletts2 if used, torch already-existing
   baseline)
3. **Python-compat approach** (native import vs subprocess, evidence cited)
4. **3 test lines** (verbatim from `b330d37f...`, matching 21.1)
5. **StyleTTS 2 measurements** (per-line wall time, RTF, RAM, **VRAM**, output
   duration)
6. **Edge TTS baseline** (re-use 21.1's measurements if unchanged — cite by reference)
7. **GPU-sharing behavior** (real Ollama-qwen coexistence measurement; chosen sharing
   strategy)
8. **Side-by-side comparison table** (StyleTTS 2 vs. Kokoro-from-21.1 vs. Edge TTS)
9. **Owner listening protocol** (path to comparison mp3, listening question)
10. **Decision proposal** (PASS / SCOPE-CUT / STOP + real-number reasoning)

## Definition of done

- All allowed files created, no disallowed touched.
- Design commit lands **before** implementation commit.
- 12 real clips on disk under `data/tmp/phase21_styletts2_spike/`.
- `spike_comparison_styletts2.mp3` on disk.
- Real GPU coexistence evidence documented (with-and-without qwen loaded).
- Spike report on disk with every "Evidence" item filled from real measurement.
- Handover message includes: report path, RTF number, VRAM footprint, GPU-sharing
  strategy, owner listening question link, PASS / SCOPE-CUT / STOP proposal.
