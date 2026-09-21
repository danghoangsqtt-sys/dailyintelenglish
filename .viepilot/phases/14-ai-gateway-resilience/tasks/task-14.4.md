# Task 14.4 — Gate B Second Run, Both Providers

- **Status:** in_progress (14.4a only -- 14.4b is PM's)
- **Owner:** 14.4a Coder (runner preparation); 14.4b PM (execution and report)
- **Priority:** P1
- **Dependency:** 14.1, 14.2, 14.3 merged and PM-reviewed; 14.4a before 14.4b
- **Controlling detail:** plan §4.4, §6 Task 14.4

## Objective

Measure, under a protocol declared before any run, whether each provider can now
complete real eight-minute script jobs, separating infrastructure failures (503/429/
timeout/quota) from content failures (word count), and quantifying repair, backoff, and
per-section behaviour. The result selects the rollout mode for Task 13.10 (14.6).

## 14.4a — Runner preparation (Coder)

**Allowed files:** `scripts/run_ai_operational_trial.py` only.

**Required changes:**

1. Failure class per run from `error_code`: `infra` if it starts with `provider_`;
   `content` for `section_validation_failed`/`global_validation_failed`; `other`
   (including `handler_exception`) otherwise. Keep the existing word-count breakdown.
2. Read `metrics.calls[]` from the job API per run and report: total attempts, total
   backoff seconds, max attempts on one call, absorbed transient errors
   (`sum(attempts − 1)` over calls that ended `ok`), `repair_count`, `fallback_count`,
   `actual_provider`, `model`.
3. Per-section table from the trial DB `ai_generation_checkpoints.metrics_json`
   (`stage='section'`): nominal, effective, actual words, deviation %, repaired,
   words before repair.
4. Aggregates per matrix: completion rate; content pass rate; infra failure count;
   per-section within-±15%-of-nominal rate; repair success rate (repairs that ended
   inside ±15% of effective); mean/σ section deviation; totals vs 720–880; total
   backoff seconds; max attempts observed.
5. `--matrix local|gemini` (replaces ad-hoc `--mode` use for gates; keep `--mode` for
   raw diagnostics): local matrix = Phase 13 13.9 protocol verbatim; Gemini matrix =
   5 × B1 eight-minute + learning per completed script, samples optional
   (`--with-samples`), media pipeline optional (`--with-media`), `AI_MODE=gemini`.
6. Decision output per plan §4.4: local → PASS/FAIL (13.9 rule); Gemini → PASS-cloud /
   FAIL-CONTENT / FAIL-INFRA; any `handler_exception` flagged as a defect. Partial
   matrix stays `DIAGNOSTIC_ONLY`. A two-day split of the Gemini matrix is supported by
   `--resume-evidence <json>` so five runs across two files aggregate as one matrix.
7. `has_outro` false negative (disclosed in the Phase 13 report): treat the final line
   as an outro when it matches the widened marker list **or** the outline's last
   section objective mentions closing/outro/farewell; document the rule in the docstring.
8. Evidence under `data/quality_reviews/phase14/gate-b2/` (gitignored). Never port 8000.
9. `--reaggregate <evidence.json>`: recompute aggregates/decision from an existing
   evidence file without running anything (used to verify the new code against the
   Phase 13 files).

**Verification (Coder — no live trial):** `ruff` clean; `py_compile`; `--reaggregate`
against `data/quality_reviews/phase13/gate-b/gate-b-20260921T000903Z.json` and
`…T010451Z.json` reproduces the known counts (local 1/5 complete; Gemini 0/2, both
`infra` once 14.2's codes exist — for the old files they classify as `other` with
message `ProviderUnavailableError…`; both outcomes must be printed and pasted here).
**The Coder never runs a live trial** (`OLLAMA_NUM_PARALLEL=1`).

## 14.4b — Execution and report (PM)

**Allowed files:** `docs/operations/phase14-gate-b2.md`,
`data/quality_reviews/phase14/gate-b2/*` (gitignored), runtime-created rows/media.

**Preflight (all recorded in the report):**

- User confirms the Coder is idle; `git rev-parse HEAD`; worktree clean; full suite
  green at that HEAD.
- Ollama env set (`OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_MODELS=D:\DataAdmin\OllamaModels`,
  `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_QUEUE=4`,
  `OLLAMA_NO_CLOUD=1`); `curl http://127.0.0.1:11434/api/tags` shows digest
  `6488c96fa5fa…`.
- Three direct Gemini `generateContent` probes, status codes logged.
- Live RPM/RPD for `gemini-3.8-flash` from the AI Studio dashboard. If RPD < ~35, the
  Gemini matrix is split 3 + 2 across two calendar days, declared here before run 1.
- `nvidia-smi` baseline; port 8000 untouched.

**Sequence:** local matrix (full 13.9 protocol) → Gemini matrix. Never concurrent.
Between matrices, verify no job is active on the trial DB.

**Measured per run / per section / aggregate:** exactly plan §4.4.

**Decision rules (declared, immutable):**

- Local: Phase 13 Gate B rule verbatim → PASS promotes local in development.
- Gemini: PASS-cloud = 5/5 complete ∧ ≥ 4/5 content pass ∧ ≤ 1 infra job death.
  Absorbed transient errors (retries that ended `ok`) are the 14.1 success signal, not
  failures. ≥ 2 infra deaths → FAIL-INFRA (reopens 14.1, blocks 14.6). Content failures
  alone → FAIL-CONTENT.
- Any `handler_exception` → defect triage before quoting the matrix.
- Thresholds never weakened after seeing results.

**Report (`docs/operations/phase14-gate-b2.md`):** preflight; per-run tables; per-
section tables; aggregates; both decisions with reasons; comparison against the Phase 13
run (per-section pass rate, repair effectiveness now measurable, backoff absorption);
open questions answered or carried (−9% compensation; 3 vs 4 attempts); evidence file
names and SHA-256.

## Execution record

- 14.4a (Coder):
  - **Investigation before code:** inspected the two named Phase 13 evidence
    files directly. `gate-b-20260921T000903Z.json` (local): 5 B1-8min runs, 4
    `error_code == "section_validation_failed"`, 1 `job_status == "complete"`
    (785 words) -- confirms "local 1/5 complete". `gate-b-20260921T010451Z.json`
    (gemini): 2 runs, both `error_code == "handler_exception"`,
    `error_message` starting `"ProviderUnavailableError: Gemini is temporarily
    overloaded (HTTP 503)"` -- confirms both classify as `other` under the new
    rule (not `infra`, since `handler_exception` doesn't start with
    `provider_`; the plan's own expectation for these specific pre-14.2
    files). Also inspected the still-present trial DB
    (`data/quality_reviews/phase13/gate-b/trial-data/app.db`, gitignored but
    left on disk locally) directly with `sqlite3`: every `ai_generation_checkpoints`
    row from that trial has `metrics_json = '{}'` (predates 14.2/14.3), and the
    one completed run's checkpoints let me reproduce the disclosed `has_outro`
    false negative exactly: last line "Good luck with your journey to better
    health and longer life ahead." matches none of the old marker list, while
    the outline's own last-section objective ("The interviewer concludes the
    show by summarizing key takeaways...") clearly signals a close -- confirms
    the fix design (objective-based fallback, matching "conclu" as a substring,
    not just literal "closing/outro/farewell").
  - **Design decisions:**
    - `classify_failure(error_code, error_message) -> "infra"|"content"|"other"`:
      `infra` iff `error_code` starts with `"provider_"`; `content` iff
      `error_code` in `{"section_validation_failed", "global_validation_failed",
      "schema_validation_failed"}` (Amendment B's code included); `other`
      otherwise (covers `handler_exception`, `None`, and every pre-14.2 file).
      A completed job always gets `failure_class = None` (not applicable).
    - Per-run call stats (`_call_stats`) are derived only from `ok`-outcome
      calls in `job["metrics"]["calls"]` (an `error`-outcome call has no
      `attempts`/`backoff_seconds` recorded on it -- the exception is raised
      before a `GenerationResult` exists to read those from, see 14.2's
      `_call_record`): `total_attempts`, `total_backoff_seconds`,
      `max_attempts_on_one_call`, `absorbed_transient_errors = Σ(attempts-1)`,
      `error_calls` count. Both the raw `metrics` dict and the derived
      `call_stats` summary are stored on each run record -- raw for full
      fidelity/future reaggregation, summary for the report table.
    - Per-section data (`_read_section_checkpoints`) is read directly from the
      trial's own `app.db` via a short-lived `sqlite3` connection (busy
      timeout 5s) -- `AIJobOut` deliberately never exposes checkpoint-level
      data (see `app/models/ai_job.py`'s own docstring), and this is a
      diagnostic runner, not the running app. Returns `[]` on any DB error or
      missing file rather than raising, so `--reaggregate` against an old
      evidence file whose trial DB is gone still works (its per-section table
      is just empty, not a crash).
    - `has_outro` fix: widened the last-line marker list (a handful more
      common closing phrases) **and** added a fallback that reads the
      outline's own last-section `objective` (via the same direct-DB read) and
      treats it as an outro signal when the objective text contains
      "closing"/"outro"/"farewell"/"conclu"/"wrap up"/"sign off" -- "conclu" as
      a substring specifically because the real disclosed case's objective
      said "concludes", not "closing". Documented in the function's own
      docstring per the task card's requirement.
    - `--matrix {local,gemini}` sets `DIE_AI_MODE` the same way `--mode`
      already does (read from `sys.argv` before the `app.*` import, since
      `Settings()` is a module-level singleton) *and* selects which
      decision-rule-set and default sample/media behavior applies. `--mode`,
      if also given, still wins for `DIE_AI_MODE` (raw-diagnostic override,
      per the task card); omitting `--matrix` entirely keeps every existing
      flag's old behavior byte-for-byte (a bare rerun of the script is
      unaffected by this task).
    - Local matrix keeps the exact 13.9 protocol: samples and media run
      unconditionally (`--skip-samples` still available to opt out for a
      diagnostic). Gemini matrix defaults samples/media OFF, turned on via the
      new `--with-samples`/`--with-media` flags, per item 5.
    - `--resume-evidence <path>` seeds `b1_eight_minute_runs`/`sample_runs`/
      `learning_runs` from a prior evidence file and only runs however many
      more B1-eight-minute runs are needed to reach the requested count, so a
      quota-split Gemini matrix (e.g. 3 runs one day, 2 the next) merges into
      one evidence file/one matrix decision. Structurally verified (seeding
      logic, remaining-count math); the live two-day run itself is 14.4b's
      (PM's), not something the Coder can verify without a live trial.
    - `--reaggregate <path>`: loads an existing evidence JSON, recomputes
      `failure_class` fresh for every run (the whole point -- old files never
      had it), recomputes aggregates and the matrix decision from
      `ai_mode`/`b1_runs_requested`/`diagnostic_only` already in the file,
      re-attempts a per-section DB read (works if the trial DB is still on
      disk, degrades to empty otherwise), and prints everything -- no server,
      no network, no live trial.
- 14.4b (PM):
