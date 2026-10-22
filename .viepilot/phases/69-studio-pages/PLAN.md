# PLAN — Phase 69: the studio look for the Dashboard, Channel plan and Settings (ENH-051)

Status: execution_authorized 2026-10-22 — the owner asked for the upgrade.

| Task | Scope |
|---|---|
| 69.1 | Shared styles: `frontend/static/css/studio.css` — the studio bar (kicker, title, subtitle, bar buttons), number tiles, studio cards with headers, rails and day strips, in light and dark, loaded by the three pages |
| 69.2 | Dashboard: studio bar with the stats as tiles and the actions (Channel plan, Automation, Shorts batch, New project); Start here as three large cards with an icon; the 7-step rail; Next to publish / Today; the roadmap rail; the production board as coloured columns; the next two weeks as day columns (`dashboard_channel.js` groups the items by date, same `#cockpit-calendar` list); the project grid under a studio card header |
| 69.3 | Channel plan: studio bar (title, short explanation, counts as tiles), the steps as a rail, topic cards with a coloured header band and series cards with a mode badge and a cleaner control row, the calendar as week rows of day chips (`#calendar-list` keeps one item per episode) |
| 69.4 | Settings: studio bar, the left menu as tiles with a description, cards with icon headers, the provider status tiles |
| 69.5 | Verification: 1024 / 1440 / 1600 px, light and dark, EN and VI (new texts in `i18n_vi.js`); the existing browser tests keep passing (ids kept); full pytest + Vitest; before/after screenshots |

Kept: every id, data attribute, control and API; no backend change. No version bump; CHANGELOG `[Unreleased]`.
