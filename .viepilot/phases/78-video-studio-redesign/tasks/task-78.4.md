# Task 78.4 — Page layout, verification and records

## Objective
Step 5 reads as one clear flow at desktop and phone widths, the changes are verified, and the project records say what is done and what is not.

## Paths
- `frontend/pages/step5_video.html`: section headers numbered 1–4 (Nhân vật & cảnh, Storyboard, Render, Xem trước, Shorts & TikTok), render options grouped in a card, narrow-width rules.
- `frontend/static/js/i18n_vi.js`: copy for renamed headers.
- `.viepilot/phases/78-video-studio-redesign/PHASE-STATE.md`, `SUMMARY.md`; `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`, `CHANGELOG.md`.

## File-Level Plan
- Keep ids and order of the existing controls; only headings, grouping and CSS change.
- Verify in the sandbox server (port 8030, `DIE_DATA_DIR=D:\DataAdmin\p78-sandbox-data`): 1440×900 and 390×844, light theme; screenshots as evidence.
- Run related pytest, renderer Vitest + typecheck, then the full pytest suite (background).
- Record results honestly (counts, failures if any); no push, no package.

## Verification
Full `pytest -q` (2137 + new tests); renderer `npx vitest run`, `npx tsc --noEmit`.

## Result
Done 2026-10-26. Sections numbered 1-5, render options card, narrower inspector / shorter timeline (still resizable), phone width collapses the workflow list (no page overflow at 390 px). Related suites 124 passed; full pytest 2143 passed in 24:35; renderer Vitest 184, tsc clean.
