# Phase 27 — Rebrand to Daily Beyond English and a Canva/CapCut-style layout (ENH-018)

**Status:** planned 2026-10-06 from `docs/brainstorm/session-2026-10-06.md` (D57, D60, D61, D62).
**Prototype:** `.viepilot/ui-direction/session-2026-10-06/index.html` (screenshots in
`docs/operations/ui-audit/proto-*.png`).

## 0. Principles

- Look and layout only. Element ids, roles, labels and flows stay, so the tests keep guarding behaviour.
- The owner's logo, name and palette are used as given: green `#3a9d3f` → lime `#9bd13c`, yellow
  `#ffd60a`, white, red `#e5322d` for calls to action, navy `#151a5c` for titles on light backgrounds.
- Light content area with a deep-green sidebar (the prototype). A dark mode stays available.

## 1. Tasks

| Task | What | Accept when |
|---|---|---|
| 27.1 | **Brand pack:** copy the logo into `frontend/static/` (PNG + a small WebP and the favicon), brand tokens (green/yellow palette) in `style.css`, name "Daily Beyond English" in titles, the header and package metadata; update the YouTube prompts (tagline, name) and the `Welcome to …` greeting | every page shows the new name and logo; tests green |
| 27.2 | **App shell:** a collapsible left sidebar on every page (Projects, Studio, Characters & scenes, Music, Settings), remembered per browser; the top bar keeps the page title, search and the primary action. The old top-bar nav is removed | the sidebar works at desktop and narrow width; tests green |
| 27.3 | **Libraries:** merge the Character and Scene libraries into one page with tabs, a large image grid, filters, search and a right-hand detail panel (status, use, outfit, duplicate, lock); the Music Library becomes the same grid + detail pattern (waveform, mood, pace, licence) | the owner can find and use a character, a scene and a track from the grids; tests green |
| 27.4 | **Studio steps 1–7:** one consistent 3-panel frame (media/steps left, preview centre, properties right, timeline below) and the sidebar | all steps share the frame; tests green |
| 27.5 | **Video intro/outro** with the new logo, name and palette; farewell adds "New videos every Wed & Sat" if the owner agrees | a real render passes the same length/level checks as Phase 25 |
| 27.6 | **Gate B-19:** the owner reviews the pages and one rendered episode | owner PASS |

## 2. Risks

- Browser tests pin page structure. Each task runs the affected tests and keeps their anchors (for
  example "a link named Character Library", `#step-nav` placement on step 1); anchors move deliberately and
  the tests are updated in the same task when a layout decision requires it.
- The Character and Scene pages merge: URLs `/characters` stays and shows both tabs.
