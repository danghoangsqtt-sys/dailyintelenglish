# Task 13.7 — Gemini Fallback and Compatibility Migration

- **Status:** pending
- **Dependency:** 13.2–13.6
- **Controlling detail:** implementation plan §8, Task 13.7

## Objective

Verify a stable Gemini identifier, provide exactly one visible bounded fallback, move
all four Gemini consumers onto the common transport policy, and preserve legacy response
contracts for one deprecated compatibility release.

## Allowed files

Exactly the provider/router/script/learning/thumbnail/YouTube/API/doc/test paths listed
for 13.7 in the controlling plan.

## Constraints

Remote-background Gemini is capability-probed, not assumed. Local mode never uses
cloud. Fallback transmits user content and may consume quota, so it is explicit in
settings/UI/job metadata. No preview model enters automatic routing.

## Verification and exit

Forced Ollama-down produces exactly one visible cloud fallback; disabled fallback is a
safe local-only error; retry deadline is bounded; all four consumers use the gateway;
legacy endpoint response shapes and tests remain green.
