# Phase 47: Phrase-aware caption pagination (BUG-041)

## Authorization and scope

2026-10-15: owner explicitly requests vp-evolve planning followed immediately by vp-auto implementation for the audited subtitle defect. This authorizes executing the bounded plan without another plan-confirmation round. Existing owner authorization for project GitHub updates continues; formal visual acceptance and the older B-25/B-26/B-27/B-28 gates are not inferred.

Single focused renderer fix, compatible with the existing linked-runtime Windows trial. No API/schema/audio/script changes, dependency additions, model requests, stable-version bump or release asset replacement. Current published version stays 1.4.0-rc.1; changes are tracked under Unreleased for the next trial candidate.

## Outcome

- Both 16:9 and 9:16 choose grammatical page boundaries instead of cutting blindly at capacity.
- Fitting idioms and multiword learning terms stay together; page tails are balanced under existing safe-area limits.
- Every original token and timestamp remains intact; segmentation is deterministic and computed outside the per-frame path.
- Actual Episode 3 boundary previews and regression results are retained for review.

## Tasks

| Task | Outcome |
|---|---|
| 47.1 | Implement pagination and learning-phrase wiring, verify both layouts, persist source and evidence documentation |

No new milestone or architecture service is needed. Pending Phase 46 owner gates remain pending.
