# Task 2.1a: Quality Testing — CEFR × Genre Script Sample Exporter

## Meta
- **ID**: 2.1a (first bounded slice of ROADMAP.md Phase 2 "Quality Testing")
- **Phase**: 2
- **Status**: code_complete_pending_real_run (PM-owned; Codex must not change this field — code independently verified 2026-09-14, real 18-call campaign blocked on external Gemini quota, see Implementer Evidence/PM Acceptance below)
- **Priority**: medium
- **Assignee**: Codex (AI Implementer under AR-06; no self-approval)

## Doc-First Gate

This task card records the PM-approved scope before implementation. Codex must stop after
creating this file and wait until PM confirms that the plan in this file has been read.
No other allowed file may be created or modified before that confirmation.

## Context

ROADMAP.md Task 2.1 requires 18 scripts for manual CEFR accuracy review: six CEFR levels
times three genres. The application already has the production generation path in
`app/services/script_service.py::generate_script()`, including production prompt
composition, Gemini `responseJsonSchema`, Pydantic validation, and the semantic check
that every returned speaker UUID belongs to the supplied config.

This task will automate only sample generation and evidence packaging. It will not infer,
score, or claim that a script is CEFR-accurate. Final language-quality judgment remains
with PM/the human reviewer.

## Objective

Add a standalone CLI that generates a deterministic 18-case input matrix and calls the
existing production `generate_script()` service once per case:

- CEFR levels: `A1`, `A2`, `B1`, `B2`, `C1`, `C2` (uppercase, matching
  `app/core/constants.py::CEFR_LEVELS`).
- Genres: `small_talk`, `interview`, `news` (matching
  `app/core/constants.py::GENRES`).
- Accent: `american` (matching `app/core/constants.py::ACCENTS`).
- Duration: 2 minutes per sample by default.
- Speakers: 2 per case, each with a fresh temporary UUID.
- Project ID: one fresh temporary UUID per case.

The CLI must not create a real project, open/write SQLite, or modify any application
state. It passes an in-memory production-shaped config directly to `generate_script()`.

## Fixed Topic Matrix

Each genre uses one fixed topic for all six CEFR levels. Keeping topic constant within a
genre isolates CEFR level as the changing variable and makes A1→C2 comparisons easier.

| Genre | Topic used for A1, A2, B1, B2, C1, and C2 |
|---|---|
| `small_talk` | `Planning a healthy weekday routine` |
| `interview` | `How remote work changes communication` |
| `news` | `A city opens a new public library` |

The matrix order is deterministic: CEFR level outer loop in `A1`→`C2` order, then genre
inner loop in `small_talk`, `interview`, `news` order, for exactly 18 cases.

## Per-Case Configuration

Every case uses the following explicit configuration; only `topic`, `cefr_level`, and
`genre` vary according to the matrix above:

- `accent`: `american`
- `duration_minutes`: `2.0` by default (overridable by the CLI's positive
  `--duration-minutes` option)
- `num_speakers`: `2`
- `language_features`:
  - `collocation`: `true`
  - `idiom`: `true`
  - `slang`: `false`
  - `local_expressions`: `false`
  - `phrasal_verbs`: `true`
  - `business_register`: `false`
- `speakers`: two in-memory speakers with stable display/persona fields but fresh UUIDs
  per case:
  - Alex: male, American accent, Edge TTS
  - Maya: female, American accent, Edge TTS

No API key, environment value, full prompt text, or other secret may be written to an
output artifact.

## CLI Contract

Command:

```powershell
venv\Scripts\python scripts\generate_cefr_review_samples.py
```

Supported selection/inspection options:

- `--levels`: optional subset of uppercase values from `CEFR_LEVELS`.
- `--genres`: optional subset of the three approved genres.
- `--duration-minutes`: positive duration override; default `2.0`.
- `--dry-run`: print the selected case matrix/config summary without calling Gemini or
  creating output files.

Real generation runs sequentially. Request start times must be separated by at least
4.1 seconds so the tool respects the project's declared 15-RPM Gemini limit. PM has
explicitly accepted the quota/time cost of the required full 18-call verification run;
Codex must run it without requesting another approval after the doc-first gate is lifted.

## Output Contract

Each non-dry run creates a new timestamped directory without overwriting an earlier run:

`data/quality_reviews/script-samples/<run-id>/`

It contains:

- `manifest.json`: run metadata and one record per selected case.
- `samples/<CEFR>__<genre>.json`: the validated structured script for each successful
  case, including line text and language notes.
- `review.md`: all successful transcripts plus an intentionally blank human-review
  checklist per case covering vocabulary, grammar, collocations, naturalness, topic
  relevance, speaker balance, and reviewer notes.

For traceability, every `manifest.json` case record must store the complete config passed
to `generate_script()`, including at minimum:

- `topic`
- `cefr_level`
- `genre`
- `accent`
- `duration_minutes`
- `num_speakers`
- the full `language_features` mapping
- the two speaker configs and their generated UUIDs
- the temporary `project_id`

Successful records also store status, output-relative path, and line count. Failed
records store status plus the concrete exception type/message, without secrets.

The manifest must be checkpointed as cases finish so successful samples remain available
if a later case fails. A per-case failure must be recorded and must not be reported as a
success. The run may continue to collect the remaining cases, but the CLI must exit with
a non-zero code if any selected case failed.

## Paths (`allowed_files` — do not touch anything outside this list)

- `.viepilot/phases/02-testing-polish/tasks/task-2.1a.md` (this task card; PM owns
  `Status` and final acceptance)
- `scripts/generate_cefr_review_samples.py` (new)
- `tests/test_generate_cefr_review_samples.py` (new)
- `.gitignore` (only add the `data/quality_reviews/` ignore entry)
- `data/quality_reviews/script-samples/**` (generated runtime evidence only; ignored,
  never staged or committed)

## Acceptance Criteria

- [ ] Default CLI matrix contains exactly 18 unique cases: 6 approved uppercase CEFR
  levels × 3 approved genres, in the documented order and using the fixed topics above.
- [ ] Each real case calls `app.services.script_service.generate_script()` directly with
  temporary UUIDs and a production-shaped in-memory config.
- [ ] The CLI never creates a project, opens/writes SQLite, or changes application state.
- [ ] Default real run throttles Gemini request start times to at least 4.1 seconds apart.
- [ ] `--dry-run` makes zero Gemini calls and creates zero output files.
- [ ] Each timestamped run writes `manifest.json`, successful per-case JSON files, and a
  consolidated `review.md` with blank human-review fields and no automatic CEFR verdict.
- [ ] Every manifest case stores the complete generation config and temporary IDs defined
  in the Output Contract, not only pass/fail status.
- [ ] If any real case fails, completed samples remain intact, the failure is written to
  the manifest with a concrete error, the summary is truthful, and the process exits
  non-zero.
- [ ] Tests use monkeypatched generation/sleep for deterministic coverage and never make
  real network calls; the separately required CLI full run supplies real-integration
  evidence.
- [ ] `.gitignore` gains only `data/quality_reviews/` for this task.
- [ ] No file outside `allowed_files` changes.

## Planned Automated Coverage

`tests/test_generate_cefr_review_samples.py` will cover at least:

- Exact 18-case matrix, ordering, uppercase CEFR casing, approved genres, and fixed topic
  mapping.
- Subset CLI selection and positive duration validation.
- Dry-run performs no generation and writes no artifacts.
- Successful fake generation writes traceable complete configs, sample JSON, and human
  review Markdown without an automated CEFR score/verdict.
- A failed case preserves earlier successes, records the exact failure, and produces a
  non-zero result.
- Throttling enforces at least 4.1 seconds between request starts, using a fake clock and
  sleeper so unit tests remain fast.

## Risks and Boundaries

- Gemini output is nondeterministic; this task guarantees traceable inputs and validated
  structure, not identical text across runs.
- The required real run consumes 18 Gemini calls and can encounter 429, network, or schema
  errors. Existing production retry/validation behavior remains authoritative; this CLI
  adds no alternate/fake success path.
- Generated content may require correction after human review. This task does not change
  prompt templates in response; any prompt fix requires a separate PM-approved task.
- This slice covers only the CEFR-script portion of Task 2.1. It does not complete or
  claim completion of multi-accent listening, audio quality, or video/subtitle testing.
- GPU and ffmpeg are not used by this CLI. Their availability does not justify expanding
  this task into TTS/audio/video QA.

## Forbidden Scope

- No changes under `app/`, including `script_service.py`.
- No changes to prompt templates, database/migrations, API routes, frontend, ROADMAP.md,
  TRACKER.md, or PHASE-STATE.md.
- No automated CEFR scoring or AI-as-judge verdict.
- No background-job/progress-cancellation work.
- No refactor of existing generation logic.
- No `git add .`, self-approval, commit, or push.
- Codex must not change this task card's `Status` field.

## Verification Commands

Run in this exact required set before reporting `ready_for_review`, preserving the real
stdout/stderr and exit code for the evidence section:

1. `venv\Scripts\python -m pytest tests/test_generate_cefr_review_samples.py -q`
2. `venv\Scripts\python scripts\generate_cefr_review_samples.py --dry-run`
3. `venv\Scripts\python scripts\generate_cefr_review_samples.py` — real 18-call Gemini
   run; PM has approved the quota/time cost.
4. `venv\Scripts\python -m pytest tests/ -q`
5. `venv\Scripts\python -m ruff check app/ tests/ scripts/generate_cefr_review_samples.py`
6. `git diff --check`
7. `git status --short`

If the known full-suite Gemini retry timing flake occurs, rerun the exact failing test in
isolation and report both raw outputs. Do not conceal it and do not classify an unrelated,
unreproduced failure as acceptable.

## Implementer Evidence (Awaiting PM Acceptance)

**Correction to the line above (PM, 2026-09-14):** this section previously stated
"Implementation has not started," but that was stale — Codex ran out of quota again after
implementing the full solution and before updating this section (same recurring pattern as
Task 1.8b and the Task 2.3 step-nav slice). PM found `scripts/generate_cefr_review_samples.py`
(427 lines) and `tests/test_generate_cefr_review_samples.py` (233 lines) already complete and
correct on disk, plus the exact one-line `.gitignore` addition (`data/quality_reviews/`) —
matching `allowed_files` precisely, nothing else touched. Per AR-06, PM did not trust this
written report and independently re-read both files end-to-end and re-ran every verification
command from scratch below.

## PM Independent Verification (2026-09-14)

1. `venv\Scripts\python -m pytest tests/test_generate_cefr_review_samples.py -q` → `6 passed in 0.57s`
2. `venv\Scripts\python scripts\generate_cefr_review_samples.py --dry-run` → printed the exact 18-case matrix (A1→C2 × small_talk/interview/news, correct topics/accent/duration/speakers per case), zero files created, confirmed by directory listing.
3. `venv\Scripts\python -m ruff check app/ tests/ scripts/generate_cefr_review_samples.py` → `All checks passed!`
4. `venv\Scripts\python -m pytest tests/ -q` → `499 passed, 3 warnings in 257.11s` (was 493 before this task; +6 new tests, zero regressions, zero flake this run).
5. `git diff --check` → clean (exit 0).
6. `git status --short` → only files inside `allowed_files` are new/modified (`.gitignore`, the task card, the script, the test file).

Code read end-to-end, not spot-checked: confirmed `_safe_error_message()` actually redacts
`settings.GEMINI_API_KEY` and any `?key=...` query-string pattern before anything is written to
disk (verified by the test that plants a real secret and asserts it's absent from both
`manifest.json` and `review.md`); confirmed the manifest is checkpointed after every case
(`_write_manifest` called inside the loop, not only at the end) so a mid-run crash can't lose
earlier successes; confirmed `REQUEST_INTERVAL_SECONDS = (60.0 / GEMINI_RATE_LIMIT_RPM) + 0.1`
resolves to exactly `4.1` against the real `GEMINI_RATE_LIMIT_RPM = 15` in
`app/core/constants.py` (not hardcoded, so it stays correct if the declared limit ever changes);
confirmed the CLI only ever imports `app.services.script_service.generate_script` and never
touches `app.db`/`ProjectService` — no real project or SQLite row is created, matching the
"never create a project" acceptance criterion.

**Required real 18-call run — blocked by a live external condition, not a code defect:**
Command 7 (`venv\Scripts\python scripts\generate_cefr_review_samples.py`, no flags) was
launched for real. Live output shows a mix of real Gemini `HTTP 503` ("model currently
experiencing high demand") **and real `HTTP 429` "You exceeded your current quota, please
check your plan and billing details"** — the latter is a genuine quota/billing exhaustion on
this project's Gemini API key, not the transient-overload class of 503 seen earlier today. The
CLI's own failure-handling behaved exactly as designed under real failure: each failed case is
recorded individually in `manifest.json` with the real exception type/message (secrets
redacted), earlier/later successes are unaffected, and the process is expected to exit `1`.
This independently proves the failure path for real, but does not yet supply "18/18 real
samples for human CEFR review" — that requires re-running command 7 once the account's Gemini
quota/billing is resolved. **Flagging back to the user separately**, since this may mean the
API key needs a billing/plan check on Google AI Studio, not just "wait a few minutes" as
diagnosed earlier today.

**First real-run result (2026-09-14, before the model-fallback fix):** `data/quality_reviews/script-samples/20260914T020330.711707Z/` —
`manifest.json` confirms **1/18 succeeded, 17/18 failed**, `status: completed_with_errors`, exit
code 1 (truthful, matches design). Only `B1__news` (10 lines) generated successfully; every
other case failed on real `HTTP 503` (early cases) or real `HTTP 429 "You exceeded your current
quota"` (case 2 onward, and consistently for every case from #10 through #18) — a hard quota
wall, not a flaky retry situation. PM spot-checked the manifest directly (not just the console
log): the one success is real and complete, every failure's stored `error.type`/`error.message`
matches the real exception, no secrets present.

**Second real-run result (2026-09-14, after shipping the `GEMINI_MODEL_FALLBACKS` fix —
see TRACKER.md 2026-09-14 Decision Log entries):** `data/quality_reviews/script-samples/20260914T070018.898570Z/` —
`manifest.json` confirms **11/18 succeeded, 7/18 failed**, `status: completed_with_errors`,
exit code 1. Real improvement directly attributable to the fallback chain: multiple cases only
succeeded after `gemini-3.8-flash` and `gemini-3.7-flash` both exhausted their retries on real
429/503 responses and the request fell through to `gemini-3.6-flash` (console log shows this
explicitly per case). The 7 remaining failures are a *different* failure class — real
connection-level errors (`httpx.RequestError`: "All connection attempts failed" / empty message)
rather than HTTP 429/503 — which the current design deliberately does not retry or fall back on
("any other non-200 status / connection failure fails immediately, since retrying won't fix a
bad request" — this reasoning was written for auth/bad-request errors, not transient network
drops, and is a legitimate candidate to revisit in a future task, not this one). PM verified the
manifest directly: 11 real successes (A1/A2 nearly complete, B1 complete, B2 partial, only
C1_small_talk from C1/C2), 7 failures clustered at the end of the run (`A2_news`, `B2_news`,
`C1_interview`, `C1_news`, `C2_small_talk`, `C2_interview`, `C2_news`), consistent with the
underlying network/API degrading further as the run progressed rather than anything specific to
higher CEFR levels. **This is real, usable evidence for 11 of 18 CEFR×genre combinations** — a
material improvement, though still short of full coverage. Re-running with
`--levels C1 C2 --genres interview news` (or a full re-run) once the network/API is stable again
would close the remaining gap; not done in this session since 11/18 already gives PM/user real
content to start a CEFR review pass on the levels most complete (A1–B1).

## PM Acceptance

**Code: ACCEPTED.** All `allowed_files` boundaries respected, all automated acceptance
criteria verified independently and passing, zero regressions to the existing 493 tests, doc-
first gate content is accurate now that this section has been corrected. Status below reflects
that the code is done; the campaign's "18 real samples ready for review" outcome remains
pending on the external Gemini quota condition above, so this is not the same as declaring
Task 2.1 (the parent ROADMAP item) complete.

