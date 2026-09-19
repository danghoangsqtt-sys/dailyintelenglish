# Task 13.4 — Checkpointed Script Pipeline

- **Status:** in_progress
- **Dependency:** 13.2–13.3
- **Controlling detail:** implementation plan §6 and §8, Task 13.4

## Objective

Generate scripts as outline plus validated 1–2 minute sections, checkpoint valid work,
repair only one failed section, merge with server-owned IDs, and publish atomically.

## Allowed files

Only prompt, service, worker, constants, fixture, and test paths listed for 13.4 in the
controlling plan.

## Hard checks

Valid schema; allowed speaker enum; non-empty text; correct section/input hash; per-
section ±15%; global ±10%; 35–65% word share; no exact duplicate line; repeated
normalized 8-gram ratio <1%; line IDs generated server-side. Topic/CEFR heuristics are
warnings plus human review, not unstable hard rejections.

## Verification and exit

5/8/10-minute fixtures, injected repair, fallback decision, interruption/resume,
cancel/stale race, and preservation of the prior valid script on failure all pass.

## Plan (written before implementation)

### Scope note: main.py wiring deferred, not forgotten

`app/main.py` is not in this task's allowed-file list, so `script_pipeline.py`'s
handler is built and fully tested standalone (each test constructs its own
`AIWorker` + `AIRouter` + in-memory DB, same pattern as `tests/test_ai_worker.py`)
but is **not** registered onto the app's shared `ai_worker` singleton in this task.
Wiring `ai_worker.register_handler("script", script_pipeline.make_handler(router))`
into `app/main.py`'s lifespan happens once a task with `app/main.py` in its allowed
files exists (Task 13.6 touches Step 2/3 job UX, the natural place) — recorded here
so it isn't silently lost, not treated as this task's own gap.

### Reused, not touched: `app/services/project_service.py`

Not in this task's allowed files, and doesn't need to be: `project_service.py`
already exports `mark_script_changed(db, project_id, commit=False)`, a **public**
function that already handles both the forward `draft → script_generated`
transition and the three-status downgrade in one call (built for Task 7.1/9.1) —
the pipeline's final atomic save calls this exact function, the same one
`app/api/projects.py`'s legacy save path already uses, so project-status behavior
is provably identical to the existing route, not reimplemented.

### Constants (`app/core/constants.py`)

```python
CEFR_WORDS_PER_MINUTE = {"A1": 80, "A2": 90, "B1": 100, "B2": 115, "C1": 130, "C2": 150}
```
Values copied from the already-live `prompts/script/cefr_*.txt` "Pace: target about
N words per minute" lines (checked against all 6 files) — a single source of truth
the pipeline computes from, instead of parsing prompt prose at runtime.
`SCRIPT_SECTION_TARGET_MINUTES = 1.5` (midpoint of the plan's "1-2 minute" section
spec), `SCRIPT_SECTION_WORD_TOLERANCE = 0.15`, `SCRIPT_GLOBAL_WORD_TOLERANCE = 0.10`,
`SCRIPT_SPEAKER_BALANCE_MIN_SHARE = 0.35`, `SCRIPT_SPEAKER_BALANCE_MAX_SHARE = 0.65`,
`SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5` (same value already hardcoded in
`script_base.txt`'s prose "no monologues" rule — now also a named constant the new
pipeline enforces programmatically), `SCRIPT_MAX_REPEATED_8GRAM_RATIO = 0.01`,
`SCRIPT_PIPELINE_MAX_REPAIR_ATTEMPTS = 1`.

### New prompts

- `prompts/script/outline.txt` — asks for a JSON `{title, sections: [{index,
  objective, target_words}]}` outline given topic/genre/CEFR/speakers/duration and
  the computed total target word count and section count; reuses the existing
  genre/CEFR block injection pattern (`genre_instructions`/`cefr_constraints`) so
  outline tone matches what section generation will later target.
- `prompts/script/section.txt` — asks for JSON `list[{speaker_id, text,
  language_notes}]` (no `id` field — line IDs are server-owned, per this task's
  hard-check list) for exactly one outline section, given the section's objective/
  target_words, the full speaker list, genre/CEFR blocks, language-feature
  precedence rules (reused verbatim from `script_base.txt`), and a short prior-
  section summary (plain text, last section's line count + first/last line gist)
  for continuity — never the full prior transcript, to keep prompts bounded as
  section count grows.
- `prompts/script/repair.txt` — given the failed section's own prompt context plus
  the exact validator error strings and the invalid output, asks for one corrected
  JSON section addressing every listed error.

### `app/services/script_pipeline.py` (new)

Pydantic models (not in `app/models/script.py` — not in this task's allowed
files): `OutlineSectionSpec` (`index`, `objective`, `target_words`),
`ScriptOutline` (`title`, `sections: list[OutlineSectionSpec]`), `SectionLineOut`
(`speaker_id`, `text`, `language_notes: LanguageNotesOut` — reusing
`script_service.LanguageNotesOut`, not duplicating it — **no `id` field**).

Pure functions (unit-testable without any provider/DB):
- `compute_target_words(cefr_level, duration_minutes) -> int`
- `plan_sections(target_words, cefr_level) -> list[int]` (word budget per section,
  each within `SCRIPT_SECTION_TARGET_MINUTES`'s implied size, remainder folded
  into the last section)
- `validate_section(lines, target_words, known_speaker_ids) -> list[str]` (hard
  errors: schema/speaker-enum are already enforced by Pydantic + a post-check
  before this runs; this checks §15% word envelope, unknown speaker_id, and the
  consecutive-line limit)
- `validate_global(lines, target_words, known_speaker_ids, num_speakers) ->
  tuple[list[str], list[str]]` — `(hard_errors, warnings)`: global ±10% word
  envelope, 35-65% word-share balance (skipped entirely when `num_speakers == 1`,
  same solo-override precedent as the legacy prompt), exact-duplicate-line
  detection (normalized: casefold + whitespace-collapsed), repeated normalized
  8-gram ratio (`Counter` over 8-word sliding windows of the whole normalized
  transcript). Topic relevance is a **warning only** (a low-precision keyword-
  overlap heuristic against the project topic — deliberately not a hard reject,
  per the plan's explicit instruction that this stays a warning/human-review
  signal).
- `repeated_8gram_ratio(words) -> float`, `normalize_text(text) -> str` (shared by
  both duplicate-detection and 8-gram ratio).

Orchestration: `make_handler(router: AIRouter) -> JobHandler` returns a closure
`async def _handler(job, worker): ...` (matches `app.services.ai_worker.JobHandler`)
implementing plan §6's exact 8-step script pipeline:
1. Re-fetch the project fresh (never trust the job's creation-time snapshot) under
   `read_transaction()`; recompute a config hash locally (same simple
   `sha256(json.dumps({"project": project, "operation": "script"}, sort_keys=True,
   default=str))` shape `ai_job_service.create_job` already used to produce
   `job["config_hash"]` — duplicated here as ~3 lines rather than importing
   `ai_job_service`'s private `_canonical_hash`, since `ai_job_service.py` is not
   in this task's allowed files) and compare against `job["config_hash"]`; a
   mismatch calls `ai_job_service.mark_stale()` and returns. Also checks
   `job["cancel_requested"]` before doing any generation work at all.
2. `compute_target_words` + `plan_sections`.
3. Generate (or resume from a `stage="outline"`, `section_index=0` checkpoint) the
   outline via `router.generate()` + `validation.parse_and_validate`.
4. For each outline section not already checkpointed: check `cancel_requested`
   fresh from the DB; generate via `router.generate()`; `validate_section()`; on a
   hard error, send exactly one repair request (`prompts/script/repair.txt`) and
   re-validate; on continued failure, `transition_status(..., "error",
   error_code="section_validation_failed")` and return (the prior persisted
   script, if any, is never touched — this handler never calls `save_script`
   before every section is valid); on success, `ai_job_service.save_checkpoint()`
   the section's lines, `update_progress()`, and `await worker.heartbeat(job_id)`.
5. After all sections: `transition_status(..., "validating")`, run
   `validate_global()`; a hard error transitions to `error` and returns (prior
   script untouched).
6. Re-check the config hash and `cancel_requested` **again** immediately before
   the final save (closes the exact race the plan calls out: inputs changed, or a
   cancel arrived, while the last section was generating).
7. Atomic final save: inside one `write_transaction`, assign server-side UUIDs to
   every merged line, call `script_service.save_script(..., commit=False)`,
   `project_service.mark_script_changed(db, project_id, commit=False)`, and
   `ai_job_service.transition_status(db, job_id, "complete", commit=False)` — all
   three in the same transaction, so a failure after the script write but before
   the job flips to `complete` rolls back the script write too (no
   completed-looking job with no script, and no persisted script with a job stuck
   at `validating`).
8. Any unexpected exception propagates to `AIWorker._process`'s existing
   `except Exception` handler (Task 13.3), which already transitions the job to
   `error` — the pipeline does not need its own top-level catch-all.

### `app/services/script_service.py` (edited)

`regenerate_line()` migrates from its own `_generate_with_retry`/`_call_gemini`
implementation to the Task 13.2 gateway: new `_build_ai_router() -> AIRouter`
factory (constructs `OllamaProvider`/`GeminiProvider` from `settings`, mode from
`settings.AI_MODE`); `regenerate_line(..., router: AIRouter | None = None)`
accepts an optional injected router (defaults to `_build_ai_router()` in
production, lets tests pass a `FakeProvider`-backed one with zero network calls).
Prompt rendering (`render_regenerate_line_prompt`), the `ScriptLineOut` schema
(id/speaker_id validated exactly as before), and the "model must not change
`speaker_id`" check are all byte-for-byte unchanged — only the HTTP transport
underneath changes, so every existing `tests/test_script_service.py` regression
test for `regenerate_line` must keep passing unmodified (this is the literal
meaning of "preserve line-regeneration behavior through the provider gateway").
`generate_script()` (the bulk legacy path) is **not** touched — it keeps its
existing multi-model Gemini fallback chain as the synchronous compatibility
route's implementation until Task 13.7 decides its fate; `script_pipeline.py` is
an entirely separate, additive code path for the new durable-job route.

### `app/services/ai_worker.py` (edited)

Adds a public `get_db(self)` accessor (`return self._db_getter()`) so a handler
function (which only receives `(job, worker)`) can reach the shared connection —
the smallest possible addition, no behavior change to existing methods.

### Tests

`tests/test_script_pipeline.py`: pure-function unit tests for
`compute_target_words`/`plan_sections`/`validate_section`/`validate_global`/
`repeated_8gram_ratio` (including the 3 golden fixtures' exact CEFR/duration
combinations — 5/8/10-minute A2/B1/C1 — computing their real target word counts);
full end-to-end handler tests using a `FakeProvider`-backed `AIRouter` (scripted
outline + section responses) against the real `db` fixture: happy path (valid
outline+sections → `complete`, real `script_lines` rows persisted, server-assigned
UUIDs, `mark_script_changed` called), injected single-section repair (first
response invalid, repair response valid → `complete`, repair prompt used),
repair-then-still-invalid (→ `error`, `script_lines` table empty, i.e. the prior
state — none, in a fresh project — is provably unchanged), interrupted-then-
resumed generation (checkpoint an early section, kill the handler mid-run,
re-invoke it → resumes from the checkpoint, doesn't re-call the provider for
already-valid sections), cancel-requested race (mid-section cancel →
`cancelled`, no partial script saved), and stale race (project topic changed
between claim and final save → `stale`, no partial script saved). Reuses
`tests/fixtures/ai/golden_projects.json`'s 3 real project shapes.

`tests/test_script_service.py`: existing `regenerate_line` tests unmodified
(prove behavior preservation) plus new tests injecting a `FakeProvider`-backed
router to confirm the gateway path returns the identical validated shape and
still rejects a speaker-id-changing response.

`tests/test_script_api.py`: existing HTTP tests for `POST .../script/generate`
and `POST .../script/regenerate` re-run unmodified (neither route's contract
changes in this task) — regression proof that `regenerate_line`'s transport swap
is invisible at the API layer.

### Best practices applied

AR-02 (all async, no blocking calls in the event loop), AR-04 (typed exceptions —
reuses `ai_job_service`'s existing `ValidationError`/`NotFoundError` and
`script_service`'s `ScriptGenerationError`, no new exception types needed), CR-02
(every tolerance/limit a named constant, none hardcoded inline), CR-03 (every
prompt in `prompts/`, none inlined as Python string literals), the project's
established provider-call logging convention (model/purpose/prompt_hash/latency
only, reused automatically via `AIRouter`'s own logging — the pipeline adds no
separate logging of prompt/response content).

### Verification commands

```
venv\Scripts\python.exe -m ruff check app\services\script_pipeline.py app\services\script_service.py app\services\ai_worker.py app\core\constants.py tests\test_script_pipeline.py tests\test_script_service.py tests\test_script_api.py
venv\Scripts\python.exe -m pytest tests\test_script_pipeline.py tests\test_script_service.py tests\test_script_api.py -v
venv\Scripts\python.exe -m pytest tests\ -x -q
git diff --check
```

Expected: all new/updated tests pass; existing `regenerate_line`/script-API tests
pass unmodified; full suite has no new failures beyond the documented Gemini-retry
flake class; ruff clean.
