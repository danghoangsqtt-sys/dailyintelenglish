# Task 19.2 — Edge TTS `WordBoundary` capture + per-word timestamps + additive migration

- **Status:** not started (doc-first card, awaiting Coder pickup)
- **Owner:** Coder
- **Priority:** P0 (blocks 19.3 karaoke composition)
- **Dependency:** Task 19.1 accepted (spike PASS, owner D33 2026-09-28, commit
  `4dd325b`); `docs/operations/phase19-spike-remotion.md` on disk
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.2"; ENH-013
  ("Scope" item 1: word-level karaoke needs per-word timestamps; Edge TTS emits
  `WordBoundary` events); Phase 19 invariants 36–40; standing invariants 31–35 (secrets),
  4–5 (thresholds); PM/Coder split AR-06

## Goal

Capture per-word timestamps from Edge TTS's own `WordBoundary` events during line synthesis,
aggregate them onto the mixed-output timeline (same offset math as today's per-line times),
and persist them alongside the existing `audio_jobs.timestamps_json` — as an additive column,
not a replacement. This is a pure data-capture task: nothing in the Remotion composition
consumes the new column yet (that is 19.3). No user-visible behaviour changes on this task
alone.

## Allowed files

- **Modify** `app/services/tts_service.py` — `_synthesize_edge_tts()` returns both audio bytes
  and the per-word list (`[{text, offset_sec, duration_sec}]`), backward-compatible via a
  small return-type change or a paired helper. Existing callers that only want bytes keep
  working; `AudioService` is the only new consumer.
- **Modify** `app/services/audio_service.py` — while building the mixed output, aggregate
  per-line word boundaries onto the mixed timeline (`mix_offset_sec + wb.offset_sec`), store
  as one JSON blob on the job row. **Reuse the existing per-line offset math**, do not
  invent a second one.
- **New** `app/db/migrations/007_word_timestamps.sql` — additive `ALTER TABLE audio_jobs ADD
  COLUMN word_timestamps_json TEXT` (nullable, no default). Same additive pattern as
  `004_youtube_chapters_measured.sql`, `005_video_vertical_output.sql`. Migration runner is
  already file-driven per `app/db/database.py`; do **not** change the runner itself.
- **Modify** `app/db/database.py` **only if** the runner needs a bump for the new file and
  the change is a one-line "list migrations up to N" style; anything larger is out of scope
  and a design question, not a fold-in.
- **Modify** `app/services/audio_service.py`'s job-persistence path to also write
  `word_timestamps_json` when present. Existing `timestamps_json` write path stays
  unchanged; both columns coexist.
- **New** `tests/test_tts_word_boundary.py` — real Edge TTS call on **one** short B1-shaped
  test line with a known word count (5–8 words); assert per-word `text` matches the input,
  offsets are monotonic non-decreasing, and `sum(duration_sec)` is within ±10% of the
  synthesized clip's actual duration (ffprobe or pydub-measured, whichever is already used
  elsewhere in this test module — don't add a new dependency for measurement).
- **Modify** `tests/test_audio_service.py` — one new test asserting that when TTS returns
  word boundaries, `mix_project`'s output row has a well-formed `word_timestamps_json` whose
  first word's aggregated offset equals its line's `start_sec`, and last word's aggregated
  end equals (or is within 20 ms of) its line's `end_sec` for the last line. Keep every
  existing test's fixtures/expectations untouched (this is additive).
- `CHANGELOG.md` — append under `[Unreleased]` one bullet describing the additive schema
  addition + capture path, no user-visible behaviour change yet.
- `.viepilot/phases/19-remotion/PHASE-STATE.md` — flip 19.2 row to "done", append an
  Evidence log entry with real numbers.

**Not allowed:** any file under `video-renderer/`, `frontend/`, `docs/implementation/`,
`docs/operations/` (the 19.1 spike report is not amended here — its findings stand as
written). `data/app.db` write access is scoped to whatever the existing migration runner
already does on startup — no manual `UPDATE`/`INSERT` from this task.

## Design decisions (Coder, doc-first — commit these under `docs(review)` before code)

The Coder writes a design section here answering each of the following, PM approves, then
code lands in a separate commit. Same pattern as Task 19.1.

### D19.2-a: `WordBoundary` chunk shape and unit

- Confirm from Edge TTS's own `Communicate.stream()` that `chunk["type"] == "WordBoundary"`
  events carry `offset`, `duration`, `text`, and that `offset`/`duration` are in
  100-nanosecond ticks (.NET convention — `ticks / 1e7 == seconds`). Cite one real
  observation from a throwaway probe, not just the library README.
- Decide whether to store `offset_sec` (float) or `offset_ticks` (int). Recommend `float
  seconds` throughout, matching the existing `timestamps_json` shape's `start_sec`/`end_sec`
  keys; justify in one line.

### D19.2-b: TTS return-type change vs. paired helper

- Two shapes on the table:
  - (i) `_synthesize_edge_tts()` returns a tuple `(bytes, list[WordBoundary])`, all callers
    updated.
  - (ii) `_synthesize_edge_tts()` keeps returning `bytes` unchanged; a new
    `_synthesize_edge_tts_with_boundaries()` returns the tuple, called only by
    `AudioService.mix_project`.
- Recommend (i) with a `NamedTuple` (or a small `@dataclass`) return type — clearer,
  no duplication, and only one internal caller today (`_generate_line`) plus the mix path.
  But justify the choice against the actual current call graph, not from principle.

### D19.2-c: Aggregation math

- Given a line's per-word boundaries (relative to that line's own audio) and the line's
  offset in the mixed output (already computed for `timestamps_json`), express the
  aggregation formula in one line. Assert it is the same offset value used by the existing
  `timestamps_json`'s `start_sec` — reused, not recomputed.
- Handle these edge cases explicitly in the design (each one in one line):
  - Line with zero word boundaries returned (Edge TTS occasional edge case): store an empty
    array for that line, not `null`, so consumers can distinguish "captured but empty" from
    "not captured for this project's older rows".
  - Line with per-word times summing to slightly more/less than the pydub-measured line
    duration: keep the raw per-word values (do not rescale); document the tolerance.
  - Silence gaps between lines (Task 1.6b's 300 ms / 500 ms same/different-speaker padding):
    these fall in the between-lines gaps and are already accounted for in the line's own
    offset — do not attribute silence to any word.

### D19.2-d: Storage shape

- Exact JSON shape written to `audio_jobs.word_timestamps_json`. Recommend:
  `[{"line_id": <str>, "words": [{"text": <str>, "start_sec": <float>, "end_sec": <float>}, …]}, …]`
  with the top-level array in the same order as `timestamps_json`'s lines. Justify per-line
  nesting (Remotion's `@remotion/captions` will consume per-line + per-word — see 19.3).
- Confirm the total JSON size on a real B1 8-min episode (~2500 words) fits comfortably in
  SQLite's default `TEXT` limits (measurement in the design commit, not a guess).

### D19.2-e: Backward compatibility for existing rows

- Existing `audio_jobs` rows (e.g. `b330d37f...` from the 19.1 spike) will have
  `word_timestamps_json = NULL`. Confirm — with a code reference, not a claim — that no
  existing consumer of `audio_jobs` reads a column that doesn't exist (they don't; the
  additive migration is safe by construction) and that the new column is only ever read by
  code introduced in this task and later.
- **The regenerate path** (`AudioService.mix_project` re-run for an existing project): the
  new column is populated on next mix; no back-fill migration for old rows. Not a defect —
  same behaviour Task 1.9b took with the `chapters_estimated` flag when
  `real_chapters_from_timestamps` was added.

### D19.2-f: Test-time isolation

- The real Edge TTS test on one line must:
  - Run against the real free Edge TTS endpoint (no mock — the value of this test is that
    the boundary shape and units are what the code assumes).
  - Skip cleanly with a clear reason when network is unavailable (e.g. `pytest.skip` with
    "Edge TTS network unavailable"). No offline fixture — a fixture would test the assertion
    without testing the assumption.
  - Use a fresh in-memory SQLite for anything DB-touching. Never touch `data/app.db` (hard
    constraint from `SYSTEM-RULES.md` / Coder brief).

## Design decisions — Coder answers (2026-09-28)

**Card correction found first:** `_generate_line` (cited in D19.2-b as an existing internal
caller of `_synthesize_edge_tts`) does not exist anywhere in this codebase (confirmed by
grep). The real, only internal caller is `tts_service.synthesize_line_audio` (two call
sites within it: the omnivoice-fallback branch and the plain edge_tts branch). Everything
below is grounded in the actual call graph, not the card's name for it.

### D19.2-a: `WordBoundary` chunk shape and unit — real probe, and a missing-parameter finding

Ran two live throwaway probes against the real Edge TTS endpoint (`en-US-AriaNeural`,
"Hello there, how are you today?"):

1. **First probe, using `_synthesize_edge_tts`'s *current* exact `Communicate(...)` call
   shape** (no `boundary` kwarg): the stream produced `{'SentenceBoundary': 1, 'audio': 23}`
   chunks — **zero `WordBoundary` chunks.** Root cause, found by reading
   `edge_tts/communicate.py:335`: `Communicate.__init__` takes
   `boundary: Literal["WordBoundary", "SentenceBoundary"] = "SentenceBoundary"`, defaulting
   to sentence-level. **The card's assumption that `WordBoundary` events "just show up" is
   wrong for this installed version (`edge-tts==7.2.8`) — `boundary="WordBoundary"` must be
   passed explicitly to the constructor,** alongside the existing `rate`/`volume`/`pitch`
   kwargs. This is the one required code change D19.2-a exists to specify; without it, this
   entire task captures nothing.
2. **Second probe, with `boundary="WordBoundary"` passed:** real chunks observed:
   `{'offset': 1000000, 'duration': 3750000, 'text': 'Hello'}`,
   `{'offset': 4875000, 'duration': 2875000, 'text': 'there'}`, … 6 words total. Confirms the
   card's unit assumption: `offset`/`duration` are integers in 100-ns ticks (.NET
   convention) — `1000000 / 1e7 = 0.1` matches "Hello" starting ~0.1s in, a plausible small
   leading pause.
- **Storage decision: float seconds throughout**, converted once at capture time
  (`chunk["offset"] / 1e7`, `chunk["duration"] / 1e7`) — matches `timestamps_json`'s
  existing `start_sec`/`end_sec` float-seconds convention; ticks never leave `tts_service.py`.
- New `WordBoundary` shape (a module-level `NamedTuple` in `tts_service.py`, only used
  internally — not persisted directly, see D19.2-d for the two *different* JSON shapes at
  the two different stages): `text: str`, `offset_sec: float`, `duration_sec: float`.

### D19.2-b: TTS return-type change vs. paired helper — recommend (i), with a real blast-radius count

Recommend **(i)**: `_synthesize_edge_tts()` returns `tuple[bytes, list[WordBoundary]]`
directly. Rejected (ii) for a concrete reason, not principle: (ii) has
`AudioService.mix_project` call the new helper directly, which means **AudioService calls a
TTS engine** — directly contradicting `audio_service.py`'s own module docstring invariant
("this module only processes already-synthesized audio files — it never calls a TTS engine
itself") and doubling the real Edge TTS network cost per line (once at synthesis, once again
at every mix/re-mix) for no benefit. (i) keeps one synthesis call per line, full stop.

**Real blast-radius check for (i), done by grepping rather than guessing:** 5 test files
monkeypatch `tts_service._synthesize_edge_tts` directly with a `fake_edge_tts` returning bare
bytes: `tests/test_tts_service.py` (in this card's own scope already, via
`test_audio_service.py`'s sibling) — plus **four files not in this task's "Allowed files"
list**: `tests/test_audio_api.py:49`, `tests/test_video_api.py:45`,
`tests/test_youtube_export_api.py` (its own `fake_edge_tts`, wired at line 120), and
`tests/test_tts_api.py:37`. Every one of these fakes is a **one-line body** (e.g.
`return _real_tone_mp3_bytes(...)` or `return FAKE_MP3_BYTES`) that must become
`return (<same bytes>, [])` once `_synthesize_edge_tts`'s real contract changes — otherwise
`synthesize_line_audio`'s new `audio_bytes, word_boundaries = await _synthesize_edge_tts(...)`
unpacking crashes against a bare-bytes fake with "too many values to unpack".

**Explicit scope question for PM:** these 4 files are not in the card's "Allowed files" list.
I'm asking to fold them in rather than silently touching them or leaving the suite red —
each needs exactly the one-line mechanical fix above, no behavior change to what they test
(still zero real network calls). Proceeding on the assumption this is approved alongside the
rest of this design (flagging per my brief's "ask rather than silently do" rule); will hold
if PM says otherwise.

### D19.2-c: Aggregation math

**Where per-word data lives between synthesis and mix**, since `audio_service.py` cannot call
TTS (D19.2-b) and today only reads `line["audio_cache_path"]` off disk: `synthesize_line_audio`
writes a **sidecar JSON file** next to the cached MP3 — `<line_id>.words.json` in the same
`tts_cache/<project_id>/` directory, derived via `Path(audio_path).with_suffix(".words.json")`
(verified this is a single, correct rename, not two suffix ops). Contents: the raw per-line
`[{"text", "offset_sec", "duration_sec"}, …]` list, in the line's own local time — **no DB
column added for this path; it's fully deterministic from `audio_cache_path`, so
`audio_service.py` derives the same path independently.** Only written when
`engine_used == "edge_tts"` (omnivoice lines get no sidecar — same as "not captured").

**Aggregation formula** (in `_mix_project_sync`'s existing per-line loop, where `start_ms` is
already computed for that line's own `timestamps.append(...)` entry):
```
word.start_sec = round(start_ms / 1000 + raw_word["offset_sec"], 3)
word.end_sec   = round(start_ms / 1000 + raw_word["offset_sec"] + raw_word["duration_sec"], 3)
```
`start_ms` is the exact same value `timestamps_json`'s `start_sec` is built from three lines
later in the same loop — reused, not recomputed.

**Edge cases:**
- Zero word boundaries (no sidecar file, or an empty sidecar): append
  `{"line_id": line["id"], "words": []}` — empty array, never `null`. This one representation
  covers *both* "omnivoice, never captured" and "edge_tts, genuinely zero words returned" —
  the aggregation stage has no way to distinguish them and doesn't need to; both mean "no
  words available for this line" to any future consumer (19.3).
- Sum-vs-duration drift: **do not rescale.** Real measured example (from the probe above,
  6-word clip): `sum(duration_sec) = 1.475s` vs. the pydub-measured clip duration `2.712s` —
  a **46% gap**, not "slight." This is expected, structural behavior, not a defect: per-word
  `duration_sec` covers only the voiced span of that word, excluding inter-word pauses and a
  trailing pause after the last word (leading pause before the first word too — first word's
  `offset_sec` was `0.1s`, not `0.0s`, in the same probe). **This real number changes the
  verification assertions the card proposed** — see D19.2-f.
- Silence gaps between lines (300/500 ms same/different-speaker padding, Task 1.6b): already
  folded into `start_ms` (computed *after* the gap is added to `cursor_ms`), so word offsets
  automatically land after the gap — no separate handling needed, confirmed by reading
  `_mix_project_sync`'s existing loop order (gap added to `cursor_ms` before `start_ms` is
  captured for the *current* line).

### D19.2-d: Storage shape

Two different JSON shapes at two different stages, worth stating explicitly so they're never
confused:
- **Sidecar** (per-line, local time, `tts_service.py`-owned): `[{"text", "offset_sec",
  "duration_sec"}, …]`.
- **`audio_jobs.word_timestamps_json`** (whole-episode, mix-absolute time,
  `audio_service.py`-owned), exactly the card's proposed shape:
  `[{"line_id": <str>, "words": [{"text", "start_sec", "end_sec"}, …]}, …]`, top-level array
  in `timestamps_json`'s line order. Per-line nesting matches how 19.3's
  `@remotion/captions` will need to look up "words for the currently active line."

**Real size check** (not a guess): measured the actual JSON byte cost of a real 6-word
captured line at 380 bytes total including its `{"line_id": …, "words": [...]}` wrapper —
**~56.5 bytes/word** net of the per-line wrapper overhead (~40 bytes/line). Extrapolated to a
~2500-word, ~60-line episode (that shape, not the 19.1 spike's 30-line/176-word sample):
**≈140 KB total.** SQLite's `TEXT` column has no practical size ceiling anywhere near this
(default `SQLITE_MAX_LENGTH` is ~1 GB) — comfortably fits.

### D19.2-e: Backward compatibility for existing rows

- Code reference, not a claim: `audio_service.get_audio_job`'s `SELECT` lists columns
  explicitly (`"SELECT id, project_id, status, mp3_path, wav_path, timestamps_json, …"` —
  never `SELECT *`), so **every existing caller of this function today is unaffected by the
  new column** until this task's own edit adds `word_timestamps_json` to that same list.
  `_row_to_job` will parse it the same way `timestamps_json` already is:
  `json.loads(...) if ... else []` — NULL rows (every row created before this task,
  including the 19.1 spike's `b330d37f...`) read back as `word_timestamps: []`, never a
  crash, never `None` leaking to a consumer that expects a list.
- Regenerate path: next `mix_project` run for an existing project populates the column going
  forward; no back-fill migration for old rows. Same precedent as `chapters_estimated`
  (`app/services/youtube_service.py`, Task 1.9b) — old rows simply don't get the new
  capability until regenerated.
- **`app/db/database.py` needs no change.** Its migration runner is fully
  glob-plus-sorted-filename driven (`for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql"))`)
  — a new `007_word_timestamps.sql` file is picked up automatically. The card's "modify
  database.py only if the runner needs a bump" doesn't apply; noting this so nobody expects
  an edit there.

### D19.2-f: Test-time isolation, and two corrected assertions from real measurement

- Real-network test (`tests/test_tts_word_boundary.py`): calls the real endpoint, no mock.
  **Skip mechanism:** catch `(aiohttp.ClientError, OSError)` around the real call specifically
  (edge-tts's transport is `aiohttp` under the hood, confirmed by reading
  `edge_tts/communicate.py`'s imports) and `pytest.skip("Edge TTS network unavailable: …")` —
  deliberately *not* a blanket `except Exception`, so a real bug in the capture code (e.g. a
  `KeyError` on `chunk["text"]`) still fails the test instead of being swallowed as "network
  unavailable."
- In-memory DB for `test_audio_service.py`'s new case: uses the existing `db` fixture (same
  as every other test in that file), never `data/app.db`.
- **Two assertions from the card need correcting, backed by the real numbers in D19.2-c**,
  or the new tests would fail against real Edge TTS output on day one:
  1. `test_tts_word_boundary.py`: **not** "`sum(duration_sec)` within ±10% of clip duration"
     — real measurement shows a structural ~46% gap (inter-word/trailing silence isn't
     counted in any word's `duration_sec`). Corrected assertion: per-word text matches the
     input's words, offsets are monotonic non-decreasing (unchanged from the card), and the
     **last word's `offset_sec + duration_sec` does not exceed the clip's measured duration
     by more than a 0.5 s absolute tolerance** (generous for trailing-pause padding, still a
     real correctness check — it would catch a genuinely broken/scaled timestamp).
  2. `test_audio_service.py`'s new case: **not** "first word's aggregated offset *equals*
     its line's `start_sec`" — real measurement shows ~0.1 s of leading silence before the
     first word, so the true value is `line.start_sec + ~0.1s`, not `line.start_sec` exactly.
     Corrected assertion: first word's aggregated `start_sec` is `>= line.start_sec` and
     within `0.5s` of it (same generous, real-evidence-based tolerance as above, applied
     symmetrically to both ends — the card already allowed "within 20ms" for the *last*
     word's end vs. the line's `end_sec`; that one stays as the card wrote it since it's
     testing a different, already-adjacent boundary, not the leading-silence case).

### Second explicit scope question: `app/api/audio.py` wiring

`AudioService.mix_project`'s result dict gains a new `"word_timestamps"` key
(`_mix_project_sync` builds it, `mix_project` already passes its whole return value through
unchanged — no edit needed there). But the only caller that turns that result into a
persisted `audio_jobs` row is `app/api/audio.py::generate_audio`
(`app/api/audio.py:53-64`), which passes each field to `save_audio_job` **by explicit
keyword** (`mp3_path=result["mp3_path"]`, `timestamps=result["timestamps"]`, …) — there is no
`**result` spread to piggyback on. Without one added line
(`word_timestamps=result["word_timestamps"]`) in that call, `word_timestamps_json` stays
`NULL` forever, on *every* project, even brand-new ones — the whole task would be inert data
plumbing with nothing on the write end. `app/api/audio.py` is not in this card's "Allowed
files" list and not in "Not allowed" either (that section only names `video-renderer/`,
`frontend/`, `docs/implementation/`, `docs/operations/`). Flagging explicitly and asking for
sign-off to add this one line, same as the 4-test-file question above, rather than silently
touching it or shipping a feature that silently never writes anything.

(Aside, not a blocker: `app/models/audio.py`'s `AudioJobOut` Pydantic model already declares
a `timestamps` field but is never used as a `response_model` anywhere — confirmed by grep,
zero references outside its own definition. Dead code predating this task; not touching it,
since the actual API response is an unvalidated dict and doesn't need this model updated for
`word_timestamps` to reach the response body.)

### Carry-over conditions from 19.1 — acknowledged, not implemented here

1. **8-min B1 episode:** still does not exist in `data/app.db` (unchanged since the 19.1
   spike). Not invented for this task. If one exists by close of this task, run one
   confirmation synthesis + capture at that scale and append a line to the evidence log; if
   not, say so plainly in the handover (this design doc is written assuming it will still say
   "none exists").
2. **Chrome ~270 MB hard floor:** out of scope for 19.2 (no `video-renderer/` change in this
   task at all). Acknowledged as carried into 19.7, not forgotten.

## PM review — APPROVED with scope extensions (2026-09-28, session a01f96)

Both explicit scope questions **greenlit**, added to this task's effective "Allowed files":
1. `app/api/audio.py::generate_audio` — the one-line `word_timestamps=result["word_timestamps"]`
   addition to the `save_audio_job(...)` call.
2. `tests/test_audio_api.py`, `tests/test_video_api.py`, `tests/test_youtube_export_api.py`,
   `tests/test_tts_api.py` — one-line mechanical fix each to `fake_edge_tts`'s return value
   (`return (<bytes>, [])`), a direct consequence of the D19.2-b contract change.

Explicitly **not** extended: `app/models/audio.py::AudioJobOut` stays untouched (dead code,
not a `response_model` anywhere) — agreed, leave for whenever it's actually wired up.

Both real-data corrections (sum-vs-duration → last-word absolute tolerance; first-word
offset → `>=` + tolerance, not exact equality) accepted verbatim as designed above.

One clarification (not a change request): confirmed at implementation time (see note above
this section) that `tts_cache/<project_id>/<line_id>.mp3` is genuinely one file per line —
the sidecar path derivation is safe.

Implementation proceeds as designed. Fold this approval into the implementation commit (no
separate re-commit of the design card needed).

## Verification

- New tests pass (`tests/test_tts_word_boundary.py`, the new `test_audio_service.py` case).
- **Revert-and-confirm-failure** on the new `test_tts_word_boundary.py`: revert
  `_synthesize_edge_tts()`'s WordBoundary-capture branch, re-run the test, confirm it fails
  for the right reason (empty word list, not a syntax error). Restore, re-run, confirm
  green. Same discipline the project has applied on every prior test-heavy task.
- Full suite: **1177+/1177+ pass** (1175 baseline + at least the 2 new tests). `ruff check
  .` clean.
- Migration applies cleanly on a fresh DB and on the existing real DB (verified via a
  read-only `PRAGMA table_info(audio_jobs)` check that the new column appears). Migration
  runner still finds all 8 migrations (`001`, `002`, `003`, `004_app_settings`,
  `004_youtube_chapters_measured`, `005`, `006`, `007`) and applies `007` exactly once.
- `git diff` shows zero changes under `app/services/video_service.py`, `frontend/`,
  `video-renderer/`, `docs/implementation/`.

## Evidence (what the Coder's handover message includes)

- Commit sha for the design commit and the implementation commit (two separate commits, per
  the doc-first discipline).
- Full-suite line ("N passed, M warnings in Xs").
- `ruff check .` line.
- One real-numbers datapoint from the WordBoundary test: which line, its text, the word
  count returned, the sum of per-word durations vs. clip duration.
- Confirmation of the two Task 19.1 carry-over conditions:
  1. If a real 8-min B1 episode with completed audio exists in the DB by close of this
     task, one confirmation synthesis + word-boundary capture end-to-end at the 8-min scale
     (append one line to the report / phase evidence log). If none exists, say so — do not
     invent an episode.
  2. Chrome ~270 MB hard floor: no action in this task (packaging is 19.7's problem); just
     acknowledge in the handover that the condition is carried, not lost.

## Definition of done

- All allowed files edited or created, no disallowed files touched.
- Design commit lands **before** the implementation commit — git history proves the
  doc-first gate.
- New tests + full suite green; revert-and-confirm-failure done on the key new test.
- `word_timestamps_json` column populated on any new `mix_project` run; existing rows
  unaffected (`NULL` for them, verified live).
- Handover message to PM includes: both shas, full-suite line, ruff line, real WordBoundary
  datapoint, carry-over condition acknowledgement.
- PM ACCEPTS task-level; owner does not need to sign off on 19.2 (it's a data-capture task,
  not a phase-level gate).
