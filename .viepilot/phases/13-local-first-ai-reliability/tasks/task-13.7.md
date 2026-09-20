# Task 13.7 — Gemini Fallback and Compatibility Migration

- **Status:** in_progress
- **Dependency:** 13.2–13.6 (all done)
- **Controlling detail:** implementation plan §8, Task 13.7

## Objective

Verify a stable Gemini identifier, provide exactly one visible bounded fallback, move
all four Gemini consumers onto the common transport policy, and preserve legacy response
contracts for one deprecated compatibility release.

## Allowed files

Base list from the controlling plan:
`app/services/ai/gemini_provider.py`, `app/services/ai/router.py`,
`app/services/script_service.py`, `app/services/learning_service.py`,
`app/services/thumbnail_service.py`, `app/services/youtube_service.py`,
`app/api/projects.py`, `app/api/learning.py`, `docs/api.md`,
`tests/test_ai_router.py`, `tests/test_ai_providers.py`, `tests/test_script_api.py`,
`tests/test_learning_api.py`.

**Expanded during doc-first review (recorded here before any code, per the
controlling plan §8 preamble: "A newly discovered required file pauses that task
until the plan and allowed-file list are updated"):**

- `tests/test_script_service.py`, `tests/test_learning_service.py`,
  `tests/test_thumbnail_service.py`, `tests/test_youtube_service.py` — all four
  currently unit-test each service's own duplicated `_call_gemini`/`_attempt_model`/
  `_generate_with_retry`/`GEMINI_MODEL_FALLBACKS` cascade in detail (confirmed by
  reading all four files in full). Migrating `generate_script`,
  `generate_learning_pack`, `generate_suggestions`, and the YouTube package generator
  onto `AIRouter` necessarily changes or removes that internal machinery, so these
  test files must be updated to test through the router (mirroring
  `regenerate_line`'s existing `router: AIRouter | None = None` injection pattern and
  `test_ai_router.py`'s `FakeProvider` style) instead of monkeypatching the deleted
  internals. This is a test-only expansion — no new production file is touched beyond
  the original list, and no test outside these four files' own Gemini-transport tests
  is altered. Not escalated to the user: the controlling plan's own §4 already states
  "Thumbnail text and YouTube metadata also use gateway capabilities after 13.7", so
  this is the plan's documented architecture, not a new one — only the task card's
  test-file list was incomplete, matching the same class of gap self-resolved in
  13.5/13.6 (see PHASE-STATE evidence log).

## Constraints

Remote-background Gemini is capability-probed, not assumed. Local mode never uses
cloud. Fallback transmits user content and may consume quota, so it is explicit in
settings/UI/job metadata. No preview model enters automatic routing.

## Pre-implementation findings (doc-first gate)

1. **Live Gemini model re-verification (2026-09-20):** a real `models.list` call
   against the configured key, plus `models/gemini-3.8-flash`'s own metadata (no
   `-preview` suffix, `supportedGenerationMethods` includes `generateContent`) and
   the official `ai.google.dev/gemini-api/docs/models` page, confirm `gemini-3.8-flash`
   is still Google's current stable Flash model today, one day after Task 13.2's own
   live verification. `GEMINI_MODEL` (`app/core/constants.py`, unchanged file) stays
   pinned to it — no constant change needed.
2. **Gemini remote-background capability — real but out of this task's scope.** Live
   docs (`ai.google.dev/gemini-api/docs/background-execution`) confirm a real
   Interactions API (`/v1beta/interactions`, `"background": true`) exists and lists
   `gemini-3.8-flash` as supported, distinct from `generateContent`. `ADR-001` point 7
   and controlling-plan §4 mark remote-background as an *optional* capability: "the
   worker may make an async foreground call if remote-background capability is not
   available for the account/model." Wiring actual background submission/poll/resume
   requires persisting and reading `ai_generation_jobs.remote_interaction_id` (column
   already added by Task 13.3's migration, still unused anywhere) from
   `app/services/ai_worker.py`/`app/services/ai_job_service.py` — neither file is in
   13.7's allowed list, and adding it now would be an architecture change outside
   allowed files (the real control point the user asked to stop for). Decision: keep
   the durable worker's existing synchronous foreground `AIRouter.generate()` call
   (already correct and ADR-compliant, since foreground is explicitly valid whether or
   not background is available) and leave background-execution wiring for a future,
   separately-scoped task. Documented here, not silently dropped.
3. **Legacy `GEMINI_API_KEY` upfront guard is now mode-aware, not blanket.**
   `generate_script`/`generate_learning_pack`/`generate_suggestions`/the YouTube
   package generator each currently hard-require `settings.GEMINI_API_KEY` before
   calling Gemini directly. Once routed through `AIRouter`, that blanket check would
   incorrectly block `AI_MODE=local`/`hybrid` usage that needs no Gemini key at all.
   Each guard becomes `if AIMode(settings.AI_MODE) is AIMode.GEMINI and not
   settings.GEMINI_API_KEY: raise ...` — byte-identical behavior/error message for the
   packaged default (`AI_MODE=gemini`), correct new behavior for local/hybrid. This is
   an intentional, disclosed behavior change, not a response-shape change.
4. **Shared router factory.** `app/services/ai/router.py` (allowed) gains one
   `build_ai_router_from_settings()` function (Ollama+Gemini provider construction from
   `app.core.config.settings`, exactly `script_service.py`'s existing private
   `_build_ai_router()` body, relocated and shared). All four services import it
   instead of each hand-rolling — or duplicating — their own copy.
5. **Legacy multi-model cascade is deliberately not preserved.** ADR-001's own
   "Rejected alternatives" explicitly rejects "Multiple automatic fallback models" as
   unpredictable. `GEMINI_MODEL_FALLBACKS`-based retries inside these four services are
   removed in favor of the router's single-model, one-retry, one-fallback policy. The
   constant itself (`app/core/constants.py`, not an allowed file) is left in place,
   now unused by these four call sites — noted here as a known, out-of-scope cleanup
   item for a later docs/constants pass, not hidden.

## Implementation notes (file-level plan)

- `app/services/ai/router.py`: add `build_ai_router_from_settings() -> AIRouter`.
- `app/services/script_service.py`: `generate_script()` gains `router: AIRouter | None
  = None`, calls `build_ai_router_from_settings()` + `AIRouter.generate()` with
  `purpose="script_generate_full"` instead of `_generate_with_retry`; mode-aware key
  guard; delete `_call_gemini`/`_attempt_model`/`_generate_with_retry` and now-dead
  imports (`httpx`, `sleep`, `GEMINI_MAX_RETRIES`, `GEMINI_MODEL_FALLBACKS`,
  `GEMINI_RETRY_BASE_DELAY`, module-level `GEMINI_ENDPOINT`); `regenerate_line` switches
  its own `_build_ai_router()` call to the shared factory.
- `app/services/learning_service.py`: same migration for `generate_learning_pack()`
  (`purpose="learning_generate_full"`).
- `app/services/thumbnail_service.py`: same migration for `generate_suggestions()`
  (`purpose="thumbnail_suggestions"`).
- `app/services/youtube_service.py`: same migration for the package-generation
  function (`purpose="youtube_package"`).
- `app/api/projects.py`: `POST /{project_id}/script/generate` marked
  `deprecated=True` with a docstring note pointing at the durable-jobs API; comment
  updated from "Gemini call" to "provider gateway call". `regenerate_script_line` is
  untouched (line regen is not a durable-job operation).
- `app/api/learning.py`: `POST /generate` marked `deprecated=True` the same way.
- `docs/api.md`: regenerated via the existing `scripts/generate_api_docs.py` so the
  two deprecation flags flow through from the live OpenAPI schema (no hand-editing).
- Tests: rewrite the Gemini-transport-specific tests in the four service test files to
  inject a `FakeProvider`-backed `AIRouter` (mirroring `test_script_service.py`'s
  existing `regenerate_line` gateway tests); add `AI_MODE=local`/`hybrid` no-key-needed
  cases; extend `tests/test_ai_router.py`/`tests/test_ai_providers.py` only if a real
  gateway-level gap appears (not to duplicate router tests already there).

## Verification and exit

Forced Ollama-down produces exactly one visible cloud fallback; disabled fallback is a
safe local-only error; retry deadline is bounded; all four consumers use the gateway;
legacy endpoint response shapes and tests remain green; full suite/ruff clean.
