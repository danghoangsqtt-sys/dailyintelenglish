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
