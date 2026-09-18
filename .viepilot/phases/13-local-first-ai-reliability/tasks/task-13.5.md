# Task 13.5 — Grounded Learning Pipeline

- **Status:** pending
- **Dependency:** 13.2–13.4
- **Controlling detail:** implementation plan §6 and §8, Task 13.5

## Objective

Generate from the persisted final-script hash, validate grounding/counts/answers,
repair failed items once, and atomically publish only if the script is still current.

## Allowed files

Only prompt, service, worker, constants, fixture, and test paths listed for 13.5 in the
controlling plan.

## Constraints

Expressions and quoted examples normalize back to the transcript; MCQ answer belongs
to options; open-ended contract remains valid; duplicates and count violations fail.
IPA, Vietnamese meaning, and grammar correctness require named human review and are not
misrepresented as dictionary-verified.

## Verification and exit

Five fixture packs pass deterministic checks; targeted failure repairs once; script edit
causes `stale`; failed/cancelled generation leaves the prior learning pack unchanged.
