# Task 18.4 — Fallback-rate readout + runner `--matrix cloud_first`

- **Status:** done (pending PM ACCEPTED)
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** 18.3 accepted
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.4", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.4", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

The fallback rate over the last N jobs (the share of calls and of jobs) appears in health and on the Settings page. The trial runner gains `--matrix cloud_first` and records provider/model/fallback per call.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**PM review — APPROVED with two changes (C1, C2), folded into this implementation, no
re-approval needed:**
- **C1:** the window is the last N **terminal** jobs, `status IN ('complete', 'error')` —
  excluding `cancelled`/`stale`, but *not* excluding `error` — rather than `status = 'complete'`
  alone. Counting only `complete` jobs hides exactly the case D22 most needs visibility into: a
  job where the cloud call failed AND the fallback didn't save it either. `get_fallback_rate_stats`
  also returns a per-status breakdown of the window, `"by_status": {"complete": <int>, "error":
  <int>}`, so the readout distinguishes "the fallback covered for cloud outages" from "jobs are
  still failing outright."
- **C2:** the runner unit test asserts `DIE_AI_MODE`/`DIE_AI_ALLOW_CLOUD` are restored to their
  pre-test values after the `runner_module` fixture tears down — not just that they're correct
  *during* the test. This matters specifically because `tests/conftest.py`'s N1 fix
  (`_neutralize_cloud_config()`) depends on `AI_ALLOW_CLOUD=False` holding for the whole pytest
  session; a `--matrix cloud_first` test that leaked `DIE_AI_ALLOW_CLOUD=true` into
  `os.environ` after its own fixture exited would reintroduce exactly the class of session-wide
  cloud-config leak N1 closed. (The existing `runner_module` fixture already restores the full
  `os.environ` snapshot in its `finally` — this is a new assertion confirming that restore
  actually covers these two keys, not a new restore mechanism.)

**Current state, read before designing:** Task 14.2's call telemetry already gives this task
almost everything it needs, unchanged — every AI call already appends a safe-fields-only record
(`provider`, `model`, `fallback_used`, `fallback_reason`, `outcome`, no prompt/response/key) to
its job's `metrics_json.calls` (`ai_job_service.record_generation_call`), and the job row already
carries aggregate `fallback_used`/`fallback_count`/`fallback_reason` columns
(`006_ai_generation_jobs.sql`). `fallback_reason` is `type(exc).__name__` on the `ProviderError`
subclass that triggered the fallback (`router.py:225`) — e.g. `ProviderRateLimitError`,
`ProviderUnavailableError`, `ProviderTimeoutError`, `ProviderAuthError` — already exactly the
RateLimit/Unavailable/Timeout/Auth breakdown point 1 asks for, no new plumbing needed to produce
it. The trial runner's `run_script_trial` (`scripts/run_ai_operational_trial.py`) already stores
each run's full `metrics` dict (including `calls`) in its per-run record, via the existing
`AIJobOut.metrics` field — so "records provider/model per call" (point 3) is also already true
today; this task adds only the *aggregation* over that existing data, on both sides (app +
runner), never a new recording mechanism.

### 1. `fallback_rate`: precise definition (point 1)

New `ai_job_service.get_fallback_rate_stats(db, limit=FALLBACK_RATE_WINDOW) -> dict` — a
read-only aggregate, no new tables/columns/migration. `FALLBACK_RATE_WINDOW = 50` is a
module-level constant in `ai_job_service.py` itself (`app/core/constants.py` is not in this
task's allowed files, and the constant is meaningful only to this one aggregate).

Query: the last `limit` jobs with `status IN ('complete', 'error')` (C1), ordered by
`finished_at DESC`. For each, parse `metrics_json.calls` (defensively — `{}`/`[]` on any parse
failure, matching every other reader of this column). Returns:
```python
{
    "window": <int>,                    # jobs actually counted, <= limit
    "by_status": {"complete": <int>, "error": <int>},  # C1: window composition
    "call_fallback_rate": <float|None>, # point 1(a): fallback calls / total calls
    "job_fallback_rate": <float|None>,  # point 1(b): jobs with >=1 fallback call / window
    "fallback_reason_counts": {str: int},  # point 1(c): count per fallback_reason among fallback calls
}
```
`job_fallback_rate` reads the job row's own `fallback_used` column directly (already correct per
job, set by `record_generation_call`) rather than re-deriving it from `calls` — cheaper and can't
drift from what `record_generation_call` itself decided. `call_fallback_rate` and
`fallback_reason_counts` iterate `calls[]` since those need per-call granularity the job row
doesn't carry. Both rates are `None` (not `0.0`) when their denominator is zero — an empty
install has no fallback rate yet, not a `0%` one, so the UI/health payload can render "no data"
distinctly from "reads as 0%, still meaningful."

D22 (owner decision, restated): this is a **decision input**, never a gate — nothing in this task
adds `fallback_rate` to any pass/fail check anywhere.

### 2. Where it's shown (point 2)

- **Health:** `GET /api/ai/health` gains one nested `"fallback_rate": {...}` key (the dict above,
  verbatim) — `app/api/ai_jobs.py`'s `ai_health()` gains a `db: aiosqlite.Connection =
  Depends(get_db)` param (it has none today) and calls `get_fallback_rate_stats(db)` inside a
  `read_transaction()`, same pattern every other route in this file already uses. Additive only;
  no existing health field changes (matches Task 18.3's own additive precedent for this
  endpoint).
- **Settings page:** one new display line, `#fallback-rate-status` in `settings.html`'s "AI
  Provider" card, right after `#effective-mode-status`. `settings.js` gains
  `renderFallbackRate(health)` + `loadFallbackRate()` (calls the existing `Api.getAiHealth()` —
  already defined in `api.js`, no new API-client method needed), called once alongside the
  existing `loadStatus()` at page load. Renders e.g. "Fallback rate (last 50 jobs): 12% of calls,
  8% of jobs." or "No completed AI jobs yet." when `window` is 0. No key material anywhere in
  this payload (inherits the existing invariant — `fallback_rate` is a new derived field, not a
  new read path into stored settings).

### 3. Runner `--matrix cloud_first` (point 3)

- Argparse: `--matrix` choices become `("local", "gemini", "cloud_first")`.
- Env, same sys.argv-before-import pattern the file already uses for `--matrix`/`--mode`
  (argparse itself runs too late — `Settings()` is a module-level singleton read at import time):
  right after the existing `os.environ["DIE_AI_MODE"] = _MODE` line, add
  ```python
  if _MODE == "cloud_first":
      os.environ["DIE_AI_ALLOW_CLOUD"] = "true"
  ```
  This is the only new env-setting code the runner needs — `_MODE` already becomes
  `DIE_AI_MODE` for any value handed to `--matrix`/`--mode` (existing code, unchanged), so
  `--matrix cloud_first` already sets `DIE_AI_MODE=cloud_first` today; the one gap is
  `DIE_AI_ALLOW_CLOUD`, which this task closes explicitly rather than relying on `.env`'s default
  (now `true` per Task 18.3's Amendment C, but the runner must not depend on that — an install
  with a `.env` override to `false` must not silently run a "cloud_first" trial in local-only
  mode). The key itself is never touched by the runner — it's already in the process env/`.env`
  (`DIE_OPENAI_COMPAT_API_KEY`), read the normal way `Settings()` reads any env var; the runner
  is not pytest, so it legitimately uses the owner's real key for a real trial (unlike every test
  in this suite, which never may — `tests/conftest.py`'s `_neutralize_cloud_config()`).
- Per-run recording: unchanged, already correct (see "current state" above) — `run_script_trial`
  already stores `record["metrics"]["calls"]` (provider/model/fallback_used/fallback_reason per
  call) and `record["fallback_count"]`/`record["actual_provider"]`/`record["model"]` at the job
  level. Nothing in this task touches key material — the call record shape (`_call_record` in
  `script_pipeline.py`/`learning_pipeline.py`, safe fields only) is Task 14.2's, outside this
  task's allowed files, and was never going to change.
- Key never reaches evidence JSON or console logs: verified, not newly enforced — every field
  this task reads or prints (`job.get("actual_provider"/"model"/"fallback_...")`,
  `AIJobOut.metrics`, `/api/ai/health`'s payload) already excludes the key by construction
  (Task 14.2's call-record shape, Task 18.3's health payload). This task adds no new read path
  into `OPENAI_COMPAT_API_KEY`.

### 4. Aggregates + decision logic stay separate (point 4)

`compute_matrix_aggregates(runs)` gains three new keys, computed the same way
`total_fallback_count` already is (iterate the same `runs` list, `.get(...)` throughout so it
still works unchanged for `--reaggregate` on old evidence files that predate this task):
`call_fallback_rate`, `job_fallback_rate` (both `None` if no denominator), and
`fallback_reason_counts` — same three-key shape as point 1's `get_fallback_rate_stats`, computed
over this one matrix run's `runs` list instead of the last-50-jobs DB window (the two are
independent readouts: one process-wide/DB-wide for the health/Settings display, one per-trial for
gate evidence — deliberately not sharing code, since one reads `aiosqlite`/DB rows and the other
reads already-fetched HTTP response dicts).

Decision logic itself: **zero changes**. `matrix == "cloud_first"` is not special-cased anywhere
in `main()` — only `matrix == "gemini"` is (samples/media defaults, `gemini_matrix_decision`).
`cloud_first` therefore already falls through to the exact same `else` branch `"local"` and
`None` use today: `run_samples`/`run_media` default on, `local_full_decision` (13.9-verbatim
thresholds, pinned) decides PASS/FAIL. The new `fallback_rate` fields land in
`evidence["aggregates"]` only — never read by `local_matrix_decision`/`local_full_decision`,
matching D22 exactly ("report... as information only... not gated"). One `print(...)` line added
after the existing decision-reasons loop in `main()`, reporting the run's `call_fallback_rate`
for visibility — cosmetic, no effect on `evidence["decision"]`.

### 5. Tests (point 5)

No real API calls anywhere in this task's own tests (matches every other task in this phase).
- `tests/test_ai_job_service.py`: `get_fallback_rate_stats` on seeded rows inserted directly via
  `db.execute(...)` against the `db` fixture (in-memory SQLite, migrations applied) — cases: no
  jobs (`window=0`, both rates `None`, empty reason counts, `by_status={}`), all-local (both
  rates `0.0`), a mix with multiple fallback reasons (`fallback_reason_counts` sums correctly,
  `call_fallback_rate` != `job_fallback_rate` when one job has multiple fallback calls and others
  have none), an **`error`-status job whose calls include a fallback attempt** (C1 — confirms it's
  counted in the window and in `by_status["error"]`, not silently dropped), `limit` actually
  bounding the window, a `cancelled`/`stale` job excluded, and a malformed `metrics_json` row
  (parse failure) not crashing the aggregate.
- `tests/test_ai_jobs_api.py`: `GET /api/ai/health` includes the new `fallback_rate` key with the
  right shape, including `by_status` (extends the existing `expected_keys` pattern from Task
  18.3).
- `tests/test_run_ai_operational_trial.py`: reuses the Task 17.2 `runner_module` fixture
  (`importlib`-based fresh load, `os.environ`/`sys.argv`/`sys.modules` snapshot-restore) —
  (a) set `sys.argv = [argv0, "--matrix", "cloud_first"]` before loading, assert
  `os.environ["DIE_AI_MODE"] == "cloud_first"` and `os.environ["DIE_AI_ALLOW_CLOUD"] == "true"`
  while the fixture is active; (b) **C2** — after the fixture tears down (a second, nested check
  or a follow-up assertion once the `with`/fixture context exits), assert `DIE_AI_MODE`/
  `DIE_AI_ALLOW_CLOUD` are back to their pre-test values (whatever `tests/conftest.py`'s
  `_neutralize_cloud_config()` set them to, i.e. `AI_ALLOW_CLOUD` reads `False` again once the
  fixture's `os.environ` restore has run) — guards against this exact test reintroducing the
  class of session-wide leak N1 closed; (c) `compute_matrix_aggregates` on a small synthetic
  `runs` list (recorded evidence shape, safe fields only, no live server) asserting the three new
  keys are correct, including the `None`-when-no-calls case.

Revert-and-confirm-failure per the standing protocol: comment out the new aggregate logic (or the
new health field) and confirm the relevant new test fails, then restore.

## Verification (required)

See plan §3 "18.4". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

- Design commit `f30b593` (APPROVED with C1/C2), this implementation commit folds both in per
  "no re-approval needed."
- **Code:**
  - `app/services/ai_job_service.py`: `FALLBACK_RATE_WINDOW = 50` and new
    `get_fallback_rate_stats(db, limit=FALLBACK_RATE_WINDOW)` — read-only aggregate over the last
    `limit` jobs with `status IN ('complete', 'error')` (C1). Returns `{window, by_status,
    call_fallback_rate, job_fallback_rate, fallback_reason_counts}`; both rates `None` when their
    denominator is zero. No new table/column/migration.
  - `app/api/ai_jobs.py`: `ai_health()` gained a `db` dependency and a new `"fallback_rate"` key
    in its payload (additive; every existing field unchanged).
  - `frontend/pages/settings.html`/`settings.js`: one new `#fallback-rate-status` line, reading
    the existing `Api.getAiHealth()` (no new API-client method needed).
  - `scripts/run_ai_operational_trial.py`: `--matrix` gained the `cloud_first` choice; right
    after the existing `DIE_AI_MODE` assignment, `--matrix cloud_first` now also sets
    `DIE_AI_ALLOW_CLOUD=true` (explicit, not relying on `.env`'s default). `compute_matrix_
    aggregates` gained `call_fallback_rate`/`job_fallback_rate`/`fallback_reason_counts`, computed
    over the matrix run's already-fetched `runs` list (each run's `metrics.calls`, already
    recorded unchanged since Task 14.2). Decision logic untouched: `cloud_first` was never
    special-cased in `main()` (only `"gemini"` is), so it already falls into the same branch
    `"local"` uses — `local_full_decision`, thresholds pinned (D22: fallback rate stays
    informational, added to `evidence["aggregates"]` only). One `print(...)` line reports
    `call_fallback_rate` after the decision-reasons loop, cosmetic only.
- **Tests (13 new, 1060 total):**
  - `tests/test_ai_job_service.py` (+7): empty window, all-local (0.0 not None), mixed reasons
    and rates (call rate != job rate), **C1** — an `error`-status job with a fallback call is
    counted (`by_status`, `job_fallback_rate`), `cancelled`/`stale` excluded, `limit` bounds the
    window, malformed `metrics_json` doesn't crash the aggregate.
  - `tests/test_ai_health_api.py` (+2): the `fallback_rate` key's shape with an empty window
    (extends the existing `expected_keys` allowlist test), and a whitebox pass-through test
    (monkeypatches `ai_job_service.get_fallback_rate_stats` — the aggregation math itself is
    covered at the service layer, not re-derived here).
  - `tests/test_run_ai_operational_trial.py` (+4): a new `_runner_module_with_argv` helper
    (same importlib/env/argv snapshot-restore pattern as the existing Task 17.2 `runner_module`
    fixture, parameterized by argv) — `--matrix cloud_first` sets both env vars while active,
    and **C2** — both are back to their pre-test values once the context exits (guards against
    reintroducing the class of session-wide leak `tests/conftest.py`'s N1 fix closed); two
    `compute_matrix_aggregates` tests on synthetic `runs` lists (no live server, no real API
    calls) covering the no-calls-is-`None` case and the mixed-reasons case.
- **Revert-and-confirm-failure:**
  - C1: temporarily reverted `get_fallback_rate_stats`'s filter to `status = 'complete'` only →
    `test_get_fallback_rate_stats_includes_error_jobs_with_fallback_calls` failed
    (`assert 0 == 1`, the error job's window dropped to 0) as expected; restored, 7/7 passed
    again.
  - C2: temporarily commented out the `os.environ.clear()`/`update(env_snapshot)` restore in the
    new `_runner_module_with_argv` fixture → `test_matrix_cloud_first_sets_ai_mode_and_allow_
    cloud_env_vars` failed, showing `DIE_AI_MODE`/`DIE_AI_ALLOW_CLOUD` had genuinely leaked into
    the real `os.environ` (`'cloud_first' == None` assertion failure) — confirmed the assertion
    actually catches a leak, not just checks a value that was already correct; restored, 6/6
    passed again. No secret material involved (these two env vars carry no key), so this check
    ran directly in terminal output, unlike the N1/N2 key-adjacent checks.
- **Full suite:** **1060 passed** (1047 baseline + 13 new). `ruff check .` → all checks passed.
  Real DB untouched throughout (the conftest guard never tripped).
- Settings page: `tests/test_settings_browser.py` (all 7, unchanged) still pass with the new
  `#fallback-rate-status` line and `loadFallbackRate()` call added — the new fetch degrades
  silently (empty text) on error, so it never blocks the existing mocked flows.
