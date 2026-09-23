# Phase 16 Implementation Plan — Stability Hardening

**Status:** CLOSED 2026-09-23 (D20: after Gate B-7; 16.6/16.7 not run; ENH-010 logged). Controlling plan, PM, 2026-09-23. The owner opened this phase through `/vp-evolve` on
2026-09-23, after a `/vp-audit` stability pass.
**Predecessors:** the Phase 13–15 plans (still controlling where not amended), ADR-001 (+A1, A2).
**Requests closed by this phase:** BUG-022, ENH-008, ENH-009, BUG-023
(`.viepilot/requests/`).

## 1. Why this phase exists

The 2026-09-23 audit ran the full suite (932/932: 771 unit/API + 161 browser), `ruff` (clean),
`scripts/check_dependencies.py` (all green) and a read-only `PRAGMA integrity_check` of
`data/app.db` (`ok`). The foundation is sound. It still found four gaps between "works" and
"stable":

| Request | Gap | Why it matters |
|---|---|---|
| BUG-022 | `AIWorker._run_loop` has no top-level guard | One transient DB error (for example `database is locked` while the owner has `app.db` open in a DB browser) ends the worker task silently. The server and `/health` stay green, but every new AI job stays `pending` until the app restarts. |
| ENH-008 | `subprocess.run` for ffmpeg has no `timeout` | A hung ffmpeg leaves a video `rendering` forever, with no retry. |
| ENH-009 | Script repetition gate: 5/5 at B-5, 3/5 at B-6 | The only remaining variable failure class in the core pipeline. |
| BUG-023 | 419 leftover test projects in the real `data/app.db`; CHANGELOG has no Phase 15 entry | The Dashboard is cluttered. The leak path is not yet identified (the newest leaked row, 2026-09-22T09:51Z, is from a full-suite run; the split runs on 2026-09-23 leaked nothing). |

## 2. Owner decisions (2026-09-23, recorded verbatim in TRACKER Decision Log)

- **D18. ENH-009:** do the prompt first; add a second repair only if needed. Strengthen the
  section prompt's avoid list from the real Gate B-6 evidence (16.4) and measure it (Gate B-7,
  16.5). Build a second bounded repetition repair (16.6) **only if** Gate B-7's script gate is
  below 5/5. The 1% threshold is not negotiable.
- **D19. BUG-023:** delete the leaked test projects from the real DB, **with a backup**. A
  dry-run comes first, and the owner sees its output before the real run. Only the four known
  fixture names are eligible.

## 3. Invariants (in addition to Phase 13 §2, Phase 14 §2 and Phase 15 §2)

24. **Thresholds unchanged.** `SCRIPT_MAX_REPEATED_8GRAM_RATIO`, both word tolerances and
    `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER` stay pinned for the whole phase.
25. **The worker never dies silently.** After 16.1, any exception inside the poll loop is
    logged and the loop continues. The worker's liveness is observable over HTTP.
    `asyncio.CancelledError` is never swallowed.
26. **The real `data/app.db` is only written in 16.3's cleanup, and only by the PM.** It
    happens after a backup and after the owner has seen the dry-run. The Coder may open it
    read-only (`mode=ro`) for investigation.
27. **Evidence, not guesses, for prompt changes.** Every phrase or rule 16.4 adds to a prompt
    must trace to a repeated 8-gram actually observed in the Gate B-6 evidence (or B-7 for
    16.6), and the trace is recorded in the task card.

## 4. Tasks

Order: **16.1 → 16.2 → 16.3 → 16.4** (Coder, sequential; each card doc-first, and the PM
approves the card's *Design decisions* before any code) **→ 16.5** (PM, Coder idle) **→ 16.6**
(Coder, only if D18's condition triggers) **→ 16.7** (PM, Gate B-8, only if 16.6 ran) **→**
close-out.

### 16.1 — Worker loop guard + liveness (BUG-022, P0, Coder)

**Allowed files:** `app/services/ai_worker.py`, `app/api/ai_jobs.py` (health payload only),
`app/core/constants.py`, `tests/test_ai_worker.py`, `tests/test_ai_health_api.py`,
`tests/test_ai_jobs_api.py` (health assertions only), `CHANGELOG.md`.

**Design:**
1. `_run_loop` wraps each iteration in `try/except Exception`: `logger.exception
   ("ai_worker_loop_error ...")`, then waits a bounded backoff on `_stop_event`
   (new constant `AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS`, e.g. 5.0), then continues.
   `CancelledError` propagates.
2. In `_process`, the error-transition inside the handler's `except` is itself guarded.
   An illegal transition (for example, the handler already committed a terminal status
   and then raised) is logged with `ai_worker_error_transition_failed`, not raised.
3. `start()` attaches a done-callback that logs at `ERROR` if the task ever ends
   while `_stop_event` is unset (belt and braces). A public `is_alive` property returns
   `task is not None and not task.done()`.
4. `/api/ai/health` adds `worker_alive: bool`. The existing fields stay unchanged.

**Verification:** `_claim_next` raises once, and the loop then still claims and completes a
later job. A handler raises after committing `complete`, and the loop survives. Stop still
honours the grace period. `CancelledError` is not swallowed. The health field reflects a dead
task. Revert-and-confirm-failure on the loop-survival test. Full suite, `ruff`.

### 16.2 — ffmpeg timeouts (ENH-008, P1, Coder)

**Allowed files:** `app/services/video_service.py`, `app/core/constants.py`,
`tests/test_video_service.py`, `CHANGELOG.md`.

**Design:** both `subprocess.run` calls pass `timeout=`. The main render uses
`max(VIDEO_RENDER_TIMEOUT_MIN_SECONDS, VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND ×
audio_duration_seconds)`; the vertical pass uses the same formula on the same duration
(new constants, suggested 300 s and 4.0). `subprocess.TimeoutExpired` becomes a
`VideoRenderError("ffmpeg ... timed out after N s")`, so the existing error path marks the
job `error` and the user can retry. `subprocess.run` already kills the child on timeout;
partial output files are removed.

**Verification:** a fake command that sleeps past a tiny patched timeout produces a
`VideoRenderError` and a job in `error`, and removes the partial file. Normal-render tests are
unchanged. Revert-and-confirm-failure. Full suite, `ruff`.

### 16.3 — Test-data leak: root cause, guard, cleanup tool, CHANGELOG (BUG-023, P1, Coder → PM)

**Allowed files:** `tests/conftest.py`; whichever test files are identified as the leak
source (named in the card's design section **before** editing); new
`scripts/cleanup_test_projects.py`; new `tests/test_cleanup_test_projects.py`;
`CHANGELOG.md` (the missing Phase 15 entry plus this task).

**Design:**
1. **Investigate first** (record the findings in the card): reproduce with one full-process
   `pytest -q` run (unit + browser together, as on 2026-09-22), comparing the real DB's
   project count before and after (read-only). A likely suspect to confirm or eliminate:
   `Database` is a process singleton, and `connect()` returns the already-open connection.
   A test that opens it against the real `DATA_DIR` and never closes it would make every
   later `TestClient(app)` lifespan reuse the real DB, even after `DATA_DIR` is
   monkeypatched.
2. **Guard:** an autouse session-level safeguard in `tests/conftest.py` that fails loudly
   if any test opens the real `data/app.db` (for example, by asserting the singleton's
   path is under a tmp dir, or by resetting `Database._instance` between tests). The
   exact mechanism is chosen in the card.
3. **Cleanup tool:** `scripts/cleanup_test_projects.py`:
   - `--dry-run` is the default and prints counts per name plus ids.
   - `--apply` first copies `app.db` to `data/backups/app-before-cleanup-<UTC>.db`, then
     deletes only projects whose `name` is exactly one of `Learning API Test Episode`,
     `YouTube API Test Episode`, `Export API Test Episode`, `Script API Test Episode`.
   - Deletion uses the same service path as the API's delete route, so cascaded rows and
     per-project directories are removed.
   - `--db` and `--data-dir` are overridable, so tests run it against a tmp copy.
4. **The Coder never runs `--apply` on the real DB.** The PM runs the dry-run and shows the
   owner, then runs `--apply` (invariant 26).

**Verification:** the guard test fails when the leak is reintroduced
(revert-and-confirm-failure). A full single-process `pytest -q` leaves the real DB's project
count unchanged. The cleanup script's tests on a tmp DB confirm that only exact names are
deleted, a backup is written, and dry-run writes nothing. `ruff`.

### 16.4 — Repetition: evidence-driven avoid list (ENH-009 step A, P0, Coder)

**Allowed files:** `prompts/script/section.txt`, `prompts/script/repair.txt`,
`app/services/script_pipeline.py` (avoid-phrase selection only),
`app/core/constants.py`, `tests/test_script_pipeline.py`, `tests/test_prompt_loader.py`,
`tests/fixtures/ai/*`, `CHANGELOG.md`.

**Design (doc-first; the card's evidence section is reviewed by the PM before code):**
1. **Evidence:** from `data/quality_reviews/phase15/gate-b6/` (the JSON reports and
   `trial-data/app.db`, both read-only), extract the repeated 8-grams of every B-6 script
   run, the two failures (runs 2 and 5) first, including the checkpointed sections.
   Classify each into:
   - *framing* (show openers and closers, "that's a great point" style transitions, topic
     restatements), or
   - *content* (the topic's own key terms, which will naturally recur).
   Put the table in the card.
2. **Known gap to address:** today's `avoid_phrases`
   (`frequent_repeated_phrases`, top `SCRIPT_SECTION_AVOID_PHRASES_MAX = 8`) only lists
   8-grams that have *already* repeated. The second occurrence, the one that creates the
   repeat, is never prevented. The Coder proposes a fix, for example:
   - also pass each prior section's opening and closing line (bounded) as "already said,
     don't reuse the framing"; and/or
   - add a static rule block in `section.txt` against the framing patterns seen in step 1
     (patterns, not the topic's content words).

   The Coder recommends one option in the card, bounded in prompt size.
3. Thresholds unchanged (invariant 24). No new repair pass in this task.

**Verification:** unit tests for the new selection logic, including the bound and the
empty case. A render test of `section.txt` with the new block. The prompt-contract tests
still pass. Revert-and-confirm-failure on the selection test. Full suite, `ruff`. Real-model
effect is measured only in 16.5.

### 16.5 — Gate B-7, local only (PM, Coder idle)

Same protocol as Gate B-6 (5 × B1 8-min script samples + the level matrix + the owner's A2 /
small_talk / 10-min configuration ×2, fresh trial DB, `OLLAMA_NUM_PARALLEL=1`), per-gate path
`data/quality_reviews/phase16/gate-b7/`. Report: `docs/operations/phase16-gate-b7.md`.
**Script gate:** 5/5 complete. **Any regression** on B-6's passing gates (structural 0,
learning, media duration, A/V) is a FAIL, whatever the script result.

### 16.6 — Second bounded repetition repair (ENH-009 step B, Coder; conditional)

**Runs only if** Gate B-7's script gate is < 5/5 on repetition. Allowed files as for 16.4.
`SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS` goes from 1 → 2. The second pass targets the
**next-worst** section by the current attribution (`find_repeated_8grams_by_section`),
never the same section twice. It stays bounded and separate from the other repair
budgets. Design details go in the card after B-7's evidence. Then **16.7 — Gate B-8** (PM),
with the same protocol as 16.5.

## 5. Stop conditions and rollback

- Any file outside a task's allowed list → stop and ask the PM to amend this plan first.
- Any threshold change → stop (invariant 24).
- A pre-existing test fails on an unmodified baseline → report to the PM, don't "fix" it
  inside a task.
- Rollback: each task is its own revert-able commit pair (card commit, then implementation
  commit). 16.4 and 16.6 are independently revertible. `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS
  = 1` restores pre-16.6 behaviour without a revert.

## 6. Two-session execution protocol

Same as Phase 14 §10, with a live message channel added:

- **PM** (Claude Opus, session "Phân tích mã nguồn dự án" [885a58]) owns `docs/**`,
  `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`,
  `.viepilot/requests/**`. PM owns `.viepilot/phases/16-stability-hardening/**` until the
  handover commit (the commit that adds this plan); **after it, the Coder owns that folder**
  and the PM requests edits.
- **Coder** (Claude Sonnet) owns `app/**`, `tests/**`, `scripts/**`, `prompts/**`,
  `README.md`, `CHANGELOG.md`, `.env.example`, packaging files.
- **Only the PM** runs `scripts/run_ai_operational_trial.py`, the real-DB cleanup, and gate
  runs. Before any of them, the PM messages the Coder and waits for "idle".
- **Messages:** `SendMessage` between the two local sessions (`ListAgents` shows the
  name). A message states the task id and the commit sha. Git is the record: anything that
  matters (design, evidence, review verdict) must also be in the task card (Coder) or
  TRACKER (PM). A message alone is not a record.
- **Per task:**
  1. Coder writes the card's *Design decisions* section, commits (`docs(phase16): Task
     16.x design`), pushes, and messages the PM.
  2. PM reviews and replies `APPROVED` or `CHANGES: …` (also recorded in TRACKER).
  3. Coder implements, commits (`fix|feat(...): Task 16.x ...`), pushes, and messages the PM
     with the sha plus the full-suite count.
  4. PM reviews the diff independently (re-runs tests, and does its own
     revert-and-confirm-failure check on the key test), then records acceptance.

  A task is done only when the card, PHASE-STATE and TRACKER agree.
- Both: `git pull --rebase origin main` before every commit, explicit `git add <path>`,
  small commits pushed immediately. Never `git add -A`, never force-push, never stop the
  dev server on port 8000.
- Baseline: 932/932, `ruff` clean (2026-09-23 audit).

## 7. Amendments

**Amendment A (PM, 2026-09-23, on accepting 16.1 `56bb74b`):** 16.2's allowed files gain
`tests/test_ai_health_api.py`, **only** to fix nit N3: in
`test_health_reports_worker_alive_false_when_the_worker_task_is_dead`, the monkeypatched
`_task = None` is still in place when the `client` fixture's lifespan calls `stop()`, so
`stop()` returns early and the real loop task is orphaned. Fix: save the real task and restore
it before the `TestClient` context exits (for example with try/finally inside the test, or a
dummy already-finished task instead of `None`). No other change to that file.

**Amendment B (PM, 2026-09-23, on reviewing the 16.2 design in `17cb199`):** 16.2 renders to a
temporary sibling file and swaps it in only on success. Both ffmpeg passes write to
`video.rendering.mp4` / `video_vertical.rendering.mp4` (the `.mp4` extension is kept so ffmpeg
still infers the container). On `returncode == 0` the temp file replaces the final path with
`os.replace`. On timeout **or** any other failure, only the temp file is removed.
Why: `-y` truncates the final `video.mp4` the moment a re-render starts. A failed or timed-out
re-render therefore destroys the previous good video, while `mark_video_job_failed`
(BUG-017) deliberately keeps the DB row pointing at it. Deleting the "partial output" at the
final path, as drafted, would make that row point at a missing file.
This changes **only the output path argument**. Every other ffmpeg argument (including the
Task 14.10 `-t` pacing) stays byte-identical, and the "don't change the command arguments"
prohibition is amended for this narrow purpose only.
New required test: an existing `video.mp4` with known content survives a timed-out
re-render unchanged.

**Amendment C (PM, 2026-09-23, on approving the 16.3 design in `48e52b6`):**
- Root cause accepted as diagnosed. 24 `*_browser.py` files each carry a copy-pasted,
  module-scoped `live_server_url` fixture that starts a real uvicorn server running the real
  lifespan. 21 of them never isolate `settings.DATA_DIR`, so `init_db()` opens the process
  singleton against the real `data/app.db`. `Database.connect()` then reuses that stale
  connection for the next `TestClient(app)`, even though that test monkeypatched `DATA_DIR`.
- **One shared helper, not 21 more copies.** The drift between copies (3 correct, 21 not) *is*
  the root cause. The fix is a single live-server helper in `tests/conftest.py` that:
  1. isolates `settings.DATA_DIR` to `tmp_path_factory`;
  2. starts uvicorn and waits for the port;
  3. on teardown sets `should_exit`, joins the thread with a bounded timeout, and **fails
     loudly** if the thread is still alive or the `Database` singleton is still connected;
  4. restores `DATA_DIR`.

  All 24 browser files' `live_server_url` fixtures become thin calls to it. The 3 already-correct
  files are added to 16.3's allowed files, for this migration only.
- **Guard, strengthened.** The conftest `Database.connect` wrapper fails if:
  - (a) the resolved `settings.db_path` is the real `<project root>/data/app.db`, computed
    independently of `settings`; or
  - (b) an already-open connection is about to be reused while `settings.db_path` differs from
    the path it was opened with. This is the exact stale-reuse mechanism, and it catches it
    for tmp paths too.

  `app/db/database.py` itself is still not modified.
- Revert check: remove the isolation step from the shared helper; the guard must fail the
  run immediately.

**Amendment D (PM, 2026-09-23, on the Coder's stop report during 16.3):** the new guard caught
a pre-existing isolation gap. `tests/test_ai_health_api.py::test_health_response_has_no_extra_undeclared_fields`
uses a bare `TestClient(app)` with no `DATA_DIR` override, so since Task 13.6 its lifespan has
opened the real `data/app.db`. It was never visible because the test is GET-only. 16.3's allowed
files gain `tests/test_ai_health_api.py`, **only** to isolate that one test (use the file's
existing `client` fixture, or `tmp_path` + `monkeypatch.setattr(settings, "DATA_DIR", ...)`).
No other change to that file. Any further guard trip found in the final run follows the same
rule: stop and report; don't widen scope unilaterally.

