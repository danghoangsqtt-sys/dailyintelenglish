# Phase 14 Implementation Plan — AI Gateway Resilience and Section Budget Rebalancing

**Status:** Controlling plan, authored by PM/Tester on 2026-09-21; execution authorized
by the user for a two-session (PM + Coder) parallel workflow
**Owner:** Daily Intel English Studio
**Source:** `docs/brainstorm/session-2026-09-21.md` (Gate B post-mortem, decisions D1–D8)
**Predecessor:** `docs/implementation/phase-13-local-first-ai-reliability.md` (still the
controlling contract for everything Phase 14 does not explicitly amend)
**Architecture record:** `docs/architecture/adr-001-local-first-ai.md` (amended by this
phase — see §4.1)
**Target outcome:** Both providers can complete a real eight-minute script job under
ordinary transient conditions; the pipeline enforces the product word budget exactly as
the product defines it; every repair, retry, and fallback is measurable on the job row;
Gate B is re-run for both providers and the rollout mode is chosen from that evidence.

## 1. Why this phase exists

Phase 13 Task 13.9 (Gate B) returned FAIL for the local provider. The independent
PM/Tester review (`docs/brainstorm/session-2026-09-21.md`) found the Coder's conclusion
("not a system defect, only the local model's word-count precision") **falsified on the
decisive point**. Two independent root causes exist, one of them a regression introduced
by Phase 13 itself, and a third gap makes the repair pass unmeasurable:

**A. Compounding-failure architecture defect (local provider).** `script_pipeline.py`
hard-fails the whole job when one section misses its budget by more than ±15%. Measured
from `ai_generation_checkpoints` (re-verified by the PM on 2026-09-21 directly from
`data/quality_reviews/phase13/gate-b/trial-data/app.db`): per-section pass rate 66.7%
(18/27); five consecutive passes needed → 0.667⁵ = 13.2%, matching the observed 11% job
pass rate (1/9). The one completed job produced sections `[137,152,163,164,165]` =
781/800 words (−2.4%): per-section errors cancel at the total. The product requirement is
**±10% on the total** (720–880 words, `SCRIPT_GLOBAL_WORD_TOLERANCE = 0.10`). The internal
±15%-per-section hard stop is therefore *stricter than the product requirement it exists
to serve*. Accepted sections show a systematic undershoot (mean 145.9 vs target 160, −9%,
σ = 19.5).

**B. Task 13.7 regression (Gemini — the primary provider).** Gemini was never run through
Gate B. When run (`--mode gemini --runs 2`): 0/2 jobs, both killed by HTTP 503 after 9 s
and 24 s. A direct probe returned `200 → 503 → 200` — Gemini is healthy; 503 is the
ordinary transient overload every production client absorbs. `grep -rn "sleep"
app/services/ai/` is empty: `AIRouter._attempt_with_one_retry` re-fires immediately and
the job dies. Pre-13.7 code had 4 attempts × 1s→2s→4s backoff × 6 models; 13.7 removed the
cascade (correctly, per ADR-001) **and** the backoff (never intended). `SYSTEM-RULES.md`
"Gemini API Rules" has always required exponential backoff.

**C. Repair and fallback are unmeasured.** `repair_count`, `fallback_used`,
`fallback_count`, `actual_provider`, `model`, and `metrics_json` on `ai_generation_jobs`
are **never written** by any pipeline (PM verified: every trial row has `repair_count=0,
fallback_used=0, actual_provider=NULL, model=NULL`). The router sets `fallback_used` on
its in-memory result only. Phase 13 invariant 5 ("fallback is recorded in job state")
is therefore not actually met at the row level, and repair effectiveness cannot be
distinguished from "repair never ran".

Task 13.10 (rollout) is **blocked** (D1) until 14.1 and 14.2 land and Gate B is re-run
fairly for both providers (14.4).

## 2. Non-negotiable invariants

All twelve Phase 13 invariants remain in force. Phase 14 adds:

13. **No threshold relaxation, ever.** `SCRIPT_GLOBAL_WORD_TOLERANCE` stays `0.10`
    (720–880 words for a B1 eight-minute script) and `SCRIPT_SECTION_WORD_TOLERANCE`
    stays `0.15`. Neither value changes in this phase. A test pins both values so a
    silent edit fails CI. Task 14.3 changes what the section tolerance *does* (it
    becomes the repair trigger and drift signal instead of a job-killing gate); it does
    not change the number. See §4.3 governance note.
14. **Single model, single fallback — the ADR-001 cascade ban stands.** Backoff restores
    *attempts against the same model*; it never re-introduces `GEMINI_MODEL_FALLBACKS`
    or any second cloud model into automatic routing. Preview models stay barred.
15. **One deadline, honoured by backoff.** Every sleep and every attempt lives inside the
    caller's `deadline_seconds` (`AI_REQUEST_DEADLINE_SECONDS`, 120 s). The router never
    sleeps past the remaining budget, and never starts an attempt it cannot finish
    inside it.
16. **Backoff is real or it does not exist.** A test must prove the router actually
    waits the declared sequence (patch the module-local `sleep` and assert the recorded
    delays), not merely that a constant exists.
17. **Telemetry is written to the job row inside the same short transactions the
    pipeline already uses.** Never a new lock, never held across inference, never any
    prompt/response text or secret in `metrics_json`.
18. **Infrastructure failures and content failures are distinguishable on the job
    row** (`error_code`) and in the Gate B evidence. A 503 that exhausts backoff is
    `provider_unavailable`, never `handler_exception`, never confused with a word-count
    miss.
19. **Session partition is a hard rule** (§10). PM never edits `app/**`, `tests/**`,
    `scripts/**`, `prompts/**`; Coder never edits `docs/**`, `.viepilot/TRACKER.md`,
    `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`; Coder never runs
    `scripts/run_ai_operational_trial.py`.

## 3. Scope

### In scope

- Bounded exponential backoff for transient provider errors in `AIRouter`.
- Per-call attempt/backoff telemetry on `GenerationResult`; per-job telemetry on
  `ai_generation_jobs` (`repair_count`, `fallback_*`, `actual_provider`, `model`,
  `metrics_json`); specific `provider_*` error codes on provider-caused job failures.
- Running section word budget in `script_pipeline.py`; hard gate only at the global
  total; one bounded final-section budget repair.
- Runner preparation and a second Gate B run for **both** providers with a declared
  measurement protocol.
- Correction of the Phase 13 acceptance report; ADR-001 amendment.
- Resumption of Task 13.10 driven by the new evidence.

### Out of scope

- Any change to `SCRIPT_GLOBAL_WORD_TOLERANCE`, `SCRIPT_SECTION_WORD_TOLERANCE`, Gate B
  thresholds, or the CEFR/duration targets.
- Compensating the measured −9% undershoot by inflating requested targets (open
  question; decided only with 14.4 data, in a later task if at all).
- Multi-model cascade, preview models, Gemini remote-background execution, changes to
  the learning pipeline's validation shape (its n=1 pass is noted, not acted on).
- Frontend changes (Step 2 already renders `job.fallback_used`; populating the row is
  enough).
- Fine-tuning, prompt rewrites beyond passing the effective target to the section/repair
  templates.

## 4. Design decisions

### 4.1 Transient-error backoff (D3) and the ADR-001 amendment

ADR-001 Decision 3 currently reads "at most one semantic repair **or infrastructure
retry** and one visible stable Gemini fallback". The brainstorm's fairness note (cascade
ban ≠ backoff ban) is correct about *intent*, but the ADR text does cap infrastructure
retries at one. Restoring 1s→2s→4s therefore requires an explicit amendment, recorded in
`docs/architecture/adr-001-local-first-ai.md` §"Amendments" by the PM in the same commit
as this plan (docs are PM-owned). The amendment: transient infrastructure errors may be
retried against the *same* model up to `AI_TRANSIENT_MAX_ATTEMPTS` total attempts with
exponential backoff inside the single request deadline; the one-semantic-repair rule,
the single-fallback rule, and the cascade ban are unchanged.

Policy (implemented in `AIRouter` only — providers stay single-attempt):

| Error class | Members | Policy |
|---|---|---|
| Transient infrastructure | `ProviderUnavailableError`, `ProviderRateLimitError`, `ProviderTimeoutError` | up to `AI_TRANSIENT_MAX_ATTEMPTS = 4` attempts per provider; sleep `AI_TRANSIENT_BACKOFF_BASE_SECONDS × 2^(n−1)` = 1 s, 2 s, 4 s before attempts 2, 3, 4; each sleep capped at `AI_TRANSIENT_BACKOFF_MAX_SECONDS = 4.0` |
| Content | `ProviderInvalidResponseError`, `SchemaValidationError` | unchanged: exactly one immediate retry (no sleep) — these are not infrastructure conditions and the semantic-repair budget already covers them |
| Non-retryable | `ProviderAuthError` and any other `ProviderError` | no retry (unchanged) |

Deadline rule: the router records `deadline_at = monotonic() + request.deadline_seconds`
on entry. Before sleeping it computes `remaining`; if `remaining < delay +
AI_BACKOFF_MIN_REMAINING_SECONDS (5.0)` it stops retrying and raises the last error.
`asyncio.wait_for` on the whole route stays as the outer guard. Hybrid mode keeps the
exact same shape as today (local → up to 4 attempts → circuit-breaker failure → one
Gemini route → up to 4 attempts), all inside the one deadline. Circuit-breaker
accounting is unchanged (one `record_failure` per exhausted local route).

Optional (allowed, not required for acceptance): honour a provider-supplied retry-after
hint (`ProviderRateLimitError.retry_after_seconds`) as `max(hint, delay)`, still capped
by the remaining deadline.

`GenerationResult` gains `attempts: int` (total calls made on the winning provider),
`backoff_seconds: float` (total slept before the winning call), and
`transient_errors: list[str]` (exception class names, never messages). Router logs one
`ai_router_backoff provider= purpose= attempt= delay_seconds= error=` line per sleep and
one `ai_router_exhausted provider= purpose= attempts= backoff_seconds=` line when a
provider route gives up. No prompt/response text, no key.

### 4.2 Job telemetry (D5)

`ai_job_service` gains `record_generation_call(db, job_id, call: dict, commit=True)`
which, in one UPDATE: appends `call` to `metrics_json["calls"]` (bounded to
`AI_JOB_MAX_RECORDED_CALLS = 64` entries, oldest dropped), sets `actual_provider`/`model`
from the call, sets `fallback_used = 1` and increments `fallback_count` when the call
reports `fallback_used`, and increments `repair_count` when `call["is_repair"]` is true.
It is legal in `running`/`validating` only (a terminal job is immutable; the function
raises `ValidationError` otherwise). It is called inside the pipeline's existing short
`write_transaction` blocks, never during inference.

Call record shape (all fields safe): `{"purpose", "section_index" (nullable),
"provider", "model", "attempt", "attempts", "backoff_seconds", "latency_ms",
"fallback_used", "circuit_open", "is_repair", "outcome": "ok"|"error",
"error_type" (nullable), "at": ISO-8601 UTC}`.

Repair outcomes are recorded on the section checkpoint's `metrics_json`:
`{"target_nominal", "target_effective", "words", "deviation_pct", "repaired": bool,
"words_before_repair" (nullable), "errors_before_repair": int}`.

Provider-caused job failures get specific codes: pipelines catch `ProviderError` around
each router call and fail the job with `error_code` = `provider_unavailable` |
`provider_timeout` | `provider_rate_limited` | `provider_auth` |
`provider_invalid_response` (mapping by exception class, `provider_error` for the base
class) and a safe message (`type(exc).__name__` plus the provider's own safe text,
truncated to 200 chars as today). `handler_exception` remains reserved for genuine
handler bugs. Both pipelines (script, learning) apply this.

**Amendment B (PM, 2026-09-21, after reviewing commit `cde8e79`):**
`SchemaValidationError` is a `ProviderError` subclass but is a *content* failure (raised
by `parse_and_validate` after a successful provider call, or by `_render` on a missing
template). The script pipeline's outline path catches it through `except ProviderError`
and, with the 14.2 table as landed, records `provider_error` — which §4.4 would count as
an infrastructure failure. Required follow-up **14.2-b** (Coder, within 14.2's allowed
files, before 14.4a): `provider_error_code(SchemaValidationError)` returns
`schema_validation_failed`; §4.4's failure classification treats
`schema_validation_failed` as `content`; one service test and one script-pipeline test
(outline returns unparseable JSON → `error_code == "schema_validation_failed"`,
never `provider_*`). `fallback_reason` staying unpopulated in 14.2 is accepted: the
router does not expose the local failure class on `GenerationResult` (14.1 is closed),
and neither Gate B-2 matrix exercises fallback (local matrix has it OFF; Gemini mode
has none). Candidate for a later task, not a Phase 14 gate.

`AIJobOut` gains `metrics: dict` (parsed `metrics_json`, `{}` on parse failure) so the
trial runner and future diagnostics read telemetry over the same safe API. `docs/api.md`
is updated by the PM (docs domain) after the Coder lands the field.

### 4.3 Running section budget (D4) — governance note first

**This is not a threshold relaxation.** The product standard — 720–880 words, ±10% of
the total — is untouched and remains the only hard word-count gate. What is removed is
an *internal* intermediate hard stop (fail the job when one section is outside ±15%)
that was never a product requirement and which, because it must hold five consecutive
times, enforced an effective standard *stricter* than the product's own. Measured
evidence: the only completed job passed the product gate at −2.4% while individual
sections ranged from −14% to +3%. The ±15% number itself is kept exactly, but it now
means "trigger one repair and carry the drift", not "kill the job". A pull request that
edits either tolerance constant is a Phase 14 stop condition, not an implementation
choice.

Mechanics:

1. **Nominal targets** come from the outline exactly as today (`plan_sections` and the
   outline call are unchanged).
2. **Effective target** for section *i*: `effective_i = clamp(nominal_i + carry,
   nominal_i × (1 − SCRIPT_SECTION_CARRY_CAP), nominal_i × (1 + SCRIPT_SECTION_CARRY_CAP))`
   with `SCRIPT_SECTION_CARRY_CAP = 0.35`; the residual not absorbed by the clamp stays
   in `carry`. `carry` starts at 0 and after each accepted section becomes
   `carry + (effective_i − actual_words_i)` (positive = deficit to make up).
3. **Last section**: `effective_last = clamp(target_words − words_so_far,
   nominal_last × 0.5, nominal_last × 1.5)` (`SCRIPT_LAST_SECTION_CARRY_CAP = 0.5`) so
   the closing section can actually land the total.
4. **Section validation is split** into structural hard checks (no lines, unknown
   speaker IDs, > `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`) and a word-deviation
   check against the *effective* target using `SCRIPT_SECTION_WORD_TOLERANCE`. Either
   class still triggers the one repair pass (unchanged repair budget per section).
   After repair: any structural error → `section_validation_failed` (unchanged); a
   remaining word deviation → **accept**, log `script_section_accepted_off_target`, and
   carry the drift. Schema-invalid output after repair still fails as today.
5. **Global gate** (`validate_global`, ±10%) is unchanged and remains hard.
6. **One final-section budget repair**: if, after the last section, the merged total is
   outside ±10%, the pipeline regenerates the last section **once** through the repair
   prompt with `target_words = target_words − words_before_last_section`, counts it as a
   repair (`repair_count += 1`), overwrites that section's checkpoint (`save_checkpoint`
   already upserts on `(job_id, stage, section_index)`), and re-runs `validate_global`.
   Still outside → `global_validation_failed`. Total repair calls per job are therefore
   bounded by `num_sections + 1`.
7. **Resume is deterministic**: on restart, `carry` is recomputed from the checkpointed
   sections' actual word counts against the outline's nominal targets — no new column,
   no new checkpoint stage.
8. The section and repair prompts receive the effective target in the existing
   `target_words` variable; wording may say the budget is adjusted, nothing else changes.
9. The −9% systematic undershoot is **not** compensated in this task (open question;
   decide with 14.4 data). The Coder records its reasoning in the task card.

### 4.4 Gate B second run (D6) — measurement protocol

Both providers, same runner, same content thresholds as Phase 13 §8 Task 13.9 (not
weakened), run **sequentially, never concurrently** (Ollama is `OLLAMA_NUM_PARALLEL=1`).
The PM runs it; the Coder prepares the runner (14.4a) and never executes it.

**Preflight (recorded in evidence):** `git rev-parse HEAD` after 14.1–14.3 are merged;
full suite green; Ollama env + `/api/tags` digest `6488c96fa5fa…`; three direct Gemini
`generateContent` probes with status codes; the account's live Gemini RPM/RPD limits for
`gemini-3.8-flash` read from the AI Studio dashboard (the constants file records
5 RPM / 20 RPD as of 2026-09-14 — if 20 RPD is still enforced, five B1 runs ≈ 35 calls
cannot fit one day and the Gemini matrix is split across two calendar days, declared
before the first run; a split matrix is still five runs, not `DIAGNOSTIC_ONLY`).

**Local matrix (unchanged from 13.9):** 5 × B1 eight-minute, then B1 5/10-minute and
A2/C1 samples, learning on each completed script, real Edge TTS → MP3 → MP4 pipeline on
the winning configuration. `AI_MODE=local`, fallback OFF.

**Gemini matrix ("Gate B-cloud"):** 5 × B1 eight-minute, learning on each completed
script, samples optional (quota permitting), no media pipeline requirement (media is
provider-independent and already required once under the local matrix; if local
produces no winner, run media once against the best Gemini script instead).
`AI_MODE=gemini`.

**Measured per run:** job status; `error_code`; failure class (`infra` if `error_code`
starts with `provider_`, `content` if `section_validation_failed`/
`global_validation_failed`/`schema_validation_failed` (Amendment B), `other` otherwise); total seconds; first-progress seconds;
longest stage gap; `repair_count`; `fallback_count`; every `metrics.calls[]` entry
(attempts, backoff seconds, latency); the content checks from 13.9. **Per section** (from
`ai_generation_checkpoints.metrics_json`): nominal target, effective target, actual
words, deviation, repaired flag, words before/after repair. **Aggregate per provider:**
job completion rate, content pass rate, infra failure count, per-section within-±15%
rate, repair success rate (fraction of repairs that brought the section inside ±15%),
mean/σ of section deviation, distribution of totals against 720–880, total backoff
seconds, max attempts observed.

**Decision rules (declared now, not after results):**

- Local: the Phase 13 Gate B rule verbatim — PASS promotes local in development.
- Gemini (**Amendment C, PM, 2026-09-21 — clarified before any Gate B-2 run, no
  results seen**; the first wording "5/5 complete ∧ … ∧ ≤ 1 infra death" made the
  allowance unreachable, and a single infra death would have been mislabelled
  FAIL-CONTENT). Let `infra` = jobs dead with a `provider_*` code, `content_pass` =
  completed jobs passing every content check, `n` = 5:
  - **PASS-cloud** ⇔ `infra ≤ 1` ∧ `content_pass ≥ 4` ∧ `completed + infra == n`
    (every job either completed or died to one tolerated transient death; no
    content-class or `other` death);
  - **FAIL-INFRA** ⇔ `infra ≥ 2` — reopens 14.1 (insufficient attempts/backoff or quota)
    and blocks 14.6 again;
  - **FAIL-CONTENT** ⇔ otherwise.
  An infra error the backoff absorbed is not a failure — it is the success case for
  14.1 and is reported as "absorbed transient errors: N". Any `handler_exception` is a
  defect flag on top of the verdict.
- Any `handler_exception` on either provider is a defect to be triaged before the
  matrix result is quoted.
- Thresholds are not weakened after seeing results. A partial matrix is
  `DIAGNOSTIC_ONLY`.

Evidence: `data/quality_reviews/phase14/gate-b2/` (gitignored), summarized in
`docs/operations/phase14-gate-b2.md` (PM-owned, committed).

## 5. Configuration and constants

New named constants in `app/core/constants.py` (CR-02):

```python
AI_TRANSIENT_MAX_ATTEMPTS = 4
AI_TRANSIENT_BACKOFF_BASE_SECONDS = 1.0
AI_TRANSIENT_BACKOFF_MAX_SECONDS = 4.0
AI_BACKOFF_MIN_REMAINING_SECONDS = 5.0
AI_JOB_MAX_RECORDED_CALLS = 64
SCRIPT_SECTION_CARRY_CAP = 0.35
SCRIPT_LAST_SECTION_CARRY_CAP = 0.5
SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 1
```

`GEMINI_MAX_RETRIES` / `GEMINI_RETRY_BASE_DELAY` (legacy, now unused) are left in place;
the router uses the `AI_*` names so the legacy constants can be removed in a later
cleanup with `GEMINI_MODEL_FALLBACKS`. `AI_REQUEST_DEADLINE_SECONDS` stays 120. No new
environment variable is introduced.

## 6. Work packages and strict task contracts

Every task starts only after its task card status is `in_progress`. Each task card lists
its exact allowed files. A newly discovered required file pauses that task until the plan
and the task card are updated **by the PM** (Coder reports; PM amends; Coder resumes).
Existing unrelated changes are never staged. Commits contain explicit paths only.

### 14.1 — Restore bounded exponential backoff for transient errors (P0, Coder)

**Allowed files:** `app/services/ai/router.py`, `app/services/ai/contracts.py`,
`app/core/constants.py`, `app/core/exceptions.py` (only for the optional
`retry_after_seconds` attribute), `tests/test_ai_router.py`,
`tests/test_ai_contracts.py`, `tests/test_ai_logging.py`,
`tests/test_ai_providers.py` (only if the retry-after hint is implemented).

**Amendment A (PM, 2026-09-21, after Coder commit `2384578` reported the block):**
`tests/test_learning_service.py`, `tests/test_script_service.py`,
`tests/test_youtube_service.py` are added — **test-only, exactly the four
`*_wraps_provider_error*` tests** that script two `ProviderUnavailableError` outcomes to
model the pre-14.1 "exhaust after one retry" policy. Under four attempts the router makes
a third call, `FakeProvider` runs out of scripted outcomes, and the test sees
`RuntimeError` instead of the wrapped provider error (PM reproduced: 4 failed, and the
run took ~12.8 s because the backoff genuinely slept 1 s + 2 s per test). Required fix
shape: script four transient outcomes so the router exhausts for real, and patch
`app.services.ai.router.sleep` to a no-op recorder so no test sleeps. No assertion about
the wrapping behaviour changes. No production file is added.

**Actions:** implement §4.1 exactly. Import `sleep` as a module-local name
(`from asyncio import sleep`) so tests patch `app.services.ai.router.sleep`, never the
global `asyncio.sleep` (see `tests/test_script_service.py` history for why). Keep
providers single-attempt. Keep the hybrid route shape and circuit-breaker accounting.

**Verification:**
- delay sequence test: three transient errors then success → recorded sleeps
  `[1.0, 2.0, 4.0]`, result `attempts == 4`, `backoff_seconds == 7.0`;
- exhaustion test: four transient errors → raises the fourth error, three sleeps, one
  `ai_router_exhausted` log line;
- deadline test: with a short `deadline_seconds`, the router stops before a sleep that
  would exceed the budget and raises without sleeping past it;
- content-class test: `SchemaValidationError` still gets exactly one immediate retry
  and zero sleeps; `ProviderAuthError` gets no retry and no sleep;
- hybrid test: local exhausts 4 attempts (3 sleeps), one Gemini fallback,
  `fallback_used`, circuit counts one failure;
- existing "no nested retries" tests remain green with attempt counts updated;
- log-capture test proves no prompt/key in the new log lines;
- revert-and-confirm-failure: with the sleep call removed, the delay-sequence test fails.
- `ruff` clean; full suite green.

**Rollback:** set `AI_TRANSIENT_MAX_ATTEMPTS = 2` and base delay `0.0` restores the
13.7 behaviour without a code revert.

### 14.2 — Job telemetry: repair, fallback, provider, attempts, error codes (P0, Coder)

**Allowed files:** `app/services/ai_job_service.py`, `app/services/script_pipeline.py`,
`app/services/learning_pipeline.py`, `app/models/ai_job.py`, `app/api/ai_jobs.py`
(only if the projection needs it), `app/core/constants.py`,
`tests/test_ai_job_service.py`, `tests/test_script_pipeline.py`,
`tests/test_learning_pipeline.py`, `tests/test_ai_jobs_api.py`.

**Actions:** implement §4.2. Record every router call (outline, section, repair,
learning, learning repair) via `record_generation_call` inside the pipeline's existing
short write transactions. Map `ProviderError` subclasses to `provider_*` error codes in
both pipelines. Expose `metrics` on `AIJobOut`.

**Verification:**
- service test: `record_generation_call` appends, bounds at 64, increments
  `repair_count` only for `is_repair`, increments `fallback_count`/sets `fallback_used`
  only when reported, refuses terminal jobs;
- pipeline tests (FakeProvider): one-repair-then-succeed job ends with
  `repair_count == 1` and a section checkpoint whose `metrics_json.repaired` is true;
  happy path `repair_count == 0`; hybrid fallback job has `fallback_used == 1`,
  `fallback_count >= 1`, `actual_provider == "gemini"`;
- error-code tests: a provider that always raises `ProviderUnavailableError` yields
  `error_code == "provider_unavailable"`, never `handler_exception`; same for timeout,
  rate-limit, auth;
- API test: `GET …/ai-jobs/{id}` returns `metrics.calls[]` with no prompt text and no
  key; the existing secret-absence tests still pass;
- revert-and-confirm-failure on the `repair_count` increment;
- `ruff` clean; full suite green.

**Rollback:** telemetry is additive; the columns already exist. No migration.

### 14.3 — Running section budget; hard gate only at the global total (P1, Coder)

**Dependency:** 14.2 (repair telemetry must exist before the repair trigger is changed,
so the effect is measurable).

**Allowed files:** `app/services/script_pipeline.py`, `app/core/constants.py`,
`prompts/script/section.txt`, `prompts/script/repair.txt`, `tests/test_script_pipeline.py`,
`tests/fixtures/ai/*`.

**Actions:** implement §4.3 exactly. Add the constants-pin test asserting
`SCRIPT_GLOBAL_WORD_TOLERANCE == 0.10` and `SCRIPT_SECTION_WORD_TOLERANCE == 0.15`.

**Verification (each as a FakeProvider end-to-end handler test unless noted):**
- pure-function tests for effective-target/clamp/carry math including the last-section
  rule and residual carry;
- five sections each outside ±15% of nominal but total inside ±10% → `complete`,
  `repair_count` reflects the per-section repairs, every checkpoint `metrics_json`
  carries nominal/effective/actual;
- total outside ±10% after all sections → one final-section repair → inside → `complete`
  with `repair_count` incremented by one more;
- total still outside after the final repair → `global_validation_failed`, prior script
  untouched, exactly `num_sections + 1` repair calls maximum;
- structural error surviving repair → `section_validation_failed` (unchanged);
- interrupted-then-resumed job recomputes `carry` from checkpoints and reaches the same
  total as an uninterrupted run;
- constants-pin test fails if either tolerance is edited (revert-and-confirm-failure by
  temporarily editing the constant);
- `ruff` clean; full suite green.

**Rollback:** `SCRIPT_SECTION_CARRY_CAP = 0.0` and
`SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 0` reduce the pipeline to fixed targets;
the per-section accept-and-carry behaviour is the only non-configurable change and is
reverted by git if required.

### 14.4 — Re-run Gate B for both providers (P1)

**14.4a Runner preparation (Coder). Allowed files:**
`scripts/run_ai_operational_trial.py` only.

**Actions:** classify each run's failure as `infra`/`content`/`other` from `error_code`
(`schema_validation_failed` is `content` — Amendment B);
read `metrics.calls[]` from the job API and report attempts/backoff/absorbed transient
errors per run; dump per-section nominal/effective/actual/deviation/repaired from the
trial DB's `ai_generation_checkpoints.metrics_json`; compute the aggregates in §4.4;
write evidence under `data/quality_reviews/phase14/gate-b2/`; add `--matrix
local|gemini` semantics per §4.4 (Gemini matrix: no media requirement; learning per
completed script); fix the `has_outro` heuristic false negative disclosed in the Phase
13 report (accept a natural closing line — e.g. treat a final line that the outline's
last-section objective marks as the outro, or widen the marker list; document the
rule); keep `DIAGNOSTIC_ONLY` semantics for partial matrices; never touch port 8000.

**Verification (Coder):** `--smoke-test` against FakeProvider is not possible for a
no-mock runner, so verify by `ruff`, `python -m py_compile`, and a dry parse of an
existing Phase 13 evidence JSON through the new aggregation code (add a `--reaggregate
<evidence.json>` flag for exactly this). The Coder **does not** run a live trial.

**14.4b Execution and report (PM). Allowed files:**
`docs/operations/phase14-gate-b2.md`, `data/quality_reviews/phase14/gate-b2/*`
(gitignored evidence), runtime-created project/media/database rows.

**Actions:** confirm with the user that the Coder is idle; run preflight; run the local
matrix; run the Gemini matrix; apply the declared decision rules; write the report
with every number traceable to an evidence file; do not weaken any threshold.

**Pass:** per §4.4 decision rules, reported separately for local and Gemini.

### 14.5 — Correct the Phase 13 acceptance report (P2, PM)

**Allowed files:** `docs/operations/phase13-acceptance.md`.

**Actions:** add a dated "Correction" section immediately after "Decision", stating that
the "not a system/infrastructure defect" conclusion was falsified by (a) the compounding
per-section gate and (b) the missing backoff/503 regression, with pointers to the
brainstorm and this plan; annotate the "Root cause" and "Recommendation" sections with
"superseded — see Correction" notes. **Do not delete or rewrite the original text**; the
record must show what was concluded and why it changed.

**Verification:** original paragraphs remain byte-identical apart from the added
annotations; `git diff` shows additions only within the annotated regions.

### 14.6 — Resume Task 13.10 with an evidence-backed rollout mode (P2)

**Dependency:** 14.4b decision for both providers; 14.5 done.

**Allowed files:** exactly Task 13.10's list, split by domain: Coder — `README.md`,
`CHANGELOG.md`, `.env.example`, `scripts/check_dependencies.py`,
`daily_intel_english_studio.spec`, `scripts/build_exe.ps1`, `.viepilot/ARCHITECTURE.md`,
`.viepilot/AI-GUIDE.md`, `.viepilot/PROJECT-CONTEXT.md`; PM — `docs/api.md`,
`docs/prompt-guide.md`, `docs/operations/local-ai.md`,
`docs/operations/phase13-acceptance.md`, `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`,
`.viepilot/HANDOFF.json`.

**Rollout mode by evidence (declared now):**

| Local | Gemini | Development default | Packaged default |
|---|---|---|---|
| PASS | PASS-cloud | `hybrid` (local first, one visible Gemini fallback) | `gemini` until onboarding is verified (ADR-001 §6, unchanged) |
| FAIL | PASS-cloud | `gemini`; local labelled experimental | `gemini` |
| PASS | FAIL-INFRA | **stop condition** — local-only development is allowed, packaged rollout blocked until 14.1 is revisited | — |
| FAIL | FAIL-INFRA / FAIL-CONTENT | **stop condition** — Task 13.10 stays blocked | — |

Rollback drill, packaging proof, and documentation requirements are exactly Task 13.10's.

## 7. Cross-task verification and release gates

No task is accepted until: its allowed-file diff is reviewed by the PM against the real
diff (not the report); targeted tests fail meaningfully under revert/fault injection
where declared; `venv\Scripts\python.exe -m ruff check app tests scripts` and
`venv\Scripts\python.exe -m pytest -q` pass (baseline 808/808 before this phase); no raw
key/prompt is present in captured logs, fixtures, or `metrics_json`; the task card
records commands, results, deviations; the commit contains only explicit paths; worktree
clean with `origin/main` upstream and zero unpushed commits.

Phase 14 is complete only when: backoff is proven to wait; every job row records
provider/model/repairs/fallbacks/attempts; the section pipeline accepts drift and gates
only at ±10% total; both tolerance constants are unchanged and pinned; Gate B has been
re-run for both providers under the declared protocol; the Phase 13 report carries its
correction; ADR-001 carries its amendment; Task 13.10 has an evidence-selected mode or an
explicit stop-condition record.

## 8. Stop conditions

Execution pauses and reports evidence instead of improvising when:

- a change would edit `SCRIPT_GLOBAL_WORD_TOLERANCE`, `SCRIPT_SECTION_WORD_TOLERANCE`,
  or any Gate B threshold;
- a change would add a second cloud model, a preview model, or provider-internal retries;
- backoff cannot fit the 120 s deadline without changing `AI_REQUEST_DEADLINE_SECONDS`
  (raise to the user; do not silently change it);
- a required file falls outside a task's allowed list;
- the Gemini account's live quota cannot accommodate the declared matrix even split
  across two days;
- Gate B-cloud returns FAIL-INFRA after 14.1;
- any `handler_exception` appears in a Gate B run;
- a secret or prompt text appears in `metrics_json`, logs, or evidence;
- either session detects edits in the other session's file domain.

## 9. Rollback strategy

Configuration-first, non-destructive, unchanged from Phase 13 §11. Phase 14 adds no
migration. Backoff and the running budget each have constant-level neutralisation
(§6, 14.1/14.3 rollback notes). Telemetry writes are additive and ignorable.

## 10. Two-session execution protocol

- **PM (this plan's author) owns:** `docs/**`, `.viepilot/TRACKER.md`,
  `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`, and — until the handover commit that
  contains this plan — `.viepilot/phases/14-ai-gateway-resilience/**`. After handover
  the Coder owns that folder; the PM reads it and requests edits.
- **Coder owns:** `app/**`, `tests/**`, `scripts/**`, `prompts/**`, `README.md`,
  `CHANGELOG.md`, `.env.example`, packaging files, and the Phase 14 state folder after
  handover.
- **Only the PM runs** `scripts/run_ai_operational_trial.py` and the full suite during a
  trial window (`OLLAMA_NUM_PARALLEL=1`; concurrent inference corrupts timing evidence).
  Before any trial or full-suite run the PM confirms with the user that the Coder is
  idle.
- Both: `git pull --rebase origin main` before every commit; explicit `git add <path>`;
  small commits pushed immediately; the dev server on port 8000 is never stopped.
- Task status flow: Coder sets `in_progress`/`done` in the task card and PHASE-STATE;
  the PM independently reviews the diff and records acceptance in TRACKER.md. A task is
  done only when both records agree.

This plan is the controlling implementation contract for Phase 14. The brainstorm
remains the design record; task cards and PHASE-STATE record execution evidence and any
approved amendments.

## 12. Amendment D (2026-09-21, after Gate B-2) — local-only release path

Authority: owner decisions D9–D12 (`docs/brainstorm/session-2026-09-21.md` §Addendum);
ADR-001 amendment A2. Gate B-2 evidence: `docs/operations/phase14-gate-b2.md`.

**What changes in this plan:** Task 14.1-b (Gemini backoff redesign) is dropped (D12).
Task 14.6's rollout table row "FAIL / FAIL-INFRA → stop" is superseded by D11: the release
path is **local-only**, with local hardening and a third local Gate B run before 13.10
resumes. Invariants 13–19 stay. Phase 13 invariant 9 ("No model bundled in the EXE … the
application must still start when either is absent") stays — *start* is required,
*generate* is not (D10). Phase 13 invariant 10 ("Rollback stays live: `DIE_AI_MODE`
preserves a Gemini-only recovery path") is amended to: the Gemini path is dormant and
re-enabled only by explicit configuration plus a key; it is no longer a supported
recovery path for releases.

### 14.7 — Local-only mode, config-first (Coder)

**Allowed files:** `app/core/config.py`, `app/core/constants.py`, `.env.example`,
`app/api/ai_jobs.py` (health payload only), `app/services/settings_service.py`,
`app/api/settings.py`, `app/models/settings.py`, `frontend/pages/settings.html`,
`frontend/static/js/settings.js`, `frontend/static/js/api.js` (only if a call is removed),
`frontend/static/js/step2_script.js`, `frontend/static/js/step3_learning.js` (only to
replace the "using Gemini fallback" copy with the Ollama-missing guidance),
`frontend/static/css/style.css`, `scripts/check_dependencies.py`,
`daily_intel_english_studio.spec` (only if imports/data change), `README.md`,
`CHANGELOG.md`, `tests/test_settings_service.py`, `tests/test_settings_api.py`,
`tests/test_ai_health_api.py`, `tests/test_ui_async_browser.py`,
`tests/test_script_jobs_browser.py`, `tests/test_learning_jobs_browser.py`,
`tests/test_ai_router.py` (default-mode assertions only), `tests/conftest.py` (only if the
default mode change requires a fixture change), and — **Amendment E (PM, 2026-09-21, before
any 14.7 code)** — `tests/test_thumbnail_service.py`, `tests/test_youtube_service.py`
(test-only, for action 7's two FakeProvider tests; omitted from the first list by
mistake). PM documents `docs/operations/local-ai.md` and `docs/api.md`.

**Amendment E also fixes the two choices left open in the card:** (a) the Settings mode
selector is **replaced by a read-only status line** (no dead options; the API still
accepts `local`, and `gemini`/`hybrid` only behind `DIE_AI_ALLOW_CLOUD`); (b) the health
payload **drops** `gemini_fallback_configured` and adds `cloud_enabled: false` — an
always-false field would be misleading; update every frontend reader of the old field in
the same change.

**Amendment F (PM, 2026-09-21, after reviewing commit `518dd0a`):** two more files are
added to 14.7's allowed list, both narrowly: `tests/test_ai_jobs_api.py` (test-only — the
pre-existing `test_ai_health_never_exposes_the_gemini_key` asserts the removed
`gemini_fallback_configured` field; swap the assertion to `cloud_enabled is False`, keep
the secret-absence assertion untouched) and `frontend/pages/step6_thumbnail.html`
(copy-only — the "Pillow + Gemini text" badge is stale under D9; replace with a
provider-neutral label such as "Pillow + local AI text"). Also recorded: action 7 was
delivered for thumbnail only; the YouTube FakeProvider test under `AI_MODE=local` in
`tests/test_youtube_service.py` (already allowed by Amendment E) is still required before
14.7 is accepted.

**Actions:**
1. `AI_MODE` default `"local"` in `config.py` and `.env.example`; remove the stale, unused
   `DIE_AI_CLOUD_FALLBACK` line from `.env.example` (grep confirms nothing reads it).
2. Settings page: remove the Gemini API-key section and the `gemini`/`hybrid` options from
   the mode selector (the selector may remain showing `local` only, or become a read-only
   status line). The settings API keeps accepting the key for dormancy/rollback but the UI
   no longer exposes it; `set_ai_mode` rejects `gemini`/`hybrid` unless
   `DIE_AI_ALLOW_CLOUD=true` (new env, default false — the only new switch; it exists so
   re-enabling is explicit, never accidental).
3. Health: `GET /api/ai/health` reports `cloud_enabled: false` and drops
   `gemini_fallback_configured` (or reports it always false — pick one, document it in the
   card, keep the frontend consistent).
4. Step 2/3: when health says Ollama is unreachable or the model is missing, the generate
   button is disabled and the panel shows install/pull guidance with the exact model tag
   and digest (copy from `docs/operations/local-ai.md`). No "Gemini fallback" copy remains.
5. `check_dependencies.py`: Ollama reachability and model presence become a hard
   requirement with a clear message; the Gemini key check becomes informational or is
   removed.
6. README / CHANGELOG: local-only statement, Ollama prerequisite, rollback note ("Gemini
   is dormant; re-enable via `DIE_AI_ALLOW_CLOUD=true`, `DIE_AI_MODE`, and a key —
   unsupported").
7. Thumbnail and YouTube generators already route through the gateway; in local mode they
   hit Ollama. Add one FakeProvider test each proving they run under `AI_MODE=local`; real
   structured-output behaviour on Ollama for those two schemas is measured by the PM in
   14.9 (one real thumbnail and one real YouTube package on the winning project).

**Verification:** settings/health/UI tests updated; browser tests show the Ollama-missing
state (mocked health) and no Gemini copy anywhere in the DOM; a case-insensitive grep for
"gemini fallback" across `frontend/` returns nothing; packaged smoke build starts with
Ollama stopped and shows guidance; full suite green; `ruff` clean; JS syntax check clean.

**Rollback:** `DIE_AI_ALLOW_CLOUD=true` + `DIE_AI_MODE=hybrid` + key restores the Phase 13
behaviour without a code revert.

### 14.8 — Local hardening: over-length sections and the consecutive-lines rule (Coder)

**Allowed files:** `prompts/script/section.txt`, `prompts/script/repair.txt`,
`app/services/script_pipeline.py`, `app/core/constants.py`, `tests/test_script_pipeline.py`,
`tests/fixtures/ai/*`.

**Evidence to design against (Gate B-2 local):** sections of 417, 426 (after a 340-word
first draft) and 404 words against effective targets of 214, 173 and 208; a 43-word
closing section; run 3 dead on "more than 5 consecutive lines from one speaker" after
repair; repair success 44% (8/18).

**Actions:**
1. Section prompt: state the budget as a hard range ("between A and B words; count them")
   and the consecutive-lines rule with its number; require alternating speakers by default.
2. Repair prompt: pass the measured word count, the target and the signed delta; for
   over-length, instruct to remove or shorten specific lines to reach the target rather
   than rewrite; for the consecutive-lines error, name the offending run of lines.
3. Pipeline: when a section is still over `effective × (1 + SCRIPT_SECTION_CARRY_CAP)`
   **after** the one repair, allow **one additional length-only repair**, bounded by a new
   `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS = 1` (ADR-001 A1's "one semantic repair" stays; this
   is a second, narrower pass with its own constant so the budget is visible). Over-length
   is the only trigger; under-length keeps carrying.
4. `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5` and both tolerances stay unchanged; the
   constants-pin test is extended to cover the consecutive-lines constant.

**Verification:** FakeProvider e2e tests for each new path; revert-and-confirm-failure on
the length-only repair; the repair bound per job is now ≤ `2 × num_sections + 1` and
asserted; full suite green; `ruff` clean.

### 14.9 — Gate B-3, local only (PM)

Same protocol as Task 13.9 / plan §4.4 local matrix, same thresholds, plus one real
thumbnail-text and one real YouTube-package generation on the winning project (schema
validity, human-read). Media gate: run the pipeline and record durations; the duration and
A/V thresholds are evaluated **as declared** — if the owner has not decided the pace
question before the run, the media gate is reported FAIL with the measured pace and the
decision recorded as still open. Evidence `data/quality_reviews/phase14/gate-b3/`; report
`docs/operations/phase14-gate-b3.md`.

**Pass:** the unchanged Phase 13 Gate B rule. A pass makes D11 an evidence-backed
promotion rather than an override; a fail leaves D11 as an owner override, recorded as
such, and 13.10 still resumes (D11), with the report stating plainly what the local path
does and does not achieve.

### 14.6 (revised) — Resume Task 13.10, local-only

Dependency: 14.7, 14.8, 14.9 done. Allowed files and pass criteria as before, with the
rollout mode fixed by D9–D11: development and packaged default `local`; Ollama is a
documented prerequisite; the rollback drill becomes "Ollama stopped → app starts, AI
screens show guidance, non-AI features work → Ollama started → generation resumes",
replacing the Gemini rollback drill.

### Execution order and partition

14.7 → 14.8 (Coder, sequential; PM reviews each diff) → 14.9 (PM runs; Coder idle) → 14.6.
The Coder mirrors this amendment into task cards 14.7–14.9 and a revised 14.6 in
`.viepilot/phases/14-ai-gateway-resilience/tasks/` **before** any code (the folder is
Coder-owned; the PM reviews the cards against this section).

## 13. Amendment G (2026-09-22, after Gate B-3) — decisions delegated to the PM

Authority: the owner delegated the three open product decisions to the PM on 2026-09-22
(`/vp-auto` "trao quyền quyết định cho bạn"). Decisions D13–D16 are recorded in
`docs/brainstorm/session-2026-09-21.md` §Addendum 2 with the evidence they rest on.
Gate B-3 evidence: `docs/operations/phase14-gate-b3.md`.

### D13 — Pace calibration: measured, not assumed

**Measurement (PM, real Edge TTS, the Gate B-3 winning script, 730 words / 43 lines,
silences 20.6 s included; `data/quality_reviews/phase14/gate-b3/pace-calibration.json`):**

| Speaker `speed` | Total seconds | Words per minute (incl. silences) |
|---:|---:|---:|
| 0.75 (floor `TTS_SPEED_MIN`) | 394.3 | **111** |
| 0.85 | 350.7 | **125** |
| 0.90 | 332.5 | **132** |
| 1.00 (default) | 301.5 | **145** — reproduces the Gate B-3 media run exactly |
| 1.10 | 276.2 | **159** |

Consequences: `CEFR_WORDS_PER_MINUTE["B1"] = 100` was never achievable — even at the
floor speed the pipeline's 730–800-word "eight minutes" plays in 6.6 minutes. Slowing
alone cannot fix it; word targets must follow the measured pace.

**Decision:** planned pace = measured pace. Introduce a per-level default speaker speed and
set the WPM table to the measured value at that speed, using measured points only:

| Level | Default `speed` | `CEFR_WORDS_PER_MINUTE` | 8-min target |
|---|---:|---:|---:|
| A1 | 0.75 | 111 | 888 |
| A2 | 0.75 | 111 | 888 |
| B1 | 0.85 | 125 | 1,000 |
| B2 | 0.90 | 132 | 1,056 |
| C1 | 1.00 | 145 | 1,160 |
| C2 | 1.10 | 159 | 1,272 |

This keeps the pedagogical ordering (slower for lower levels) with speech that stays
natural (no level below the 0.75 floor), and makes "eight minutes" mean eight minutes.
The media thresholds (432–528 s, A/V ≤ 1.0 s), the ±10% total gate and the ±15% section
trigger are **unchanged**; what changes is the *target*, from an unmeasured number to a
measured one. The `prompts/script/cefr_*.txt` "Pace" lines are updated in the same change
so the prompt and the constant stay one source of truth (the constant's own comment says
it was copied from those prompts).

### D14 — A/V padding

Rule, declared before the investigation: the renderer is inspected; if the 2.5 s tail is
unintentional (encoder priming, `-shortest` rounding, trailing silence), it is fixed and
the 1.0 s threshold stands; if it is a deliberate design element (end frame/fade), the
threshold is re-declared as ≤ 3.0 s with that reason written in the task card, and the
runner constant `AV_DIFF_MAX_SECONDS` follows the declaration. No silent change either way.

### D15 — Learning: repair by removal, bounded by the minimum counts

Gate B-2 and B-3 each lost one learning pack to a single ungrounded item after the one
repair ran (`learning_pack_repair ok` in telemetry, item still not in the transcript).
**Decision:** after the one repair, items that still fail grounding/answer checks are
**dropped**, and the pack is published only if every remaining count still meets the
existing minimums (`LEARNING_MIN_*`, from the prompt's own stated ranges); otherwise the
job fails as today. Every published item is still grounded; nothing is invented; the
minimums are unchanged. Dropped items are recorded in the job's `metrics_json`
(`dropped_items: [{kind, key, reason}]`) so the effect is measurable.

### D16 — Phase 13 close-out and Task 14.6

14.6 (Coder side, `1c89b6a`) is accepted with one copy fix (README rollback note still
sends the reader to an in-app key form that 14.7 removed). With 14.6 done, **Task 13.10
is complete under D11** and Phase 13 closes with an explicit decision record: local is the
primary and only runtime by owner decision; Gate B-3 script gate passed 5/5 under the
unchanged rule; the residual learning and media gaps are tracked as Phase 14 tasks
14.10/14.11 and re-measured in Gate B-4.

### 14.10 — Pace calibration (Coder; PM measured)

**Allowed files:** `app/core/constants.py`, `prompts/script/cefr_a1.txt` … `cefr_c2.txt`
(the "Pace" line only), `app/models/project.py` (default speed derived from level),
`app/services/project_service.py` (apply the level default at speaker creation when no
speed is given), `frontend/static/js/step1_config.js` and `frontend/pages/step1_config.html`
(only if the speed control's default must follow the level), `app/services/video_service.py`
(D14 investigation/fix only), `scripts/run_ai_operational_trial.py` (only
`AV_DIFF_MAX_SECONDS` if D14 re-declares), `tests/test_script_pipeline.py`,
`tests/test_project_service.py`, `tests/test_video_service.py`, `tests/fixtures/ai/*`.

**Actions:** implement D13's two tables as named constants (`CEFR_DEFAULT_TTS_SPEED`,
`CEFR_WORDS_PER_MINUTE`); a new speaker without an explicit `speed` gets the level
default; existing projects keep their stored speeds; pin test asserts the table equals the
measured values above; D14 investigation with the finding written in the card before any
change. Existing fixtures that assume 800 words for B1 8-min are updated with a one-line
justification each.

**Verification:** `compute_target_words("B1", 8) == 1000`; speaker default speed per level;
FakeProvider e2e still green at the new targets (the runner's per-run range already derives
from the constant); D14 outcome recorded; full suite green; `ruff` clean.

### 14.11 — Learning repair by removal (Coder)

**Allowed files:** `app/services/learning_pipeline.py`, `app/core/constants.py`,
`prompts/learning/learning_repair.txt` (optional wording), `tests/test_learning_pipeline.py`,
`tests/fixtures/ai/*`.

**Actions:** implement D15. Order: validate → one repair (unchanged) → drop still-failing
items → re-validate counts against `LEARNING_MIN_*` → publish or fail
(`pack_validation_failed` with the dropped list in the message tail). Record
`dropped_items` in `metrics_json` via the existing `record_generation_call` shape or a
sibling key (no new column).

**Verification:** e2e tests: one ungrounded idiom → dropped → `complete` with
`dropped_items` recorded; drop that would breach a minimum → `pack_validation_failed`;
revert-and-confirm-failure on the drop step; full suite green; `ruff` clean.

### 14.12 — Gate B-4, local only (PM)

Protocol of 14.9 at the new targets (B1 8-min = 1,000 words; the runner's ranges derive
from the constant), same thresholds, media on the winner, learning on every completed
script. Report `docs/operations/phase14-gate-b4.md`. **Pass:** the unchanged Phase 13 Gate
B rule; a pass turns D11 into an evidence-backed promotion.

### Execution order

README copy fix (14.6) → 14.10 → 14.11 (Coder, doc-first cards reviewed by the PM before
code, sequential) → 14.12 (PM; Coder idle) → Phase 14 close-out.
