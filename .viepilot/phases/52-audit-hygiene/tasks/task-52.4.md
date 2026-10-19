# Task 52.4 — BUG-047 HANDOFF resume state

Status: planned 2026-10-19.

## Objective

Make `.viepilot/HANDOFF.json` agree with TRACKER and the PHASE-STATE files so `/vp-resume` resumes the right task.

## Paths

- .viepilot/HANDOFF.json
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/phases/52-audit-hygiene/PHASE-STATE.md
- .viepilot/phases/52-audit-hygiene/tasks/task-52.*.md
- CHANGELOG.md
- .viepilot/requests/BUG-047.md

## File-Level Plan

- `feature_plan.note`: replace the stale "Next 49.6" text with the current checkpoint (49.1–49.9 verified, 49.10 owner real-art/V49 pending).
- `phases`: add entries 47, 48, 49, 50 and 52 with status and PHASE-STATE path, matching the shape of existing entries.
- Record (in HANDOFF and TRACKER) that Phases 46, 47, 50, 51 intentionally have no `-complete` tag until owner acceptance; create no tags.
- Close Phase 52: PHASE-STATE, task results, TRACKER/ROADMAP status, CHANGELOG `[Unreleased]` "Fixed" entry, request statuses.

## Verification

HANDOFF parses as JSON; `next_task` and note agree; every phase directory 47–52 has a `phases` entry; Tier 1 audit re-run shows no drift.
