# Task 13.8 — Automated Regression and Packaging Gate

- **Status:** in_progress
- **Dependency:** 13.2–13.7 (all done)
- **Controlling detail:** implementation plan §8, Task 13.8

## Objective

Close all state, concurrency, security, browser, health, and packaging gaps; prove the
ordinary suite needs no live provider and the packaged app boots without Ollama.

## Allowed files

Phase 13 tests, `tests/test_ai_logging.py`, `scripts/check_dependencies.py`, and packaging
files only when verified import/data changes require them.

## Pre-implementation findings (doc-first gate)

Audited every logger call site across the whole AI gateway/durable-job layer
(`app/services/ai/router.py`, `ollama_provider.py`, `gemini_provider.py`,
`ai_worker.py`, `ai_job_service.py`, `script_pipeline.py`, `learning_pipeline.py`)
before writing any test. Findings:

1. Only `app/services/ai/router.py` (4 call sites) and one line in
   `ai_worker.py` (`ai_worker_recovered_jobs count=%d`) log anything at all in
   this whole layer; `script_pipeline.py`/`learning_pipeline.py`/
   `ai_job_service.py` have zero direct `logger.*` calls today. Every existing
   router log line uses only safe fields (`provider`, `model`, `purpose`,
   `prompt_hash`, `latency_ms`, `tokens_used`, `attempt`, or an exception's
   `type(exc).__name__`) -- never `request.prompt`, never a provider's raw
   response text, never an API key. This is already correct by construction,
   not something this task needs to change.
2. Considered whether `ProviderInvalidResponseError`'s message (which embeds
   up to 200 chars of a provider's raw HTTP response body, in
   `gemini_provider.py`/`ollama_provider.py`, both outside this task's allowed
   files regardless) could leak user prompt content if that message is later
   logged or surfaced in an API error. In practice a malformed/error HTTP
   response body is the provider's own infrastructure error text (e.g. an
   error JSON or an HTML error page), not an echo of the submitted prompt --
   confirmed by reading every call site that constructs these messages. No
   fix needed, and none would be in scope here even if one were (those two
   provider files are not in 13.8's allowed list).
3. `tests/test_ai_logging.py` does not exist yet. Given finding #1, its job is
   to **lock down** the router's already-correct no-leakage behavior with a
   `caplog`-based regression test (broader than the existing single
   provider-level check, `test_ai_providers.py::
   test_ollama_provider_never_logs_prompt_body`, which only covers one
   provider's own log output, not the router's, not a retry/fallback
   sequence, and not response-text leakage) -- not to add new production
   logging, which would need files outside this task's allowed list.

## Verification and exit

Run ruff, targeted tests, full pytest, every JS syntax check, dependency check, clean
PyInstaller build, and fresh-dist launch without project `.env`, with Ollama absent and
present. Existing browser flakes require isolated and group reruns with evidence; no
failure is waived by label alone. Ensure Ollama/client/model is not bundled.
