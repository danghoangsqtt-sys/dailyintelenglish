# Task 13.4 — Checkpointed Script Pipeline

- **Status:** pending
- **Dependency:** 13.2–13.3
- **Controlling detail:** implementation plan §6 and §8, Task 13.4

## Objective

Generate scripts as outline plus validated 1–2 minute sections, checkpoint valid work,
repair only one failed section, merge with server-owned IDs, and publish atomically.

## Allowed files

Only prompt, service, worker, constants, fixture, and test paths listed for 13.4 in the
controlling plan.

## Hard checks

Valid schema; allowed speaker enum; non-empty text; correct section/input hash; per-
section ±15%; global ±10%; 35–65% word share; no exact duplicate line; repeated
normalized 8-gram ratio <1%; line IDs generated server-side. Topic/CEFR heuristics are
warnings plus human review, not unstable hard rejections.

## Verification and exit

5/8/10-minute fixtures, injected repair, fallback decision, interruption/resume,
cancel/stale race, and preservation of the prior valid script on failure all pass.
