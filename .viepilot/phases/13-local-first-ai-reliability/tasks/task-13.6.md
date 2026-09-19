# Task 13.6 — Settings, Health, and Step 2/3 Job UX

- **Status:** in_progress
- **Dependency:** 13.2–13.3
- **Controlling detail:** implementation plan §7 and §8, Task 13.6

## Objective

Expose validated non-secret AI settings and safe health; move Step 2/3 to durable jobs
with visible provider/fallback, polling recovery, cancellation, retry, and accessibility.

## Allowed files

Exactly the model/service/API/page/JS/CSS/test paths listed for 13.6 in the controlling
plan.

## UX/security contract

Resume active job on load; visible polling ~2s and hidden-window backoff; no duplicate
start; actionable safe errors; `aria-live`; keyboard Cancel/Retry; no key, full prompt,
filesystem path, remote interaction ID, or raw exception in API/DOM.

## Verification and exit

Desktop/narrow browser tests prove refresh/navigation recovery, duplicate prevention,
cancel/retry, fallback banner, terminal content reload, health-down nonfatal behavior,
and settings validation/redaction.

## Plan (written before implementation)

### Two deviations from the controlling plan's literal file list, recorded before touching code

1. **No separate `app/api/ai_health.py`.** `GET /api/ai/health` already exists,
   fully implemented and tested, inside `app/api/ai_jobs.py::health_router`
   (built in Task 13.3, before this task's file list was locked in — at that
   point `app/api/ai_jobs.py` was the only allowed API file for any job-related
   route). Creating a second, separate `app/api/ai_health.py` now would either
   duplicate the route (FastAPI would register two handlers for the same path)
   or require deleting/moving the existing one — and `app/api/ai_jobs.py` is
   **not** in this task's allowed-file list, so it cannot be edited here either
   way. Resolution: keep the existing implementation as-is, do not create
   `app/api/ai_health.py`, and treat `tests/test_ai_health_api.py` (which *is*
   in this task's allowed list) as testing the existing `/api/ai/health` route
   regardless of which file implements it — the controlling plan cares about
   the route's behavior, not its filename. No route path, response shape, or
   security property changes.
2. **New shared frontend module, not in the original file list:
   `frontend/static/js/ai_job.js`.** Step 2 and Step 3 need near-identical
   job-lifecycle logic (create-or-resume, poll every ~2s with hidden-tab
   backoff, render queued/running/validating/fallback/terminal states, keyboard-
   accessible cancel/retry, `aria-live`). This project has an established
   precedent for exactly this situation — shared, page-mounted JS modules
   (`step_nav.js`, `keyboard_shortcuts.js`, `save_indicator.js`) instead of
   duplicating the same state machine twice. Duplicating ~150 lines of polling/
   state-rendering logic across `step2_script.js` and `step3_learning.js`
   would be the actual "wrong shape" here, not adding one small new shared
   file. Recorded here per the doc-first rule for a file outside the original
   allowed list, before writing any of it.

### Paths

New: `app/services/ai/gateway.py` is **not** needed — `app/main.py` already
imports `AIRouter`/`OllamaProvider`/`GeminiProvider` directly, matching how
`script_service.py`'s own `_build_ai_router()` already does it (Task 13.4);
`frontend/static/js/ai_job.js` (see deviation #2), `tests/test_ai_health_api.py`,
`tests/test_script_jobs_browser.py`, `tests/test_learning_jobs_browser.py`.

Edited: `app/models/settings.py` (+`AIModeUpdate`), `app/services/settings_service.py`
(+`get_ai_mode_status`/`set_ai_mode`/`load_ai_mode_from_db`, mirroring the
existing Gemini-key functions byte-for-byte in shape), `app/api/settings.py`
(+`GET` includes `ai_mode` in the status payload, +`PUT /api/settings/ai-mode`),
`app/main.py` (construct one real `AIRouter` from `settings`, call
`ai_worker.register_handler("script", script_pipeline.make_handler(router))`
and `("learning", learning_pipeline.make_handler(router))` before
`ai_worker.start()`; call `settings_service.load_ai_mode_from_db()` in the
lifespan, same place as the existing Gemini-key loader), `frontend/pages/
settings.html` (+AI mode selector), `frontend/pages/step2_script.html`/
`step3_learning.html` (+ a job-status banner region, `aria-live="polite"`),
`frontend/static/js/api.js` (+`createScriptJob`/`createLearningJob`/
`getActiveAiJob`/`getAiJob`/`cancelAiJob`/`getAiHealth`/`getSettings` extended),
`frontend/static/js/settings.js` (+AI mode load/save), `frontend/static/js/
step2_script.js`/`step3_learning.js` (`handleGenerate` creates-or-resumes a job
and polls via `ai_job.js` instead of one blocking `Api.generateScript()` call;
on `complete`, re-fetch via the existing `Api.getScript()`/learning-content
call exactly as before — no change to how a finished result is loaded, only to
how the app waits for it), `frontend/static/css/style.css` (+job-status banner
styles, reusing existing color tokens), `tests/test_settings_service.py`/
`test_settings_api.py` (extend for AI mode), `tests/test_ui_async_browser.py`
(re-run unmodified as a regression check — no change to the autosave/dirty-
state machine this task doesn't touch).

### `frontend/static/js/ai_job.js` design

`AiJob.run({ createFn, activeFn, getFn, cancelFn, onStateChange, pollMs: 2000 })`
- On mount: call `activeFn()` first (resume-on-load) — if an active job exists,
  start polling it; otherwise wait for the caller to invoke `.start()`
  (Generate button click), which calls `createFn()` (idempotent — the backend
  already coalesces a duplicate active-job create, Task 13.3) then polls.
- Polling: `setInterval` at `pollMs` while `document.visibilityState ===
  "visible"`; backs off to a longer interval (e.g. 4x) when the tab is hidden
  (`visibilitychange` listener), matching the plan's "hidden-window backoff"
  requirement, and immediately does one poll on becoming visible again rather
  than waiting out a stale interval.
- Every poll result calls `onStateChange(job)` with the raw safe job payload
  (`status`, `stage`, `progress`, `actual_provider`, `fallback_used`,
  `error_code`/`error_message`) — the calling page owns rendering, this module
  owns only the lifecycle/timing.
- On `status in ("complete", "error", "cancelled", "stale")`: stop polling,
  call `onStateChange` one final time, resolve/reject the module's promise so
  the caller can chain "load the finished result" (`complete`) or "show a
  retry affordance" (anything else).
- `cancel()`: calls `cancelFn(jobId)` (idempotent server-side already) then
  keeps polling until the job actually reaches `cancelled` (a cancel request
  does not guarantee an instant terminal state).
- No dependency on any other shared module; a plain `window.AiJob = ...`
  object, same export style as `StepNav`/`KeyboardShortcuts`.

### Step 2/3 integration (`handleGenerate`)

Replace the current single `state.lines = await Api.generateScript(...)` call
with: render a job-status banner (`aria-live="polite"`, one fixed region per
page) → `AiJob.run({...}).start()` → on `complete`, call the existing
`Api.getScript()`/learning-content getter exactly as the page already does on
`init()` (so the "how a finished script/pack is loaded and rendered" code path
is the *same* one already tested by every existing Step 2/3 test — only *how
the page waits* changes) → hide the banner. On `error`/`cancelled`/`stale`,
show the banner's terminal state with a Retry button (re-invokes `handleGenerate`)
and, for `stale`, an explanation that the project changed and generation must
restart. `init()` also calls `activeFn()` (resume-on-load) before rendering
the empty-state, so a page refresh while a job is running reattaches to it
instead of showing a false empty/idle state — this is the literal "refresh/
navigation resumes active job" verification requirement.

Existing per-line Regenerate/autosave/inline-edit code is untouched — this
task only replaces the bulk-generation waiting mechanism, per Task 13.4/13.5's
own scope boundary (their pipelines are additive, not yet the only path).

### Accessibility / duplicate-prevention contract

`aria-live="polite"` on the status banner (not `assertive` — frequent progress
updates must not interrupt a screen reader mid-sentence); Generate/Cancel/Retry
buttons are real `<button>` elements (native keyboard support, no custom
`tabindex`/`keydown` reimplementation needed); Generate is disabled for the
entire duration a job is active (mirrors the existing double-submit-lock
pattern already used everywhere else in this app) so a second click cannot
create a duplicate job even before the server-side idempotent-create protection
(Task 13.3) would catch it.

### Best practices applied

CR-05 (all calls through `Api.*`, never raw `fetch()` in a page script), the
existing double-submit-lock/friendly-error-banner conventions already proven
on every other step page, AR-04 (no new backend exception types needed — job
errors are already safe strings from `ai_job_service`/the pipelines), and this
task's own explicit "no key, full prompt, filesystem path, remote interaction
ID, or raw exception in API/DOM" contract — already satisfied by `AIJobOut`'s
field allowlist (Task 13.3), not something this task needs to re-enforce
server-side.

### Verification commands

```
venv\Scripts\python.exe -m ruff check app\models\settings.py app\services\settings_service.py app\api\settings.py app\main.py tests\test_settings_service.py tests\test_settings_api.py tests\test_ai_health_api.py tests\test_script_jobs_browser.py tests\test_learning_jobs_browser.py
node --check frontend\static\js\ai_job.js frontend\static\js\api.js frontend\static\js\settings.js frontend\static\js\step2_script.js frontend\static\js\step3_learning.js
venv\Scripts\python.exe -m pytest tests\test_settings_service.py tests\test_settings_api.py tests\test_ai_health_api.py tests\test_script_jobs_browser.py tests\test_learning_jobs_browser.py tests\test_ui_async_browser.py -v
venv\Scripts\python.exe -m pytest tests\ -x -q
git diff --check
```
