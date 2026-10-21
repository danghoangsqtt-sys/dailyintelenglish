# Task 56.2 — Channel page flow

Status: planned 2026-10-21.

## Paths
- frontend/pages/channel.html, frontend/static/js/channel.js
- tests/test_channel_browser.py

## File-Level Plan
A three-step stepper (1 Plan with AI · 2 Topics & series · 3 Publishing dates) with done/current state from the data, and a "Next:" line naming the one thing to do (describe the channel; choose characters for N series; plan the dates; create the next series' projects). The plan form shows "What should the channel cover?", levels and the two characters; audience and the three numbers go under "More options". Topics and series become collapsible cards; a series summary shows level, mode, cast (or "choose characters"), episodes and projects created. All existing actions, ids and API calls stay.

## Tests
Browser: an empty channel shows step 1 current and the start hint; after a map is applied step 2 is current and names the series without cast; existing channel tests still pass.
