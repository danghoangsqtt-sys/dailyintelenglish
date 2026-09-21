# Task 14.7 — Local-Only Mode, Config-First

- **Status:** done (Amendment F applied; full suite 879 passed, 0 failed)
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** Amendment D (plan §12, commit `94f5e7b`); Gate B-2 (`docs/operations/phase14-gate-b2.md`)
- **Controlling detail:** plan §12 Task 14.7; ADR-001 amendment A2; brainstorm decisions D9–D12

## Objective

Make `local` the real default for both development and packaged builds, per the owner's
decision to drop Gemini (D9–D12): no API-key UI, no `gemini`/`hybrid` option exposed, the
app requires Ollama to *generate* (not to *start*), and every remaining "Gemini fallback"
UI string is gone. The Gemini provider, its settings plumbing, and its tests stay in the
codebase — dormant, not deleted — so `DIE_AI_ALLOW_CLOUD=true` plus config remains a real,
if unsupported, rollback path (ADR-001 A2).

## Measured problem (do not re-derive)

Gate B-2 (`docs/operations/phase14-gate-b2.md`): Gemini 0/5 (503 storms wider than the
14.1 backoff window; free-tier 20 requests/day exhausted by retries — `quotaId` contained
`PerDay`/`FreeTier`, `retryDelay` 21s). Local 3/5, but **zero infrastructure failures**,
every completed script passed every content check. The owner decided (D9–D12,
`docs/brainstorm/session-2026-09-21.md` §Addendum) to drop Gemini as a supported path
rather than debug cloud quota/billing, and ship local-only.

## Allowed files

`app/core/config.py`, `app/core/constants.py`, `.env.example`, `app/api/ai_jobs.py`
(health payload only), `app/services/settings_service.py`, `app/api/settings.py`,
`app/models/settings.py`, `frontend/pages/settings.html`,
`frontend/static/js/settings.js`, `frontend/static/js/api.js` (only if a call is
removed), `frontend/static/js/step2_script.js`, `frontend/static/js/step3_learning.js`
(only to replace the "using Gemini fallback" copy with Ollama-missing guidance),
`frontend/static/css/style.css`, `scripts/check_dependencies.py`,
`daily_intel_english_studio.spec` (only if imports/data change), `README.md`,
`CHANGELOG.md`, `tests/test_settings_service.py`, `tests/test_settings_api.py`,
`tests/test_ai_health_api.py`, `tests/test_ui_async_browser.py`,
`tests/test_script_jobs_browser.py`, `tests/test_learning_jobs_browser.py`,
`tests/test_ai_router.py` (default-mode assertions only), `tests/conftest.py` (only if
the default-mode change requires a fixture change), and — **Amendment E (PM, 2026-09-21,
plan commit `26dae03`, before any 14.7 code)** — `tests/test_thumbnail_service.py`,
`tests/test_youtube_service.py` (test-only, for action 7's two `FakeProvider` tests;
omitted from the original list by mistake) — and **Amendment F (PM, 2026-09-21, commit
`ff99679`, after diff `518dd0a`)** — `tests/test_ai_jobs_api.py` (test-only: fix the
stale `gemini_fallback_configured` assertion at line 162) and
`frontend/pages/step6_thumbnail.html` (copy-only: replace the "Pillow + Gemini text"
badge with a neutral label).

`docs/operations/local-ai.md` and `docs/api.md` are PM-owned — report what changed, PM
documents it.

**Amendment E also settles the two choices action 2/3 originally left open:**
(a) the Settings mode selector is **replaced by a read-only status line** — no dead
`gemini`/`hybrid` options shown; the settings API still accepts `local` and, behind
`DIE_AI_ALLOW_CLOUD=true`, `gemini`/`hybrid`. (b) the health payload **drops**
`gemini_fallback_configured` entirely and adds `cloud_enabled: false` — an always-false
field would be misleading. Every frontend reader of the old `gemini_fallback_configured`
field must be updated in the same commit as the API change (no stale reads left behind).

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. `AI_MODE` defaults to `"local"` in `app/core/config.py` and `.env.example`. Remove the
   stale, unused `DIE_AI_CLOUD_FALLBACK` line from `.env.example` — grep first to confirm
   nothing reads it before deleting.
2. Settings page: remove the Gemini API-key section and the `gemini`/`hybrid` options
   from the mode selector, **replacing the selector with a read-only status line**
   (Amendment E — no dead options shown). The settings *API* keeps accepting/storing the
   key (dormancy/rollback path), but the UI no longer exposes it. `set_ai_mode` (in
   `app/services/settings_service.py`) rejects `gemini`/`hybrid` unless the new
   `DIE_AI_ALLOW_CLOUD` env var (default `false`) is `true` — this is the **only** new
   switch; it exists so re-enabling cloud is always an explicit act, never an accident.
3. `GET /api/ai/health` reports `cloud_enabled: false` and **drops**
   `gemini_fallback_configured` entirely (Amendment E — an always-false field would be
   misleading). Every frontend reader of the old `gemini_fallback_configured` field is
   updated to the new field in the same commit — no stale read left behind.
4. Step 2 (`step2_script.js`) / Step 3 (`step3_learning.js`): when `/api/ai/health` says
   Ollama is unreachable or the model is missing, the generate button is disabled and the
   panel shows install/pull guidance naming the exact model tag and digest (copy from
   `docs/operations/local-ai.md` — read it first for the current tag/digest text; do not
   invent new wording). No "Gemini fallback" copy remains anywhere in the DOM.
5. `scripts/check_dependencies.py`: Ollama reachability and model presence become a hard
   requirement with a clear failure message. The Gemini key check becomes informational
   (a note, not a failure) or is removed — Coder's choice, record which.
6. `README.md` / `CHANGELOG.md`: state local-only plainly, document the Ollama
   prerequisite, and record the rollback note verbatim: "Gemini is dormant; re-enable via
   `DIE_AI_ALLOW_CLOUD=true`, `DIE_AI_MODE`, and a key — unsupported."
7. Thumbnail and YouTube generators already route through the shared AI gateway; in local
   mode they call Ollama like everything else. Add exactly one `FakeProvider` test each
   (thumbnail, YouTube) proving they run end-to-end under `AI_MODE=local` — this is a
   wiring/regression check only; real structured-output quality on Ollama for these two
   schemas is measured by the PM in Task 14.9 (one real thumbnail + one real YouTube
   package on the Gate B-3 winning project), not here.

## Explicitly forbidden

- Deleting the Gemini provider, its adapter, or its existing tests — dormant, not removed
  (ADR-001 A2: "remain in the codebase, dormant").
- Any new env var beyond `DIE_AI_ALLOW_CLOUD`.
- Changing `AI_TRANSIENT_MAX_ATTEMPTS`, backoff constants, or any Task 14.1–14.3 behavior
  — this task is UI/config/docs only, not router/pipeline logic (that is Task 14.8's
  narrow scope, not this one's).
- Touching a file outside the allowed list above, including any `docs/**` path other than
  what's explicitly PM-owned per this card.

## Verification (all must be in the diff)

1. `tests/test_settings_service.py` / `tests/test_settings_api.py`: `set_ai_mode` rejects
   `gemini`/`hybrid` when `DIE_AI_ALLOW_CLOUD` is unset/false; accepts them when it's
   `true`; default `AI_MODE` is `local`.
2. `tests/test_ai_health_api.py`: `cloud_enabled: false` present; `gemini_fallback_configured`
   no longer in the payload (grep confirms exactly 2 current references to update:
   `app/api/ai_jobs.py:119` and this test file's own assertion at line 47 — record the
   actual line numbers found at implementation time, these may drift); existing
   secret-absence assertions still pass.
3. `tests/test_ai_router.py`: default-mode assertion(s) updated only if the router's own
   default construction path changed (it should not need behavior changes, only whatever
   default-value assertions reference the old default).
4. Browser tests (`tests/test_ui_async_browser.py`, `tests/test_script_jobs_browser.py`,
   `tests/test_learning_jobs_browser.py`): mock `/api/ai/health` as Ollama-missing, assert
   the generate button is disabled and the install/pull guidance (tag + digest) renders;
   assert no Gemini-fallback copy in the DOM.
5. A case-insensitive grep for `"gemini fallback"` across `frontend/` returns nothing
   after the change (record the exact grep command and its empty output in this card).
6. One `FakeProvider`-backed thumbnail test and one `FakeProvider`-backed YouTube test,
   both running under `AI_MODE=local`.
7. `venv\Scripts\python.exe -m ruff check app tests scripts` clean; full suite green
   (record the exact pass count); JS syntax check (`node --check` on every edited `.js`
   file) clean.
8. Packaged smoke build starts with Ollama stopped and shows guidance instead of crashing
   (if this is practical to verify without a full packaging run, record how; if not,
   record why and what was verified instead — do not claim untested behavior as tested).

## Rollback

`DIE_AI_ALLOW_CLOUD=true` + `DIE_AI_MODE=hybrid` (or `gemini`) + a configured key restores
the Phase 13 hybrid/Gemini behavior without a code revert.

## Execution record (Coder fills in)

- Plan/decisions before code:
  - **`app/core/config.py`:** `AI_MODE: str = "local"` (was `"gemini"`); add
    `AI_ALLOW_CLOUD: bool = False` (env `DIE_AI_ALLOW_CLOUD` via the existing
    `DIE_` prefix, no new `SettingsConfigDict` wiring needed). Update the
    `AI_MODE` field comment to describe the new default and dormant-cloud
    story instead of the old "gemini is the packaged default" wording.
  - **`.env.example`:** `DIE_AI_MODE=gemini` → `DIE_AI_MODE=local`; delete the
    `DIE_AI_CLOUD_FALLBACK=true` line (confirmed zero references anywhere in
    `app/`, `tests/`, `scripts/`, `frontend/` via grep before deleting); add a
    comment above `DIE_AI_MODE` documenting `DIE_AI_ALLOW_CLOUD` as the gate
    for `gemini`/`hybrid`.
  - **`app/services/settings_service.py` (`set_ai_mode`):** after the existing
    `AI_MODES` membership check, add: `if ai_mode != "local" and not
    config.settings.AI_ALLOW_CLOUD: raise ValidationError(...)` — a clear
    message naming `DIE_AI_ALLOW_CLOUD` and pointing at ADR-001 A2. `local`
    itself is never gated (always allowed, it's the only supported mode).
  - **`app/api/ai_jobs.py` (health payload only):** drop
    `"gemini_fallback_configured": bool(settings.GEMINI_API_KEY)`, add
    `"cloud_enabled": settings.AI_ALLOW_CLOUD` (Amendment E: report the real
    switch value, not a hardcoded `False` — `AI_ALLOW_CLOUD` already **is**
    the true cloud-enabled state, so this is both more honest than a literal
    `False` and simpler than computing something separate).
  - **`frontend/pages/settings.html`:** remove the entire "Gemini API Key"
    `<section>` (heading, hint, status div, input, toggle-visibility button,
    save/clear buttons, message div) and its inline styles that become
    unused (`.key-input-row`, the password/text input rule, the
    toggle-visibility affordance — kept only if still referenced by the
    remaining markup, checked at implementation time). Replace the "AI
    Provider Mode" section's `<select>` + hint (which described
    switching between gemini/local/hybrid) with a short static paragraph
    ("This app runs entirely on your local Ollama model — no cloud API key
    needed.") plus the existing `#ai-mode-status` read-only div (kept,
    still shows the live `ai_mode`/`ai_mode_source`). Page heading `<p>`
    updated to match (no longer "Configure the Gemini API key...").
  - **`frontend/static/js/settings.js`:** rewritten down to just
    `loadStatus()`/`renderAiModeStatus()` reading `Api.getSettings()` into
    `#ai-mode-status` — no `Api.updateGeminiApiKey`/`clearGeminiApiKey`/
    `updateAiMode` calls left (those UI affordances are gone), no
    `toggleVisibilityBtn`/`saveBtn`/`clearBtn`/`aiModeSaveBtn` event
    listeners (the elements themselves are gone from the HTML).
  - **`frontend/static/js/api.js`:** remove the now-unused
    `updateGeminiApiKey`/`clearGeminiApiKey`/`updateAiMode` wrapper functions
    (grep confirmed `settings.js` was their only caller before this task;
    after the rewrite above, nothing calls them) — dead code, not kept
    "just in case" (the settings *API routes* stay live for the dormant
    rollback path; only the *frontend wrapper* that called them is unused).
    `Api.getSettings` and `Api.getAiHealth` (already defined, previously
    uncalled by any frontend file) both stay/are newly used.
  - **`frontend/static/js/step2_script.js` / `step3_learning.js`:** two
    changes each:
    1. Remove the `fallbackNote` (`job.fallback_used ? " · using Gemini
       fallback" : ""`) from the job-status renderer — dead in local-only
       mode (`fallback_used` can't become true without cloud enabled) and
       the last "Gemini fallback" string in either file.
    2. **New** `checkOllamaHealthAndGate()`, called once from `init()`
       alongside the existing setup calls: calls `Api.getAiHealth()`
       (already defined, previously unused by the frontend), and if
       `!ollama_reachable || !model_present`, disables `#generate-btn` and
       injects a guidance message into `#generate-panel` (an *existing*
       container both pages already have — see below for why no `.html`
       edit is needed) naming the live `model`/`model_digest` from the
       health response itself (never a hardcoded tag/digest, so it can't
       drift from `docs/operations/local-ai.md`) and, when Ollama itself is
       unreachable (not just the model), a link to ollama.com. If healthy,
       removes any previously-injected guidance and leaves the button as
       other logic already controls it. A health-check failure (network
       error hitting the app's own `/api/ai/health`) is swallowed, not
       surfaced as a blocking error — the page must still be usable if this
       one auxiliary check fails.
    - **Why no `frontend/pages/step2_script.html` / `step3_learning.html`
      edit is needed (neither file is in this task's allowed list):** both
      pages already have a `#generate-panel` container element (holding the
      existing `<p>` + `#generate-btn`) that `checkOllamaHealthAndGate()`
      can `insertBefore`/`.remove()` a dynamically-created guidance `<div>`
      into via plain DOM APIs — confirmed by reading both HTML files before
      writing any code. If no such container existed, this would have been
      a stop-and-ask-the-PM situation (a required file outside the allowed
      list); it does exist, so it isn't.
  - **`frontend/static/css/style.css`:** add one small rule for the new
    guidance message element if the existing `.message`/`.message-error`
    classes (already used elsewhere, e.g. `settings.js`) aren't a good
    enough visual fit once seen rendered — decided at implementation time,
    not assumed here; reusing an existing class needs no CSS change at all.
  - **`scripts/check_dependencies.py`:** add `check_ollama()` (sync `httpx`
    client — `httpx` is already a project dependency, used elsewhere, e.g.
    `scripts/run_ai_operational_trial.py`): GETs `{OLLAMA_BASE_URL}/api/version`
    then `/api/tags`, checks `settings.OLLAMA_MODEL` is present among the
    tags (mirrors `app/api/ai_jobs.py`'s own `/api/ai/health` logic, kept
    independent rather than imported, matching this script's existing
    "checks the same source of truth, not a shared helper" style for
    `check_ffmpeg`). Added to the **required** checks list (`all_passed`
    fails without it). `check_env_file` (the Gemini key check) moves to a
    separate **informational** checks list, printed with a `YELLOW` status
    label instead of `RED`, never affecting `all_passed` — informational
    per action 5's explicit "or is removed" choice (kept, not removed, since
    it's still useful for anyone actually using the dormant rollback path).
    `check_gpu`/`check_omnivoice_model` stay exactly as they are now
    (required) — out of this task's scope, not mentioned by plan §12.
  - **`daily_intel_english_studio.spec`:** read first; only touched if the
    `httpx` import added to `check_dependencies.py` isn't already covered by
    PyInstaller's automatic dependency discovery or an existing hidden-import
    entry (likely already covered, since `httpx` is already imported
    elsewhere in the packaged app itself, e.g. every AI provider adapter) --
    verified at implementation time, not assumed.
  - **`README.md` / `CHANGELOG.md`:** update only the forward-looking
    sections (Requirements, Installation/env-setup steps, the packaged-app
    paragraph about reading the Gemini key from Settings, Tech Stack's AI/
    Thumbnail lines) to state local-only plainly and add the rollback
    sentence verbatim from plan §12 action 6. Historical Phase/Task rows
    (e.g. "Task 1.4 ... Gemini API ... Shipped") are **not** rewritten —
    they correctly describe what shipped at the time and rewriting them to
    pretend otherwise would falsify the project's own history. `CHANGELOG.md`
    gets one new dated entry for this task, appended, not editing old ones.
  - **Test-file plan:**
    - `tests/test_settings_service.py` / `tests/test_settings_api.py`:
      existing tests that switch to `hybrid`/`gemini` and expect success
      (e.g. `test_settings_service.py:122`, `test_settings_api.py:92`) get
      `monkeypatch.setattr(config.settings, "AI_ALLOW_CLOUD", True)` added
      (the mechanism under test there is "does a mode change take effect
      live", not "is cloud gated" — unrelated to this task's own new gate,
      so the fix is to allow it explicitly, not to change what they assert).
      New tests added: `set_ai_mode`/`PUT .../ai-mode` reject `hybrid`/
      `gemini` when `AI_ALLOW_CLOUD` is unset (default `False`); accept
      `local` unconditionally regardless of the flag.
    - `tests/test_ai_health_api.py`: `test_health_reflects_an_ai_mode_change_without_restart`
      gets the same `AI_ALLOW_CLOUD=True` monkeypatch (same reasoning).
      `test_health_response_has_no_extra_undeclared_fields`'s `expected_keys`
      set: `gemini_fallback_configured` → `cloud_enabled`. New test:
      `cloud_enabled` reflects `AI_ALLOW_CLOUD` (`False` by default, `True`
      when the env var is set).
    - `tests/test_ai_router.py` / `tests/conftest.py`: grepped for `AI_MODE`
      first — neither file actually asserts against the config *default*
      value (the router test's only `AI_MODE` mention is prose in a
      docstring; conftest has none at all) — **no change expected**; will
      re-check once the default flips, but currently no edit is anticipated
      for either file.
    - `tests/test_thumbnail_service.py` / `tests/test_youtube_service.py`
      (Amendment E): one new `FakeProvider`-backed test each, asserting the
      existing generator function runs to completion under
      `AIMode.LOCAL` — a thin wiring check (both already accept an injected
      router in their existing tests, per the same pattern Task 14.2/14.3
      used for script/learning), not new functional coverage of Ollama's
      real output quality (that's Task 14.9's job).
- Commands and results:
  - `venv\Scripts\python.exe -m ruff check app tests scripts` → All checks passed.
  - `node --check` on every edited `.js` file (`settings.js`, `api.js`,
    `step2_script.js`, `step3_learning.js`) → clean.
  - `venv\Scripts\python.exe scripts\check_dependencies.py` → all GREEN on this
    machine, including the new `Ollama + model` check (`qwen3.5:9b present
    (digest 6488c96fa5fa)`), `.env / GEMINI_API_KEY` now printed as an
    informational `[GREEN]` line (not counted toward pass/fail).
  - `venv\Scripts\python.exe -m pytest tests/test_settings_service.py
    tests/test_settings_api.py tests/test_ai_health_api.py
    tests/test_thumbnail_service.py tests/test_youtube_service.py
    tests/test_script_jobs_browser.py tests/test_learning_jobs_browser.py -q`
    → all green individually while iterating.
  - `venv\Scripts\python.exe -m pytest -q` (full suite) → **877 passed, 1
    failed** — the one failure is `tests/test_ai_jobs_api.py::
    test_ai_health_never_exposes_the_gemini_key` (`KeyError:
    'gemini_fallback_configured'`), a file **outside this task's allowed
    list**. See Deviations below — not fixed here per the doc-first
    "stop and ask the PM" rule.
  - `grep -rin "gemini fallback" frontend/` → no matches (exit 1).
  - `grep -rin "gemini" frontend/` (broader sweep, not the literal
    verification wording but done as due diligence) → one hit outside this
    task's scope: see Deviations.
- Deviations:
  - **BLOCKED on one file outside the allowed list — stop condition per plan
    §12/task-14.7.md's own instruction, mirroring the pattern already used
    for Tasks 14.1/14.2/14.4a.** `tests/test_ai_jobs_api.py:162` (not in
    this task's allowed-files list) asserts
    `data["gemini_fallback_configured"] is True` inside
    `test_ai_health_never_exposes_the_gemini_key` — a direct, mechanical
    consequence of Amendment E's explicit instruction to drop
    `gemini_fallback_configured` from the health payload (confirmed: grep
    before starting code found only 2 references, `app/api/ai_jobs.py` and
    `tests/test_ai_health_api.py`, both already fixed; this third reference
    was missed by that earlier grep because it's in a file this task never
    listed as allowed, so it wasn't in the search scope considered "this
    task's files"). Fix is mechanical and small: change the assertion to
    check `cloud_enabled` (the field's replacement) instead, matching
    exactly what `tests/test_ai_health_api.py`'s own
    `test_health_response_has_no_extra_undeclared_fields` already does.
    Requesting PM add `tests/test_ai_jobs_api.py` to this task's allowed
    files (test-only, this one assertion).
  - **Separate, smaller finding, not fixed (also outside the allowed
    list):** `frontend/pages/step6_thumbnail.html:257` has a badge reading
    "Pillow + Gemini text" — stale now that thumbnail generation defaults to
    Ollama. Not "Gemini fallback" copy (the task's literal verification
    target, confirmed clean), and `step6_thumbnail.html` / its JS are not in
    this task's allowed list, so not touched. Flagging for the PM to decide
    whether it's in scope for this task (a one-line amendment) or a
    follow-up.
  - `daily_intel_english_studio.spec`: read, no change needed —
    `scripts/check_dependencies.py` (where the new `httpx` usage lives) is
    not bundled into the packaged app at all (confirmed: no reference to it
    anywhere in the spec or `app/main.py`'s startup path), and `httpx` is
    already a normal dependency of the packaged app itself (every AI
    provider adapter uses it) — nothing to add.
  - `tests/test_ai_router.py` / `tests/conftest.py`: confirmed via grep
    (done before writing any code) that neither file asserts against the
    config *default* `AI_MODE` value — no edit made, matching the plan.
  - `tests/test_youtube_service.py`: Amendment E asked for one new
    `FakeProvider` test proving local-mode wiring, but
    `test_generate_package_local_mode_needs_no_gemini_key` (pre-existing,
    from Task 13.7) already does exactly this — `_gateway_router(AIMode.LOCAL,
    ...)` end-to-end. Rather than add a near-duplicate test to satisfy the
    letter of the instruction, this is recorded here as already-satisfied;
    only `tests/test_thumbnail_service.py` needed a genuinely new test
    (`test_generate_suggestions_runs_end_to_end_under_ai_mode_local`), since
    it had no equivalent.
  - Settings mode selector choice (Amendment E, already settled): the
    selector became a read-only status line, not hidden entirely — the
    existing `#ai-mode-status` div is kept as-is, only the interactive
    `<select>`/save button and their handlers were removed.
  - Otherwise no deviations from the plan recorded above.
  - **Amendment F (PM, 2026-09-21, commit `ff99679`) resolution:** PM reviewed
    diff `518dd0a`, confirmed both findings above and reproduced the 1
    failed / 877 passed result, amended the allowed-files list to add
    `tests/test_ai_jobs_api.py` (test-only) and
    `frontend/pages/step6_thumbnail.html` (copy-only), and additionally
    asked for a dedicated `test_generate_package_runs_end_to_end_under_ai_mode_local`
    in `tests/test_youtube_service.py` — named to match
    `test_thumbnail_service.py`'s new test — even though the pre-existing
    `test_generate_package_local_mode_needs_no_gemini_key` already covers the
    same scenario (documented above as already-satisfied before Amendment F).
    Added the extra test for naming parity across the four AI-calling
    services rather than re-litigating the point. All three items applied:
    `tests/test_ai_jobs_api.py:162` now asserts `data["cloud_enabled"] is
    False`; `step6_thumbnail.html`'s badge now reads "Pillow + local AI
    text"; `test_youtube_service.py` gained the new test. `ruff check` on
    both edited `.py` files clean;
    `pytest tests/test_ai_jobs_api.py tests/test_youtube_service.py -q` →
    **42 passed**. Full suite re-run after all three fixes:
    `venv\Scripts\python.exe -m pytest -q` → **879 passed, 0 failed** (364.28s).
- Revert-and-confirm-failure evidence:
  - Temporarily replaced `set_ai_mode`'s cloud-gate condition with `if False
    and ai_mode != "local" and not config.settings.AI_ALLOW_CLOUD:` and
    re-ran
    `venv\Scripts\python.exe -m pytest tests/test_settings_service.py::test_set_ai_mode_rejects_gemini_without_allow_cloud tests/test_settings_api.py::test_put_ai_mode_rejects_gemini_without_allow_cloud -q`:
    **2 failed** (`Failed: DID NOT RAISE ValidationError`;
    `assert 200 == 422`). Restored the real condition and re-ran
    `tests/test_settings_service.py tests/test_settings_api.py`: **37
    passed**.
- Commit(s): `518dd0a` (implementation, blocked), plus this commit (Amendment F
  fix-up: test_ai_jobs_api.py, step6_thumbnail.html, test_youtube_service.py).
