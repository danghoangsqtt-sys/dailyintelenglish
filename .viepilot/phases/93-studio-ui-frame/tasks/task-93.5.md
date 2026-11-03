# Task 93.5 — Channel

See [PLAN.md](../PLAN.md), D138–D142, and the look in `.viepilot/ui-direction/session-2026-11-03-alt/e/`.

## Design (written before code)

- `channel.html` gets tabs: Publishing calendar (the week as Short / long-video lanes from the schedule API, states as
  colours), Series (the channel plan content), Automation (the `automation.html` content, moved with its IDs and
  script); `#auto` and `#series` open their tab.

## Paths

`frontend/pages/channel.html`, `frontend/static/js/channel.js`, `frontend/static/js/automation.js`, `frontend/pages/automation.html`

## Verification

Channel and automation browser tests pass on the tabs.
