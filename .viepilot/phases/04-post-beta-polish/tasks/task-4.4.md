# Task 4.4: P0 navigation bug fixes (Dashboard Continue + Config duplicate-project)

## Meta
- **ID**: 4.4 (inserted ahead of Task 4.2's remaining sub-tasks — see Doc-First Gate
  below for why; not part of the original 21-day/3-phase plan, scoped from a real-bug
  finding, same as Task 4.2's own origin)
- **Phase**: 4
- **Status**: done (2026-09-16)
- **Priority**: high (P0 — confirmed real bugs, not polish)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: user ran a Codex-driven **read-only** UI audit (`vp-auto` read-only mode) across
the whole app on 2026-09-16, after Task 4.2c shipped. The audit found 2 real P0 behavior
bugs plus several P1/P2 polish items. PM (this session) independently re-verified both
P0 claims by reading the actual code (not trusting the audit report alone) — both are
confirmed real, see "Current state" below. Given they affect navigation reliability
across *every* already-shipped page (not just one), PM proposed and user approved
inserting this task ahead of Task 4.2d (Thumbnail Generator) rather than deferring to
after all 7 pages are redesigned. P1/P2 findings are logged as backlog in
`.viepilot/TRACKER.md` (Decision Log, 2026-09-16 entry) — explicitly out of scope here.

## Current state (researched before writing this plan — do not re-derive from scratch)

### Bug 1 — Dashboard "Continue" button no-ops for 3 of 5 statuses
`frontend/static/js/dashboard.js:154-159` — the `data-action="continue"` click handler:
```js
if (button.dataset.action === "continue") {
  const project = allProjects.find((p) => p.id === id);
  if (project && (project.status === "draft" || project.status === "script_generated")) {
    window.location.href = `/step2?project_id=${encodeURIComponent(id)}`;
  }
}
```
The button renders unconditionally on every project card (`dashboard.js:49`). For
`audio_generated`, `video_generated`, or `complete` status, the `if` is false and
**nothing happens** — no navigation, no error, no console log. Confirmed live by PM.

Project status values (`dashboard.js:21-27`, `STATUS_LABELS`): `draft`,
`script_generated`, `audio_generated`, `video_generated`, `complete`. Confirmed via
`app/api/projects.py` / `app/api/audio.py` / `app/api/video.py` that the **only**
automatic transitions the backend ever performs are `draft → script_generated`
(`projects.py:84`), `script_generated → audio_generated` (`audio.py:69`), and
`audio_generated → video_generated` (`video.py:72`). **`complete` is never set by any
code path today** — it exists in the label map and dashboard filter but is currently
unreachable. Treat it as a real, declared status to handle defensively, not as evidence
it's used.

The 7 pipeline steps (`frontend/static/js/step_nav.js:3-11`): 1 Config, 2 Script,
3 Learning, 4 Audio, 5 Video, 6 Thumbnail, 7 YouTube.

### Bug 2 — Config page always creates a new project, ignores `project_id`
`frontend/static/js/step1_config.js`:
- Line 338: `project_id` from the URL query string is read **only** to pass to
  `StepNav.render()` for breadcrumb links — never used to fetch or prefill anything.
- Line 313-335 (`handleSubmit`): unconditionally calls `Api.createProject(buildPayload())`
  (line 327) and redirects to the **new** project's id. There is no branch that checks
  for an existing `project_id` or calls any kind of update.
- `frontend/static/js/step_nav.js:4` makes "Config" (step 1) a real clickable link from
  every other step's StepNav for the current project (`stepHref` appends `project_id`),
  so a user mid-workflow genuinely lands on `/step1?project_id=<real-id>` and sees a
  blank "new project" form — not a rare edge case.

Confirmed a real, already-existing fix path: `app/api/projects.py:129-137` has
`PUT /api/projects/{project_id}` → `project_service.update_project()`, accepting a
`ProjectUpdate` partial-patch model (`app/models/project.py:165-183`: `name`, `topic`,
`cefr_level`, `duration_minutes`, `num_speakers`, `genre`, `accent`,
`language_features`, `speakers` — every field Step 1's form collects). Its docstring
says "also used as the auto-save endpoint," but **no frontend code calls it today**
(`grep updateProject` across `frontend/` returns nothing) and `frontend/static/js/api.js`
has no wrapper for it yet — this task adds the first consumer.

## Objective

Fix both bugs using only real, already-existing backend capability — no new endpoints,
no invented regeneration/cascade logic.

### Required decisions (already settled by PM, do not re-litigate)

1. **Continue button — extend the existing status→step mapping, don't replace its
   logic.** The existing 2 cases (`draft`, `script_generated` → `/step2`) both resume to
   *the step that owns/produced that status* (draft has no script yet, so step 2 is
   where you'd make one; script_generated's script was made on step 2, so you land back
   there to review/regenerate it) — keep that pattern for the new cases rather than
   inventing a "next step" heuristic:
   - `audio_generated` → `/step4` (Audio — where that audio was generated)
   - `video_generated` → `/step5` (Video — where that video was generated)
   - `complete` → `/step7` (YouTube — the last step; defensive, currently unreachable)
   - Keep `draft`/`script_generated` → `/step2` exactly as-is.
   - Implement as a single `STATUS_TO_STEP` lookup object, not a growing if-chain.
   - If a project somehow has a status outside this map (defensive — should not happen
     given the enum), do nothing rather than throwing, matching today's silent-no-op
     safety envelope for unknown values — but this should not be reachable for any of
     the 5 known statuses after the fix, so do not treat it as a normal case.

2. **Config page — branch on whether `project_id` is present and resolve via a real
   fetch, don't guess from the URL alone.**
   - On `init()`, if `project_id` is present in the URL: call `Api.getProject(project_id)`
     (existing endpoint, `app/api/projects.py:120-126`, already returns full project incl.
     speakers).
     - If the fetch fails (bad/deleted id): show the existing error banner pattern
       ("We couldn't load this project.") — do not silently fall back to the blank
       create-form, since that's the exact bug being fixed.
     - If `project.status === "draft"`: **prefill the form** with the fetched values
       (name, topic, cefr, duration, genre, accent, language_features, speakers) and on
       submit call the new `Api.updateProject(project_id, patch)` (add this wrapper to
       `api.js`, mirroring the existing `request()` helper and the `PUT` pattern already
       used at `api.js:47`/`api.js:92`) instead of `createProject`. This is safe because
       nothing downstream has been generated yet from this config.
     - If `project.status !== "draft"` (script/audio/video already exist): render the
       form **read-only/disabled** (all inputs `disabled`, no submit button, or submit
       button removed) with a clear banner explaining configuration is locked because
       downstream content already depends on it, and that changing it here would not
       regenerate anything. **Do not** wire up silent full-rewrite semantics for
       already-progressed projects — that's a new feature (cascade/regenerate) this task
       does not add, consistent with "no fake features."
   - If `project_id` is absent (the existing "start a new project" entry point from the
     dashboard's "+ New Project" button): behave exactly as today — blank form,
     `createProject` on submit. Do not change this path at all.

## Proposed File-Level Plan

- `frontend/static/js/dashboard.js`: replace the `if` in the `continue` action handler
  with a `STATUS_TO_STEP` map lookup + `window.location.href` build, reusing the
  existing `encodeURIComponent(id)` pattern.
- `frontend/static/js/api.js`: add `updateProject: (id, patch) => request(\`/api/projects/${id}\`, { method: "PUT", body: JSON.stringify(patch) })` next to the existing `getProject`/`createProject`.
- `frontend/static/js/step1_config.js`: in `init()`, branch on `project_id` presence;
  add a fetch-and-prefill path + a read-only-lock render path; change `handleSubmit` to
  call `updateProject` when editing an existing draft project, `createProject` when not.
- `frontend/pages/step1_config.html`: only if a read-only banner element / disabled-state
  styling needs a new element — keep to the minimum, reuse existing `.error-banner` /
  `.card` classes if they already fit.
- New or extended browser test file (Codex to name and confirm in the pre-code plan,
  e.g. `tests/test_dashboard_continue_browser.py` and an extension to whichever existing
  file covers `/step1` — check for one first, e.g. `tests/test_step1_config_browser.py`
  or equivalent, before assuming it doesn't exist).

## Allowed files
- `frontend/static/js/dashboard.js`
- `frontend/static/js/api.js`
- `frontend/static/js/step1_config.js`
- `frontend/pages/step1_config.html` (only if strictly needed per above)
- Whatever existing or new browser test file(s) cover `/step1` and the dashboard —
  Codex to confirm exact filenames in the pre-code plan before touching any test file
  not listed here.
- This task card (`task-4.4.md`) for plan/evidence updates.

## PM Plan Review (2026-09-16) — APPROVED

Codex presented its pre-code plan per AR-06's 3-step process. PM independently
verified the 2 load-bearing technical claims before approving (not accepted on
description alone):
- **Confirmed**: `_replace_speakers()` (`app/services/project_service.py:62-72`)
  deletes all speaker rows and generates fresh `uuid.uuid4()` ids on every `PUT` that
  includes `speakers` — this is exactly why Codex's plan is right to gate the write
  path strictly on `status === "draft"` from the server response (never trust a
  client-side assumption about status) and never allow it once script/audio/video
  already reference the old speaker ids.
- **Checked Codex's own out-of-scope flag**: `step1_config.js::buildPayload()`
  hardcodes `tts_engine: "omnivoice"` for new speakers on the create path — real, but
  harmless today because `tts_service.py::_synthesize_omnivoice()` (line 70)
  unconditionally raises `_OmniVoiceUnavailableError`, so every synthesis silently
  falls back to Edge TTS regardless. Confirmed correct to leave untouched — logged as
  a low-priority backlog cleanup item (stale code contradicting the 2026-09-13
  "Edge TTS is the sole official engine" decision and the backend model's own
  `edge_tts` default), not a functional bug, not part of Task 4.4.

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `frontend/static/js/dashboard.js`
- `frontend/static/js/api.js`
- `frontend/static/js/step1_config.js`
- `frontend/pages/step1_config.html` (minimal: mode-based title/subtitle hook + a
  read-only-state banner element; no layout redesign)
- `tests/test_dashboard_browser.py` (extend — confirmed pre-existing, no conflict)
- `tests/test_step1_config_edit_browser.py` (new — confirmed no existing file at
  this path)
- This task card, for evidence only (Status field remains PM-only)

**Plan approved as presented — no changes requested.** Codex may proceed to
implementation.

## Verification checklist
- [ ] Manual: dashboard with a project in each of the 5 statuses (seed via direct DB
  write or by walking a real project through the pipeline) — click Continue on each,
  confirm it lands on the mapped step and never no-ops.
- [ ] Manual: open Config (`/step1?project_id=<draft-project>`), confirm form is
  prefilled with the real values, edit one field, submit, confirm `Api.updateProject`
  was called (not `createProject`) and the same project id is preserved (no duplicate
  created) — verify via the dashboard project count before/after.
- [ ] Manual: open Config for a `script_generated`/`audio_generated`/`video_generated`
  project, confirm the form renders locked/read-only with no way to submit a change.
- [ ] Manual: open Config with no `project_id` (from "+ New Project"), confirm the
  blank-form + create-new-project path is completely unchanged.
- [ ] New/extended browser tests pass; full suite still 544+/544 (whatever the count is
  after this task's new tests) with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS files, `git diff --check` —
  all clean, real output pasted.

## Implementer Evidence (2026-09-16)

Implementation is ready for PM review. Implementer did not change the task Status and
did not commit or push.

### Manual browser verification

- Started the real local app and exercised it through a visible Chrome session on a
  fresh localhost origin (to exclude a previously cached Dashboard bundle).
- Seeded five disposable projects and clicked the real Dashboard **Continue** button:
  `draft → /step2`, `script_generated → /step2`, `audio_generated → /step4`,
  `video_generated → /step5`, and `complete → /step7`. All five actual URLs retained
  the matching `project_id`; none no-op'd.
- Opened a real draft at `/step1?project_id=...`: the form was populated with its real
  name/topic/level/duration/speaker/genre/accent/features. Changed the name and saved;
  the browser navigated to Step 2 with the same project id. API verification before
  and after reported `count_before=181` and `count_after=181`, and GET returned the
  same id plus the updated name — no duplicate project was created.
- Opened a real `script_generated` project at Step 1: the read-only banner was visible,
  the populated form remained visible, `enabledControls=0`, and the submit button was
  hidden.
- Opened `/step1` without `project_id`, filled the blank form, and created a disposable
  project. The button remained **Create Project** and navigation used the newly created
  id, preserving the original create flow.
- Deleted exactly the six disposable QA projects afterward; the project count returned
  to its pre-verification value (`176`).

### Targeted browser tests

Command:

```text
venv\Scripts\python.exe -m pytest tests/test_dashboard_browser.py tests/test_step1_config_edit_browser.py -q
```

Raw output:

```text
......................                                                   [100%]
22 passed in 35.51s
```

### Existing Step 1 / navigation regressions

Command:

```text
venv\Scripts\python.exe -m pytest tests/test_step1_escape_html_browser.py tests/test_step1_accent_disclosure_browser.py tests/test_keyboard_shortcuts_browser.py tests/test_step_nav_browser.py -q
```

Raw output:

```text
.........................                                                [100%]
25 passed in 38.07s
```

### Full suite

Command:

```text
venv\Scripts\python.exe -m pytest tests/ -q
```

Raw terminal failure report and summary from the full run:

```text
================================== FAILURES ===================================
______________ test_generate_script_backoff_sequence_is_1s_2s_4s ______________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001C3841BA120>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_script_backoff_sequence_is_1s_2s_4s(monkeypatch, no_real_sleep):
        queue_responses(
            monkeypatch,
            [
                FakeResponse(429, text="rate limited"),
                FakeResponse(429, text="rate limited"),
                FakeResponse(429, text="rate limited"),
                gemini_ok_response(VALID_LINES),
            ],
        )

        await script_service.generate_script("proj-1", SAMPLE_CONFIG)

>       assert no_real_sleep == [1.0, 2.0, 4.0]
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0, 2.0, 4.0]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 1173830 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_script_service.py:145: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=3 retry_in_s=4.0
_______ test_generate_script_exhausts_one_model_then_falls_back_to_next _______

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001C384DE71C0>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_script_exhausts_one_model_then_falls_back_to_next(monkeypatch, no_real_sleep):
        """After 4 failed attempts on the primary model, the next fallback model is tried."""
        calls = queue_responses(
            monkeypatch,
            [FakeResponse(429, text="rate limited")] * 4 + [gemini_ok_response(VALID_LINES)],
        )

        lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG)

        assert len(lines) == 2
        assert calls["n"] == 5
        assert calls["models"] == [script_service.GEMINI_MODEL_FALLBACKS[0]] * 4 + [
            script_service.GEMINI_MODEL_FALLBACKS[1]
        ]
>       assert no_real_sleep == [1.0, 2.0, 4.0]  # backoff resets per model, but only 1 model exhausted here
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0, 2.0, 4.0]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 4742943 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_script_service.py:162: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.script_service:script_service.py:159 gemini_model_exhausted model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 � trying next fallback model
______________ test_generate_script_retries_on_503_then_succeeds ______________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001C384DE7000>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_script_retries_on_503_then_succeeds(monkeypatch, no_real_sleep):
        """503 (model temporarily overloaded) is retried just like 429, not treated as fatal."""
        calls = queue_responses(
            monkeypatch,
            [FakeResponse(503, text="model overloaded"), gemini_ok_response(VALID_LINES)],
        )

        lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG)

        assert calls["n"] == 2
        assert len(lines) == 2
>       assert no_real_sleep == [1.0]
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 3296762 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_script_service.py:176: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=503 attempt=1 retry_in_s=1.0
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s
FAILED tests/test_script_service.py::test_generate_script_exhausts_one_model_then_falls_back_to_next
FAILED tests/test_script_service.py::test_generate_script_retries_on_503_then_succeeds
3 failed, 555 passed, 2 warnings in 1375.22s (0:22:55)
```

All three failures are the already-known Gemini retry fixture flake class. In this full
run, the fixture monkeypatched the shared `asyncio.sleep` module function and captured
millions of unrelated `0.1` event-loop sleeps; the service log still recorded the
expected retry delays. Per the agreed verification protocol, the exact failing tests
were rerun together in isolation.

Isolation command:

```text
venv\Scripts\python.exe -m pytest tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s tests/test_script_service.py::test_generate_script_exhausts_one_model_then_falls_back_to_next tests/test_script_service.py::test_generate_script_retries_on_503_then_succeeds -q
```

Raw output:

```text
...                                                                      [100%]
3 passed in 0.69s
```

### Ruff

Command:

```text
venv\Scripts\python.exe -m ruff check app/ tests/
```

Raw output:

```text
All checks passed!
```

### JavaScript syntax

Commands:

```text
node --check frontend/static/js/dashboard.js
node --check frontend/static/js/api.js
node --check frontend/static/js/step1_config.js
```

Raw output: no stdout/stderr; all three commands exited with code 0.

### Diff whitespace check

Command:

```text
git diff --check
```

Raw output (exit code 0; notices only, no whitespace errors):

```text
warning: in the working copy of '.viepilot/phases/04-post-beta-polish/tasks/task-4.4.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step1_config.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/api.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/dashboard.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step1_config.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_dashboard_browser.py', LF will be replaced by CRLF the next time Git touches it
```

## PM Re-review (2026-09-16) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word,
matching this project's established review discipline.

**Diff review** — read the full `git diff` for all 4 touched files plus the new test
file; every change matches the approved plan exactly, nothing outside scope:
- `dashboard.js`: a single `STATUS_TO_STEP` lookup object replaces the old 2-case `if`,
  minimal and exactly as specified.
- `api.js`: `updateProject()` added, mirrors the existing `request()`/`PUT` pattern.
- `step1_config.js`: confirmed the load-error path (`catch` branch) never unhides
  `#config-form` — the exact requirement this task exists to satisfy — and confirmed
  `buildPayload()` now reads `speaker.tts_engine ?? "omnivoice"` etc. instead of
  hardcoding, so an edited draft's hidden TTS fields (engine/description/speed/pitch/
  volume) survive a save unchanged.
- `step1_config.html`: title/subtitle ids + a new `#status-banner` element only, no
  layout redesign, as promised.

**New test file** (`tests/test_step1_config_edit_browser.py`) review: unusually rigorous
for a first-pass Implementer test file — `test_draft_save_uses_one_put_preserves_id_and_refetches_update`
double-submits via `form.requestSubmit()` twice and asserts exactly 1 PUT / 0 POST plus
the exact hidden-TTS-field payload; `test_progressed_project_is_read_only` is
parametrized across all 4 non-draft statuses and asserts `0` enabled `input`/`select`/
`button` elements inside `#config-form`, not a spot check.

**PM independently re-ran every verification command** (not trusting the pasted
output): targeted 22/22 pass, regression set 25/25 pass, `ruff check` clean, all 3
`node --check` clean, `git diff --check` exit 0 — all matched the Implementer's report
exactly.

**PM's own independent script + screenshot** (mocked API routes directly, not reusing
the Implementer's test file), beyond what was asked:
- Locked mode for a `video_generated` project: banner text, prefilled (not blank)
  fields, `0` enabled inputs/selects/buttons confirmed via live DOM query, and a
  `force: true` click directly dispatched at a disabled genre chip confirmed the
  browser itself blocks it (`aria-pressed` unchanged) — not just Playwright's
  actionability convenience check. Screenshot confirms correct greyed-out styling
  throughout and that the pre-existing "Cancel" link (a plain `<a>`, not a `<button>`,
  so untouched by `lockForm()`) still works — the Implementer correctly left the one
  harmless navigation control functional while locking every real data control.
- Dashboard Continue for a `video_generated` project: confirmed live navigation to
  `/step5?project_id=...`, matching the approved mapping.

**Full suite, run independently**: 558 passed, 0 failed, 263.48s — faster than the
Implementer's own 1375s run (which hit the project's known Gemini-retry timing flake
3 times, all confirmed passing in isolation at 0.69s) — confirming that slow run was
system load, not a code issue, and this PM run shows zero flakes at all at normal
speed. Up from 555 (this task's suite baseline before Task 4.4 started).

**Zero real defects found on PM review this round.** Accepted as delivered — no
changes requested.

**This closes Task 4.4.** Both P0 bugs are fixed using only real, pre-existing backend
capability. Resuming Task 4.2 with sub-task 4.2d (Thumbnail Generator, `/step6`) next.
