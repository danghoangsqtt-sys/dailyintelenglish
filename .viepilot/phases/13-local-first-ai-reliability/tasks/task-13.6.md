# Task 13.6 — Settings, Health, and Step 2/3 Job UX

- **Status:** pending
- **Dependency:** 13.2–13.3
- **Controlling detail:** implementation plan §7 and §8, Task 13.6

## Objective

Expose validated non-secret AI settings and safe health; move Step 2/3 to durable jobs
with visible provider/fallback, polling recovery, cancellation, retry, and accessibility.

## Allowed files

Exactly the model/service/API/page/JS/CSS/test paths listed for 13.6 in the controlling
plan.

## UX/security contract

Resume active job on load; visible polling ~2s and hidden-window backoff; no duplicate
start; actionable safe errors; `aria-live`; keyboard Cancel/Retry; no key, full prompt,
filesystem path, remote interaction ID, or raw exception in API/DOM.

## Verification and exit

Desktop/narrow browser tests prove refresh/navigation recovery, duplicate prevention,
cancel/retry, fallback banner, terminal content reload, health-down nonfatal behavior,
and settings validation/redaction.
