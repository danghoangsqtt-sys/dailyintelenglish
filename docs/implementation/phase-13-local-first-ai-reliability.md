# Phase 13 Implementation Plan — Local-First AI Reliability

**Status:** Approved for execution by the user on 2026-09-18
**Owner:** Daily Intel English Studio
**Source:** `docs/brainstorm/session-2026-09-18.md`
**Execution workflow:** ViePilot `vp-auto`
**Target platform:** Windows, NVIDIA RTX 3060 12 GB VRAM, 32 GB system RAM
**Target outcome:** Durable local-first script and learning generation, with an explicit stable Gemini fallback and a verified real 5–10 minute production pipeline.

## 1. Why this phase exists

The current synchronous Gemini request path failed during a real eight-minute trial:
the application exhausted its fixed request timeout and also encountered upstream 503
overload. The browser request, provider request, validation, and persistence are one
long failure domain. Changing API keys or selecting another preview model cannot make
that architecture durable.

Phase 13 therefore changes the generation boundary, not merely the model name:

1. Script and learning generation become durable jobs.
2. Provider-specific behavior is isolated behind one gateway.
3. A local model is qualified on the actual workstation before becoming primary.
4. Long scripts are generated and validated in resumable sections.
5. Cloud fallback is bounded, visible, and opt-out.
6. Promotion to local-primary requires repeated real evidence, including Edge TTS,
   audio mixing, and ffmpeg video rendering.

## 2. Non-negotiable invariants

These rules are acceptance constraints, not implementation suggestions.

1. **No data loss:** existing projects, scripts, learning content, media, and settings
   must remain readable. Schema changes are additive and forward-only.
2. **No partial publication:** a partially generated script or learning pack must never
   replace the project's current valid content.
3. **No lock during inference:** SQLite transactions and the process-wide write lock
   must be held only for short snapshots or atomic saves, never while waiting for a
   model or network.
4. **No stale overwrite:** every job records hashes of the inputs that determine its
   result. A changed project/script makes an old result `stale`, not current.
5. **No hidden cloud use:** local-to-cloud fallback is recorded in job state and shown
   in the UI. If fallback is disabled, the job fails locally with an actionable error.
6. **No retry multiplication:** only the provider router owns the total retry/deadline
   budget. Providers expose normalized retryability but do not create nested retry
   storms.
7. **No secret leakage:** API keys, authorization headers, complete prompts, and model
   responses containing user content are not emitted into routine logs or API errors.
8. **No external exposure:** the local model endpoint defaults to
   `http://127.0.0.1:11434`; non-loopback URLs require an explicit future security
   design and are rejected in this phase.
9. **No model bundled in the EXE:** Ollama and model weights are external prerequisites.
   The application must still start when either is absent.
10. **Rollback stays live:** `DIE_AI_MODE=gemini|local|hybrid` and equivalent persisted
    settings preserve a Gemini-only recovery path without reversing a migration.
11. **Compatibility is temporary but real:** existing synchronous endpoints remain for
    one compatibility release; the UI uses the new job API after migration.
12. **Evidence over assumption:** local-primary is enabled only after Gate A and Gate B
    pass. A failed gate leaves local mode optional/experimental.

## 3. Scope

### In scope

- Script generation and single-line regeneration provider routing.
- Learning-pack generation.
- Ollama local provider and stable Gemini cloud provider.
- Provider health, settings, normalized errors, metrics, bounded retries, circuit
  breaking, and explicit fallback.
- Durable AI jobs, checkpoints, recovery, cancellation, idempotency, stale-result
  prevention, and atomic persistence.
- Outline/section/repair script prompts and deterministic validation.
- Learning-pack grounding and answer consistency checks.
- Step 2/3 progress, refresh recovery, cancellation, retry, and diagnostics.
- Automated unit/service/API/browser coverage.
- A real no-mock operational runner and the full eight-minute TTS/audio/video trial.
- Installation, packaging, operations, diagnostics, and rollback documentation.

### Out of scope

- Replacing Edge TTS or changing audio/video render architecture.
- Fine-tuning or training a model.
- Bundling Ollama/model weights in PyInstaller output.
- Exposing Ollama to LAN/Internet.
- Automatically migrating thumbnail and YouTube-package generation in the critical
  path. Their existing synchronous UX remains, but their provider transport/retry/model
  selection is migrated to the shared gateway in 13.7 so Phase 13 does not leave four
  conflicting Gemini implementations behind.
- Deleting legacy synchronous endpoints in this phase.

## 4. Selected architecture and defaults

### Provider policy

| Setting | Initial value | Rule |
|---|---:|---|
| AI mode | `hybrid` in development | Local first, one visible stable-cloud fallback |
| Packaged default | `gemini` until onboarding is verified | EXE must run without Ollama |
| Local provider | Ollama on `127.0.0.1:11434` | Loopback only |
| Local candidate | `qwen3.5:9b` | Pin resolved digest after pull |
| Local context | 16,384 tokens | Reduce only on measured memory instability |
| Local concurrency | 1 | One worker and one generation semaphore |
| Cloud fallback | `gemini-3.5-flash` candidate | Confirm availability against official API before pinning |
| Preview cloud models | Disabled from automatic routing | Canary/manual comparison only |
| Semantic repair | Maximum 1 | Only failed section/items plus validator errors |
| Cloud fallback | Maximum 1 | No multi-model cascade |

The exact cloud model identifier is a deployment setting, not a hard-coded assumption.
Qualification must call the provider's model-list/metadata endpoint or an official
documented generation endpoint before it is stored as the default.

### Components

```text
Step 2 / Step 3 UI
        |
        v
AI Jobs API --short DB tx--> ai_generation_jobs/checkpoints
        |                              ^
        v                              |
single in-process worker ----atomic state/save transactions
        |
        v
task pipeline --> provider router --> Ollama (primary)
        |                  \-----> Gemini stable (bounded fallback)
        v
schema + semantic validation --> checkpoint/final atomic persistence
```

### Provider contract

All providers implement one async contract with:

- request: operation, prompt/messages, response schema, temperature, context/output
  limits, timeout/deadline, correlation/job ID, and cancellation signal;
- result: text/structured value, provider, resolved model/digest, timing, token/eval
  counters when available, and provider request/interaction ID;
- capabilities: structured output, cancellation, background operation, streaming,
  token metrics;
- normalized errors: `provider_unavailable`, `model_missing`, `timeout`,
  `rate_limited`, `invalid_output`, `authentication_failed`, `cancelled`,
  `stale_result`, and `internal_error`.

Services ask for a capability (`script`, `line_rewrite`, `learning`), never import a
provider client directly. Thumbnail text and YouTube metadata also use gateway
capabilities after 13.7, but only script and learning become durable jobs in this phase.
Gemini remote-background support is an optional provider capability: the application DB
job remains the source of truth, and an async foreground Gemini call inside the worker
is valid when the account/model does not expose remote background operations.

## 5. Durable job contract

### Database migration `006_ai_generation_jobs.sql`

`ai_generation_jobs` is additive and contains at minimum:

- `id TEXT PRIMARY KEY` (UUID), `project_id TEXT NOT NULL`, `operation TEXT NOT NULL`;
- `status TEXT NOT NULL`, `stage TEXT NOT NULL`, `progress INTEGER NOT NULL`;
- `requested_provider TEXT`, `actual_provider TEXT`, `model TEXT`, `model_digest TEXT`;
- `input_snapshot_json TEXT NOT NULL`, `input_hash TEXT NOT NULL`,
  `script_hash_at_start TEXT`, `prompt_hash TEXT`, `template_hash TEXT`,
  `config_hash TEXT NOT NULL`, `pipeline_version TEXT NOT NULL`;
- `idempotency_key TEXT NOT NULL`, `attempt INTEGER NOT NULL DEFAULT 0`;
- `repair_count INTEGER NOT NULL DEFAULT 0`, `fallback_count INTEGER NOT NULL DEFAULT 0`,
  `recovery_count INTEGER NOT NULL DEFAULT 0`;
- `fallback_used INTEGER NOT NULL DEFAULT 0`, `fallback_reason TEXT`;
- `cancel_requested INTEGER NOT NULL DEFAULT 0`, `remote_interaction_id TEXT`;
- `lease_owner TEXT`, `lease_expires_at TEXT`, `heartbeat_at TEXT`;
- `error_code TEXT`, `error_message TEXT`, `metrics_json TEXT NOT NULL DEFAULT '{}'`;
- `created_at`, `started_at`, `updated_at`, `finished_at` UTC timestamps;
- foreign key to projects with `ON DELETE CASCADE`;
- CHECK constraints for operation/status/progress/booleans;
- a partial unique index for one active (`pending|running|validating`) job per
  project/operation;
- an index supporting startup recovery by status/update time.
- a unique idempotency key scoped to project/operation and indexes supporting atomic
  claim and recent-job polling.

`ai_generation_checkpoints` contains at minimum:

- `id`, `job_id`, `section_index`, `stage`, `status`, `input_hash`;
- `result_json`, `metrics_json`, `created_at`, `updated_at`;
- unique `(job_id, stage, section_index)` and cascade delete by job.

No generated data is placed in these tables as the project's current content until
final validation succeeds.

### State machine

```text
pending -> running -> validating -> complete
              |            |----------> error
              |-----------------------> cancelled
              |-----------------------> stale
```

- `fallback` is a visible stage/metadata event, not a terminal status.
- Terminal states are immutable except for adding non-semantic diagnostic metadata.
- Cancel is idempotent. Cancelling an already terminal job returns its terminal state.
- Duplicate create requests return the active equivalent job, not a second worker item.
- There is exactly one active job per project/operation. If inputs change, the previous
  active job is first made stale/cancelled through a legal transition before a new one
  can be created; the partial unique index is not weakened with prompt hashes.
- Startup recovery resumes valid script checkpoints; learning restarts at most once.
- A job whose hashes no longer match is marked `stale` and never persisted.
- Jobs abandoned in a non-terminal state beyond the recovery lease are reclaimed once;
  repeated crash/recovery loops terminate as `error` with a specific code.
- A worker atomically claims a job with a conditional update, lease owner, heartbeat,
  and expiry. It never performs separate unguarded SELECT-then-UPDATE claiming.
- “Durable” means intent, checkpoints, and state survive browser navigation and process
  restart. In-process inference does not continue while the application/EXE is stopped;
  it resumes or restarts safely on the next startup.
- Shutdown ordering is: stop accepting jobs, request worker stop, allow a bounded grace
  period while persisting resumable state, close provider clients, then close the DB.

### API contract

- `POST /api/projects/{project_id}/ai-jobs`
  - body: `{ "operation": "script" | "learning", "idempotency_key"?: string }`
  - returns HTTP 202 for a new job or HTTP 200/202 with the same active job for an
    idempotent duplicate.
- `GET /api/projects/{project_id}/ai-jobs/active?operation=...`
  - returns active job or 404/empty contract chosen consistently by existing API style.
- `GET /api/projects/{project_id}/ai-jobs/{job_id}`
  - returns status, stage, integer progress, provider/model, elapsed/metrics, safe error,
    fallback data, and result readiness; never full prompts or secrets.
- `POST /api/projects/{project_id}/ai-jobs/{job_id}/cancel`
  - idempotent; sets durable cancel intent before interrupting in-memory work.
- `GET /api/ai/health`
  - reports mode, Ollama reachability, model presence/digest, and fallback configured;
    it does not expose an API key and does not make app startup fail.

Every status/cancel lookup verifies that the job belongs to the path's project ID. Safe
API payloads do not expose remote interaction IDs, full filesystem paths, raw provider
bodies, or diagnostic exception text.

Legacy script/learning generate endpoints retain their synchronous response contract
for one compatibility release, are explicitly deprecated after the new UI and real
trial pass, and are not counted as the production durable path. They can be disabled in
packaged/production configuration after callers migrate. They must not be silently
redefined to return a different response shape.

## 6. Content pipelines

### Script pipeline

1. Snapshot project, speakers, genre, accent, CEFR, requested duration, and prompt
   versions under a short read transaction; compute canonical hashes.
2. Compute target words from CEFR WPM × requested minutes. B1 eight minutes initially
   targets approximately 800 spoken words.
3. Generate a compact outline with section objectives, word budgets, language features,
   speaker allocation, and intro/outro placement.
4. Generate 1–2 minute sections with the outline plus a compact prior-section summary.
5. Validate each section before checkpointing: schema, allowed speaker UUIDs, word
   envelope, turn-length/consecutive-turn limits, topic relevance, and required
   language-feature policy.
6. On a repairable failure, send only the failed section and explicit validator errors
   for one repair pass. Then fall back once or fail transparently.
7. Merge server-side; assign line UUIDs server-side; perform global validation for total
   words, speaker balance, repetition, order, intro/outro, and CEFR warnings.
8. Re-check job hashes and cancel intent; atomically replace script and update project
   status only if the result is still current and valid.

Initial tolerance values must be named constants and covered by tests. The provisional
acceptance range is ±15% for individual section budgets and ±10% globally; speaker
balance is no worse than 65/35 for two speakers unless the genre explicitly requires
otherwise; no model-invented speaker ID; no exact duplicate line; and the normalized
repeated 8-gram ratio is below 1%. Topic relevance and CEFR heuristics remain warnings
plus human-review gates rather than brittle hard rejects. Thresholds may be tightened
using Gate B evidence; they may not be silently relaxed.

### Learning pipeline

1. Snapshot only the persisted final script and its canonical hash.
2. Generate with low temperature and the existing `LearningPackOut` schema.
3. Validate requested counts, normalized transcript grounding for selected expressions
   and quoted examples, option/answer consistency, and duplicate items.
4. Repair only failed items once.
5. Re-check the script hash and cancel intent, then atomically replace learning content.
6. IPA and Vietnamese definitions are explicitly marked model-generated unless a
   deterministic dictionary source is added later; Gate B includes human review.

## 7. Configuration, security, and observability

Persist non-secret AI settings in the existing `app_settings` table and support env
overrides for operations/rollback:

- `DIE_AI_MODE=gemini|local|hybrid`
- `DIE_OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `DIE_OLLAMA_MODEL=qwen3.5:9b`
- `DIE_OLLAMA_CONTEXT=16384`
- `DIE_OLLAMA_KEEP_ALIVE=5m`
- `DIE_GEMINI_MODEL=<verified stable model id>`
- `DIE_AI_CLOUD_FALLBACK=true|false`
- named total deadlines and retry limits per operation.

Only the Gemini key is secret. It remains masked by the existing settings API. Logs use
job ID, provider, resolved model/digest, prompt hash, stage, attempt, latency, counters,
validation code, fallback reason, and exception type/`repr`. Prompt bodies, response
bodies, API keys, and auth headers are excluded from normal logs.

The Ollama URL parser must reject credentials, non-HTTP schemes, and non-loopback hosts.
Health probes use short timeouts and are informational; the app boots in Gemini-only
mode or with an actionable degraded status.

## 8. Work packages and strict task contracts

Every task starts only after its task card status is changed to `in_progress`. Each
task card lists its exact allowed files. A newly discovered required file pauses that
task until the plan and allowed-file list are updated. Existing unrelated changes are
never staged or overwritten.

### 13.0 — Freeze baseline, ADR, database backup, and rollback contract

**Allowed files:** this plan, Phase 13 ViePilot state/task cards,
`docs/architecture/adr-001-local-first-ai.md`, `tests/fixtures/ai/*`,
`scripts/verify_ai_baseline.py`, `.env.example`, `CHANGELOG.md` (entry only after proof).

**Actions:** capture current API response fixtures without secrets; record A2/B1/C1
golden inputs; add ADR; add a read-only baseline verifier; create a timestamped copy of
`data/app.db` in `data/backups/` before any migration is executed, using SQLite Online
Backup API or `sqlite3 .backup` rather than filesystem copy while the server may write;
record SHA-256 and size; document recovery to Gemini mode. The backup contains the
stored Gemini key, stays gitignored/local, and must never be uploaded.

**Verification:** baseline verifier exits 0; backup opens with SQLite,
`PRAGMA integrity_check` returns `ok`, `PRAGMA foreign_key_check` is empty, and schema
version/project counts match the source at backup time; `git diff --check` is clean.

**Rollback:** documentation/fixtures can be reverted; DB backup is retained and never
restored over the live DB automatically.

### 13.1 — Provision and qualify Ollama (Gate A)

**Allowed files:** `scripts/qualify_local_ai.py`, `docs/operations/local-ai.md`,
`artifacts/phase13/gate-a/*` (gitignored evidence), and explicitly documented external
Ollama installation/model storage.

**Actions:** install Ollama using its official Windows distribution; verify the NVIDIA
driver meets the runtime's official minimum; confirm loopback
bind; pull `qwen3.5:9b`; record Ollama/driver/model digest and size; run text and nested
schema probes; measure cold/warm latency, tokens/sec, VRAM/RAM, cancellation, unload,
server-down, and model-missing behavior.

Set `OLLAMA_HOST=127.0.0.1:11434`, one loaded model, one parallel request, a small queue,
and local-only/cloud-disabled behavior where supported. Confirm the listener is not
`0.0.0.0`/LAN, `ollama ps` reports full GPU offload, and collect `nvidia-smi` once per
second during probes. Because Ollama for Windows may auto-update, runtime version and
model digest changes raise a health warning and require requalification.

**Gate A pass:** nested schema probe validates 3/3; no OOM, TDR, or OS/GPU instability;
16K steady generation leaves at least 1.5 GiB VRAM and 4 GiB system RAM free; model is
100% GPU-offloaded; cold and warm requests work; cancel/unavailable/model-missing states
are detectable; endpoint is loopback-only. If headroom alone fails, test in order:
8K context, supported Flash Attention, then q8_0 KV cache, recording every change. If
the gate still fails, continue with Gemini primary and mark local experimental.

### 13.2 — Provider-neutral gateway

**Allowed files:** `app/services/ai/**`, `app/core/config.py`,
`app/core/constants.py`, `app/core/exceptions.py`, `requirements.txt`,
`tests/test_ai_contracts.py`, `tests/test_ai_providers.py`,
`tests/test_ai_router.py`, `tests/test_ai_validation.py`.

**Actions:** implement typed contracts/errors, Ollama adapter using async `httpx`, stable
Gemini adapter, centralized routing/deadlines/retries/circuit state/metrics, schema plus
semantic validator primitives, and fake provider support for ordinary tests.

**Verification:** provider contract suite passes; retry budget proves no nested retries;
timeout/cancel/auth/429/5xx/malformed output normalize correctly; log-capture test proves
secrets and full prompts are absent; ruff is clean.

**Rollback:** legacy services do not route through the gateway until this task passes.

### 13.3 — Shared transactions and durable jobs

**Allowed files:** `app/db/transactions.py`, `app/db/migrations/006_ai_generation_jobs.sql`,
`app/models/ai_job.py`, `app/services/ai_job_service.py`,
`app/services/ai_worker.py`, `app/api/ai_jobs.py`, `app/api/projects.py`,
`app/api/learning.py`, `app/api/settings.py`, `app/api/audio.py`,
`app/api/thumbnail.py`, `app/api/tts.py`, `app/api/video.py`, `app/api/youtube.py`,
`app/main.py`, `tests/conftest.py`,
`tests/test_projects_write_lock.py`, `tests/test_ai_job_database.py`,
`tests/test_ai_job_service.py`, `tests/test_ai_jobs_api.py`,
`tests/test_ai_worker.py`.

**Actions:** move the single DB lock/transaction helpers out of the projects router and
update every reverse-importing router/test;
apply additive migration; implement state transitions, unique active job, idempotency,
short transactions, cancellation, startup recovery, leases, stale hashes, and worker
lifespan start/stop.

**Verification:** fresh and upgraded DB migration tests; legal/illegal transition tests;
duplicate create returns one job; lock is not held during fake slow inference; cancel,
restart resume, crash-loop limit, stale result, atomic save, cascade delete, and unrelated
project concurrency pass.

**Rollback:** set Gemini compatibility mode and stop creating jobs; additive tables may
remain. Do not drop them or roll back schema destructively.

### 13.4 — Checkpointed script pipeline

**Allowed files:** `prompts/script/outline.txt`, `prompts/script/section.txt`,
`prompts/script/repair.txt`, `app/services/script_pipeline.py`,
`app/services/script_service.py`, `app/services/ai_worker.py`,
`app/core/constants.py`, `tests/fixtures/ai/*`,
`tests/test_script_pipeline.py`, `tests/test_script_service.py`,
`tests/test_script_api.py`.

**Actions:** implement deterministic targets, outline/section checkpoints, server-owned
line IDs, validation/repair/fallback, final merge, stale/cancel guards, and atomic
persistence. Preserve line-regeneration behavior through the provider gateway.

**Verification:** valid 5/8/10-minute fixtures; exact allowed speaker IDs; target/balance/
repetition/global checks; injected failed section repairs once; interrupted generation
resumes at last valid checkpoint; failure leaves prior script unchanged.

### 13.5 — Grounded learning pipeline

**Allowed files:** `prompts/learning/learning_repair.txt`,
`app/services/learning_pipeline.py`, `app/services/learning_service.py`,
`app/services/ai_worker.py`, `app/core/constants.py`,
`tests/fixtures/ai/*`, `tests/test_learning_pipeline.py`,
`tests/test_learning_service.py`, `tests/test_learning_api.py`.

**Actions:** use persisted script hash, structured low-temperature generation,
grounding/count/duplicate/answer checks, one targeted repair, stale/cancel guards, and
atomic final save.

**Verification:** five deterministic fixtures; all grounding and answer invariants;
script mutation produces `stale`; failed generation leaves old pack unchanged.

### 13.6 — Settings, health, and Step 2/3 job UX

**Allowed files:** `app/models/settings.py`, `app/services/settings_service.py`,
`app/api/settings.py`, `app/api/ai_health.py`, `app/main.py`,
`frontend/pages/settings.html`, `frontend/pages/step2_script.html`,
`frontend/pages/step3_learning.html`, `frontend/static/js/api.js`,
`frontend/static/js/settings.js`, `frontend/static/js/step2_script.js`,
`frontend/static/js/step3_learning.js`, `frontend/static/css/style.css`,
`tests/test_settings_service.py`, `tests/test_settings_api.py`,
`tests/test_ai_health_api.py`, `tests/test_ui_async_browser.py`,
`tests/test_script_jobs_browser.py`, `tests/test_learning_jobs_browser.py`.

**Actions:** persist validated non-secret settings; add safe health; create/poll/resume/
cancel/retry jobs; render queued/running/validating/fallback/terminal states; `aria-live`;
two-second visible polling with hidden-window backoff; prevent duplicate/conflicting
actions while preserving unrelated reads.

**Verification:** refresh/navigation resumes active job; duplicate click creates one job;
cancel/retry are keyboard accessible; fallback is visible; secret never appears in DOM,
API, or logs; browser tests pass at desktop and narrow viewport.

### 13.7 — Cloud fallback and compatibility

**Allowed files:** `app/services/ai/gemini_provider.py`,
`app/services/ai/router.py`, `app/services/script_service.py`,
`app/services/learning_service.py`, `app/services/thumbnail_service.py`,
`app/services/youtube_service.py`, `app/api/projects.py`, `app/api/learning.py`,
`docs/api.md`, `tests/test_ai_router.py`, `tests/test_ai_providers.py`,
`tests/test_script_api.py`, `tests/test_learning_api.py`.

**Actions:** verify/pin stable Gemini model; implement bounded remote-background path
only where live capability probing supports it, otherwise use an async foreground call
inside the durable worker; one cloud fallback; visible cost-bearing transition; migrate
all four Gemini consumers to shared transport policy; preserve legacy endpoints and
document deprecation without response-shape changes or removal.

**Verification:** forced Ollama-down yields exactly one visible Gemini fallback; disabled
fallback yields a clear local error; transient statuses honor one total deadline; auth/
validation errors do not retry; legacy contracts remain green.

### 13.8 — Automated regression and observability gate

**Allowed files:** all Phase 13 test files already listed, `tests/test_ai_logging.py`,
`scripts/check_dependencies.py`, `daily_intel_english_studio.spec` only if imports/data
require it, and docs generated by existing tooling.

**Actions:** close state-machine, concurrency, security, UI, packaging, and health gaps;
run targeted tests, full pytest, ruff, JS syntax checks, and a packaged smoke build.

**Required commands:**

```powershell
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe -m pytest -q
Get-ChildItem frontend\static\js\*.js | ForEach-Object { node --check $_.FullName }
venv\Scripts\python.exe scripts\check_dependencies.py
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

**Pass:** no deterministic failures; any claimed flake is re-run in isolation and as
part of the affected group, documented with evidence; packaged app starts even when
Ollama is stopped.

### 13.9 — Real no-mock bake-off and full operational trial (Gate B)

**Allowed files:** `scripts/run_ai_operational_trial.py`,
`docs/operations/phase13-acceptance.md`, `artifacts/phase13/gate-b/*` (evidence), and
runtime-created project/media/database rows. The test project must not be deleted.

**Actions:** start real uvicorn on a non-conflicting port; call live HTTP only; run five
consecutive B1 eight-minute local jobs, then B1 5/10 and A2/C1 samples; capture timings,
provider/model digest, repairs/fallbacks, word/balance/repetition/CEFR/learning defects,
VRAM/RAM, logs, and artifacts. For the winning configuration, synthesize every line by
real Edge TTS, mix MP3, render midnight 16:9 MP4, download, hash, size, and ffprobe both.

**Gate B pass:** fallback is OFF for the local bake-off; 5/5 complete without crash or
unrecoverable schema failure; at least 4/5 contain 720–880 words, speaker word share
35–65%, no exact duplicate line, repeated normalized 8-gram ratio below 1%, intro and
outro present, and pass the human CEFR rubric; zero invalid speaker IDs or partial
writes. First durable progress appears within 90 seconds, no section exceeds five
minutes, and total script job is at most 20 minutes. Learning is 5/5 for deterministic
schema/count/grounding/answer checks and has no critical human-reviewed Vietnamese/IPA/
grammar/answer defect. One real pipeline produces nonzero ffprobe-readable MP3/MP4 of
432–528 seconds, A/V duration difference at most 1.0 second, expected H.264/AAC codecs,
and no server ERROR/traceback. Keep the server and test project available for review.

**Decision:** pass promotes local in development; fail triggers one focused challenger
test only if justified. Otherwise ship Gemini-primary durable jobs and label local
experimental. Gate thresholds are not weakened after seeing results.

### 13.10 — Rollout, packaging, documentation, and rollback drill

**Allowed files:** `README.md`, `.viepilot/ARCHITECTURE.md`, `.viepilot/AI-GUIDE.md`,
`.viepilot/PROJECT-CONTEXT.md`, `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`,
`.viepilot/HANDOFF.json`, `docs/api.md`, `docs/prompt-guide.md`,
`docs/operations/local-ai.md`, `docs/operations/phase13-acceptance.md`,
`CHANGELOG.md`, `.env.example`, `scripts/check_dependencies.py`,
`daily_intel_english_studio.spec`, `scripts/build_exe.ps1` if verified changes are needed.

**Dependency:** the Gate B **decision**, whether pass or fail. A pass permits local-first
development rollout; a failure ships durable jobs with Gemini primary and labels local
experimental rather than blocking reliability improvements.

**Actions:** document install/pull/digest/health/disk/update/uninstall/local security;
surface missing runtime/model/VRAM/key guidance; run rollback drill: Gemini mode, Ollama
stopped, restart, script + learning success, restore hybrid, no DB repair.

**Pass:** clean install instructions are actionable; packaged startup is non-blocking;
mode/model visible in diagnostics; rollback works without data loss; docs reflect only
verified behavior.

## 9. Cross-task verification and release gates

No task is accepted until:

1. its allowed-file diff is reviewed;
2. targeted tests fail meaningfully when the implementation is reverted or fault
   injected, where practical;
3. test, lint, and syntax commands pass;
4. no raw key/prompt is present in captured logs or fixtures;
5. state artifacts record commands, results, deviations, and rollback notes;
6. the relevant git commit contains only explicit paths.

Phase 13 is complete only when all of the following are true:

- durable jobs no longer depend on one long browser connection;
- refresh, restart, cancel, idempotency, recovery, and stale protection are proven;
- local and cloud providers share one gateway/error contract;
- schema and semantic validation protect atomic persistence;
- Gate A and Gate B evidence produce an explicit local-primary or experimental decision;
- one real eight-minute script → every-line Edge TTS → MP3 → ffmpeg MP4 completes and
  reports timings, durations, sizes, hashes, logs, and warnings;
- Gemini rollback is exercised successfully without migration reversal or project loss;
- full automated suite, JS syntax, dependency check, and packaged smoke pass;
- repository state is clean and pushed only under the user's authorized workflow.

## 10. Stop conditions

Execution pauses and reports evidence instead of improvising when:

- a migration integrity check fails or existing project counts change unexpectedly;
- a required change falls outside a task's allowed files and changes architecture;
- Ollama installation requires exposing a network listener or disabling security;
- GPU/OS instability appears during Gate A;
- the official stable cloud model identifier cannot be verified;
- a secret appears in tracked output/logs;
- three consecutive attempts hit the same external blocker;
- acceptance would require weakening a predeclared Gate A/Gate B threshold.

## 11. Rollback strategy

Rollback is configuration-first and non-destructive:

1. set AI mode to `gemini` and disable local fallback;
2. cancel or allow active jobs to reach a terminal state;
3. restart the application and verify health;
4. generate script and learning through the compatibility/cloud path;
5. leave additive job/checkpoint tables in place;
6. never copy the pre-phase database backup over the live database automatically;
7. restore from backup only as a separately approved disaster-recovery action after
   preserving the failed database and verifying hashes.

This plan is the controlling implementation contract. The brainstorm remains the design
record; task cards and state files record execution evidence and any approved amendments.
