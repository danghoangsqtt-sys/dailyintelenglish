# Task 13.8 — Automated Regression and Packaging Gate

- **Status:** pending
- **Dependency:** 13.2–13.7
- **Controlling detail:** implementation plan §8, Task 13.8

## Objective

Close all state, concurrency, security, browser, health, and packaging gaps; prove the
ordinary suite needs no live provider and the packaged app boots without Ollama.

## Allowed files

Phase 13 tests, `tests/test_ai_logging.py`, `scripts/check_dependencies.py`, and packaging
files only when verified import/data changes require them.

## Verification and exit

Run ruff, targeted tests, full pytest, every JS syntax check, dependency check, clean
PyInstaller build, and fresh-dist launch without project `.env`, with Ollama absent and
present. Existing browser flakes require isolated and group reruns with evidence; no
failure is waived by label alone. Ensure Ollama/client/model is not bundled.
