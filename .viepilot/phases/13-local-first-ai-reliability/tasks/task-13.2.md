# Task 13.2 — Provider-Neutral AI Gateway

- **Status:** pending
- **Dependency:** 13.0; Gate A may run in parallel conceptually
- **Controlling detail:** implementation plan §8, Task 13.2

## Objective

Create a typed async provider contract, normalized safe errors, Ollama and Gemini
adapters, one retry/deadline/fallback policy, shared validation, and fake-provider seams.

## Allowed files

`app/services/ai/**`, `app/core/config.py`, `app/core/constants.py`,
`app/core/exceptions.py`, `requirements.txt`, `tests/test_ai_contracts.py`,
`tests/test_ai_providers.py`, `tests/test_ai_router.py`, `tests/test_ai_validation.py`.

## Constraints

No legacy service is switched before contract tests pass. Async client lifetime follows
app lifespan. Ollama URL is HTTP loopback without credentials. No nested retries, full
prompt logging, response dumping, or hard dependency on Gemini remote-background APIs.

## Verification and exit

Contract/error/timeout/cancel/429/5xx/malformed cases pass; auth/400 are non-retryable;
total attempts/deadline are bounded; logs exclude key and full prompt; ruff passes.
