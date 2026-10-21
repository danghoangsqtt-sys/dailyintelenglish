# PLAN — Phase 56: Guided start, Channel flow, Activity Library (ENH-038)

Status: execution_authorized 2026-10-21 — owner chose the four designs (Dashboard "Start here", step bar, Activity Library shelves + tabs, delete all channel plans keeping projects). The plan data reset is already done with a backup (see ENH-038).

| Task | Scope | Depends on |
|---|---|---|
| [56.1](tasks/task-56.1.md) | Sidebar "Activity Library" → `/activities` (alias `/shots` kept); Activity Library page: tabs, shelves, review chips | — |
| [56.2](tasks/task-56.2.md) | Channel page as a three-step flow with a "Next" line; plan form basics first, numbers under "More options"; collapsible topics/series with a status summary | — |
| [56.3](tasks/task-56.3.md) | Dashboard "Start here": `start` block in the channel dashboard API + three cards + the 7-step path | — |
| [56.4](tasks/task-56.4.md) | Step bar: `GET /api/projects/{id}/progress`; `step_guide.js` renders a sticky bar on Steps 1–7 | 56.3 (shared step logic) |
| [56.5](tasks/task-56.5.md) | Verification: full pytest + renderer tests, screenshots both themes | all |

One session, sequential. No version bump; CHANGELOG `[Unreleased]`. Desktop rebuild only if the owner asks.

Out of bounds: the Solo files being finished by Phase 55 (`backend/library/explainer_*.py`, `renderer/src/Solo*.tsx`, `frontend/static/js/explainer_editor.js`).

Risks: the sidebar markup is copied in all 13 pages (mechanical rename, covered by the sidebar browser test). Activity Library tests use `#activity-filter-state` / `#activity-grid`; ids stay, the scope select becomes shelf buttons and the tests follow.
