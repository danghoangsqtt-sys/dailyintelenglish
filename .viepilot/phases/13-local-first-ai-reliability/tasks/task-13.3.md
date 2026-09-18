# Task 13.3 — Shared Transactions and Durable AI Jobs

- **Status:** pending
- **Dependency:** 13.2
- **Controlling detail:** implementation plan §5 and §8, Task 13.3

## Objective

Add the forward-only job/checkpoint schema, move the global transaction lock to the DB
layer, and implement atomic claim, lease, monotonic state/progress, cancellation,
recovery, stale checks, and lifespan-safe worker operation.

## Allowed files

Exactly the backend/router/test paths listed for 13.3 in the controlling plan. All
routers and tests that import transaction helpers must move together; no partial dual
lock implementation is allowed.

## Critical invariants

One active job/project/operation; conditional claim; no lock during provider wait,
backoff, TTS, or ffmpeg; final content save and `complete` transition in one transaction;
hash mismatch becomes `stale`; cancel/result race discards late output; recovery count
is bounded; project deletion creates no orphan/error traceback.

## Verification and exit

Fresh and real-DB-copy migration tests, double apply, counts unchanged, partial unique
index concurrency, transition matrix, crash/commit race, cancel, checkpoint recovery,
graceful shutdown, cascade, stale edits, and unrelated-project access all pass.
