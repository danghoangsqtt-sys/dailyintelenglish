# Task 13.8 — Automated Regression and Packaging Gate

- **Status:** done
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

## Verification results (2026-09-20)

- New `tests/test_ai_logging.py` (7 tests): success/retry/hybrid-fallback/circuit-
  breaker-open/total-failure/auth-error paths through a real `AIRouter` (never a
  live network call) each assert a deliberately distinctive prompt marker,
  response marker, and fake API key never appear in `caplog`-captured log text;
  one positive test confirms the suite is actually observing
  `app.services.ai.router`'s real log records (not silently matching zero).
  All 7 pass.
- `venv\Scripts\python.exe -m ruff check app tests scripts` — clean.
- `Get-ChildItem frontend\static\js\*.js | node --check` (every file) — clean.
- `venv\Scripts\python.exe scripts\check_dependencies.py` — all 6 checks GREEN
  (Python 3.14.7, ffmpeg, RTX 3060 12288 MiB, Gemini key, OmniVoice model
  files, data dirs).
- `venv\Scripts\python.exe -m pytest -q` — **808/808 pass** (801 + 7 new), 0
  failures, 0 flakes (366.75s). No pre-existing browser flake occurred this
  run, so no isolated/group rerun was needed.
- `powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1` — clean
  build, exit 0. `dist\DailyIntelEnglishStudio\DailyIntelEnglishStudio.exe`
  produced (22 MB exe, 169 MB total dist -- matches Task 12.2's own confirmed
  size, i.e. the `torch`/`tensorflow`/etc. exclusion list is still effective
  and nothing Phase-13-specific bloated the build).
- **Ollama/model not bundled**: confirmed by reading
  `daily_intel_english_studio.spec` -- `Analysis` only stages `frontend/`,
  `prompts/`, and `app/db/migrations/` as data; nothing references an Ollama
  binary or model weights. Task 13.8 added no spec changes (none were needed).
- **Fresh-dist launch, no `.env`, Ollama present**: launched
  `DailyIntelEnglishStudio.exe` directly from `dist\DailyIntelEnglishStudio\`
  (confirmed no `.env` in that directory) on an isolated port
  (`DIE_APP_PORT=8010`, avoiding the existing dev server on 8000). `GET
  /health` returned 200 (`database: true`, `ffmpeg: true`, real GPU info).
  `GET /api/ai/health` returned `mode: "gemini"` (correct packaged default
  per ADR-001 point 6, since no `.env` sets `DIE_AI_MODE`),
  `ollama_reachable: true`, never exposing a key.
- **Fresh-dist launch, no `.env`, Ollama absent**: stopped both the Ollama
  tray watchdog (`ollama app.exe`, which auto-relaunches the server -- the
  first stop-only-the-server attempt was silently undone by this watchdog
  within seconds, a real timing lesson recorded here, not hidden) and the
  server itself, confirmed via a real `curl` to `127.0.0.1:11434` failing
  (connection refused). Restarted the exe fresh: `GET /health` still returned
  200 immediately (startup never blocks on Ollama); `GET /api/ai/health`
  correctly reported `ollama_reachable: false`, `model_present: false`,
  `model_digest: null`, `mode: "gemini"` still served safely (no crash, no
  exception leaked, ~2s probe timeout is short per the plan's "short
  timeouts, informational" requirement). This confirms the controlling plan's
  invariant "the application must still start when either is absent" for the
  actual packaged build, not just the dev server.
- Restored the environment afterward: stopped the test exe, restarted the
  real Ollama server (`ollama.exe serve`), reconfirmed `127.0.0.1:11434`
  answers again. The existing dev server on port 8000 was never touched.
  Stray local test artifacts (`dist_exe.pid`, `dist_exe_std{out,err}*.log`)
  deleted; `dist/` itself is already gitignored and was left on disk,
  matching Task 12.2's own precedent.
- `git diff --check` — clean.
