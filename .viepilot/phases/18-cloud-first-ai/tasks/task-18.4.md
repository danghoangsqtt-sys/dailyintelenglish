# Task 18.4 — Fallback-rate readout + runner `--matrix cloud_first`

- **Status:** not started
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

Query: the last `limit` jobs with `status = 'complete'`, ordered by `finished_at DESC`. For each,
parse `metrics_json.calls` (defensively — `{}`/`[]` on any parse failure, matching every other
reader of this column). Returns:
```python
{
    "window": <int>,                    # jobs actually counted, <= limit
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
  jobs (`window=0`, both rates `None`, empty reason counts), all-local (both rates `0.0`), a mix
  with multiple fallback reasons (`fallback_reason_counts` sums correctly, `call_fallback_rate`
  != `job_fallback_rate` when one job has multiple fallback calls and others have none), `limit`
  actually bounding the window, a job in a non-`complete` status excluded, and a malformed
  `metrics_json` row (parse failure) not crashing the aggregate.
- `tests/test_ai_jobs_api.py`: `GET /api/ai/health` includes the new `fallback_rate` key with the
  right shape (extends the existing `expected_keys` pattern from Task 18.3).
- `tests/test_run_ai_operational_trial.py`: reuses the Task 17.2 `runner_module` fixture
  (`importlib`-based fresh load, `os.environ`/`sys.argv`/`sys.modules` snapshot-restore) —
  (a) set `sys.argv = [argv0, "--matrix", "cloud_first"]` before loading, assert
  `os.environ["DIE_AI_MODE"] == "cloud_first"` and `os.environ["DIE_AI_ALLOW_CLOUD"] == "true"`
  after import; (b) `compute_matrix_aggregates` on a small synthetic `runs` list (recorded
  evidence shape, safe fields only, no live server) asserting the three new keys are correct,
  including the `None`-when-no-calls case.

Revert-and-confirm-failure per the standing protocol: comment out the new aggregate logic (or the
new health field) and confirm the relevant new test fails, then restore.

## Verification (required)

See plan §3 "18.4". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

_pending_
