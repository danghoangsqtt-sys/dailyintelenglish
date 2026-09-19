# Task 13.5 — Grounded Learning Pipeline

- **Status:** in_progress
- **Dependency:** 13.2–13.4
- **Controlling detail:** implementation plan §6 and §8, Task 13.5

## Objective

Generate from the persisted final-script hash, validate grounding/counts/answers,
repair failed items once, and atomically publish only if the script is still current.

## Allowed files

Only prompt, service, worker, constants, fixture, and test paths listed for 13.5 in the
controlling plan.

## Constraints

Expressions and quoted examples normalize back to the transcript; MCQ answer belongs
to options; open-ended contract remains valid; duplicates and count violations fail.
IPA, Vietnamese meaning, and grammar correctness require named human review and are not
misrepresented as dictionary-verified.

## Verification and exit

Five fixture packs pass deterministic checks; targeted failure repairs once; script edit
causes `stale`; failed/cancelled generation leaves the prior learning pack unchanged.

## Plan (written before implementation)

### Real gap found before designing: `script_hash_at_start` is never populated

`ai_generation_jobs.script_hash_at_start` (added in Task 13.3's migration) is
never written by `ai_job_service.create_job()` or `app/api/ai_jobs.py`'s route
(built in Task 13.3, before any content pipeline existed to need it) — neither
file is in this task's allowed list either, so this can't be fixed here. Given
that, "use the persisted script hash" is implemented as the pipeline's **own**
bookkeeping instead of trusting a DB column nothing populates yet: read the
script once at the start of processing, hash it locally, and compare against a
**second** read taken immediately before the final save. This closes the exact
race window the plan cares about (a script edit landing while a learning job is
mid-flight) without needing a schema/route change outside this task's files.
Recorded here honestly, the same way Task 13.4 recorded the `app/main.py`
wiring gap — a real task-4.5-adjacent to-do for whichever later task owns
`app/api/ai_jobs.py` again (likely Task 13.6), not silently worked around.
Project-level staleness (topic/genre/CEFR changed) is still checked against
`job["config_hash"]` exactly like `script_pipeline.py` does, reusing that
module's `compute_config_hash` via import (not duplicated a third time).

### Paths

New: `prompts/learning/learning_repair.txt`, `app/services/learning_pipeline.py`,
`tests/test_learning_pipeline.py`.

Edited: `app/services/learning_service.py` (no behavior change to
`generate_learning_pack()`/`save_learning_content()`/etc. — only adds a small
`compute_script_hash(script_lines)` helper the pipeline and its tests both use,
so the hashing algorithm has one home), `app/services/ai_worker.py` (none
expected — `get_db()` already added in Task 13.4 covers this pipeline's needs
too; only touched if something unforeseen comes up), `app/core/constants.py`
(new `LEARNING_*` thresholds), `tests/test_learning_service.py` (only if
`compute_script_hash` needs its own direct test — no change to existing tests),
`tests/test_learning_api.py` (re-run unmodified as a regression check — no
route changes in this task).

### Constants (`app/core/constants.py`)

`LEARNING_MIN_VOCABULARY = 1`, `LEARNING_MIN_IDIOMS = 1` (the prompt gives no
explicit target count for these two categories, unlike questions/grammar below
— "at least one" is the only honest floor to enforce without inventing an
undocumented target), `LEARNING_MIN_GRAMMAR_POINTS = 1`,
`LEARNING_MAX_GRAMMAR_POINTS = 2`, `LEARNING_MIN_QUESTIONS = 3`,
`LEARNING_MAX_QUESTIONS = 5` (both pairs copied from
`prompts/learning/learning_pack.txt`'s own stated "1-2 grammar points"/"3-5
questions" — a single source of truth, same pattern as
`SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`), `LEARNING_GENERATION_TEMPERATURE =
0.2` (low but nonzero, per plan §6 "low temperature").

### `app/services/learning_pipeline.py` (new)

Reuses `script_pipeline.normalize_text`/`compute_config_hash` via import
(not duplicated) — both are already generic, project-agnostic utilities.

Pure validators:
- `validate_counts(pack) -> list[str]` — vocabulary/idioms non-empty; grammar
  and questions within their prompt-declared ranges.
- `validate_grounding(pack, transcript) -> list[str]` — every vocabulary/idiom
  `example_sentence`, and every idiom's own `phrase`, must normalize to a
  substring of the normalized transcript ("selected expressions and quoted
  examples" from plan §6). Vocabulary's bare `word` is deliberately **not**
  grounding-checked on its own — English inflection (plural/tense) makes a
  strict substring check too fragile there; the word's actual usage is already
  covered by its `example_sentence` check.
- `validate_duplicates(pack) -> list[str]` — no duplicate (normalized)
  vocabulary word, idiom phrase, or question text.
- `validate_answers(pack) -> list[str]` — every MCQ (`options` non-empty)
  question's `correct_answer` normalizes to one of its own `options`;
  open-ended questions (`options` empty) are valid with no `correct_answer`
  requirement, per this task's own explicit constraint.
- `validate_pack(pack, transcript) -> list[str]` — the union of all 4 above.

Orchestration: `make_handler(router) -> JobHandler`:
1. Fetch project + script fresh; compare project hash to `job["config_hash"]`
   (stale on mismatch) and check `cancel_requested`.
2. If the script is empty, fail with `error_code="script_empty"` (mirrors
   `learning_service.generate_learning_pack`'s existing guard — a learning job
   should never be created for a project with no script, but this is not
   trusted blindly).
3. Hash the script locally (`learning_service.compute_script_hash`) as this
   run's start-of-processing baseline.
4. Render the existing `prompts/learning/learning_pack.txt` (via
   `render_learning_prompt`, already public in `prompt_loader.py` — no new
   prompt-loader function needed here, unlike Task 13.4's outline/section/
   repair, which had genuinely new templates), generate at
   `LEARNING_GENERATION_TEMPERATURE` through the `AIRouter`, validate via
   `validate_pack`.
5. On failure, one repair pass through a **new** `learning_repair.txt`
   (transcript + exact validator errors + previous invalid pack → corrected
   full pack, same per-pack granularity as script_pipeline's per-section
   repair, not itemized to individual vocabulary/idiom entries); re-validate;
   continued failure → `error_code="pack_validation_failed"`, transparent, no
   partial save.
6. Immediately before saving: re-fetch the script, recompute its hash, compare
   to step 3's baseline (stale on mismatch — see the gap note above); re-check
   `cancel_requested`.
7. Atomic final save: one `write_transaction` for
   `learning_service.save_learning_content(..., commit=False)` +
   `ai_job_service.transition_status(db, job_id, "complete", commit=False)`.

### Best practices applied

Same as Task 13.4: AR-02 (async, no blocking calls), AR-04 (reuses existing
typed exceptions, no new ones needed), CR-02 (every threshold named, sourced
from the prompt's own stated ranges rather than invented), CR-03 (new prompt in
`prompts/`, no inline string), and this app's now-established
disclose-not-misrepresent stance on IPA/Vietnamese quality: this task validates
**structure** (grounding, counts, duplicates, answer consistency), never
IPA/Vietnamese/grammar linguistic correctness — those stay a named human-review
gate per ADR-001, not something code claims to verify.

### Verification commands

```
venv\Scripts\python.exe -m ruff check app\services\learning_pipeline.py app\services\learning_service.py app\services\ai_worker.py app\core\constants.py tests\test_learning_pipeline.py tests\test_learning_service.py tests\test_learning_api.py
venv\Scripts\python.exe -m pytest tests\test_learning_pipeline.py tests\test_learning_service.py tests\test_learning_api.py -v
venv\Scripts\python.exe -m pytest tests\ -x -q
git diff --check
```
