# Task 27.2: App shell: a collapsible left sidebar on every page

## Objective

Every page has a left sidebar (Canva / CapCut style) with the main places of the app, which collapses to an
icon rail and remembers its state. The old top-bar links are removed. Behaviour, ids and flows stay.

## Decisions (brainstorm D61, owner 2026-10-06)

- Collapsible left sidebar: Dashboard, Characters & scenes, Music, Settings.
- Steps 1-7 keep their own CapCut-like 3-panel frame; the sidebar is the app-level navigation around it.

## Facts found in the code and tests

- All 11 pages share one header: `header.topbar` = brand + `nav.app-nav` (4 links) + theme toggle (steps also
  add a project name). `#step-nav` sits right after `header.topbar` on step 1 and inside `#pane-sidebar`
  on steps 2-7 (`tests/test_step_nav_browser.py` pins both).
- `tests/test_visuals_library_browser.py:48` clicks `get_by_role("link", name="Character Library")` (strict
  mode: exactly one such link must exist on the page); other tests use `Go to Dashboard` and the
  Music Library link.
- The step pages build a full-height workspace with their own CSS (`.workspace`, resizable panes).

## Design (the lowest-risk way)

- The sidebar is a **fixed** element (`aside#app-sidebar.app-sidebar`) added to every page next to the
  header, and `body` reserves its width with `padding-left: var(--sidebar-w)`. Page structure, so every
  `#step-nav` anchor and workspace height rule, is untouched. Width: 232 px expanded, 64 px collapsed.
- Content: the brand (logo + wordmark) at the top (moved out of the top bar), four links with an icon each,
  the collapse button, and the build/version line at the bottom. Link names stay "Dashboard", "Character
  Library", "Music Library", "Settings" (the label is visually hidden when collapsed, the `aria-label`
  and `title` stay), so tests and screen readers keep one link of each name. `aria-current="page"` marks the
  current page (the same rule the top bar had).
- The top bar keeps: the page title/project name, the theme toggle, and on narrow screens a menu button.
- State: `localStorage["dbe.sidebar"] = "collapsed" | "expanded"` (wrapped in try/catch; default expanded
  above 1100 px, collapsed between 780 and 1100 px, a **drawer** below 780 px opened by the menu button, closed
  by Escape or a click outside).
- Icons are inline SVG (no network, no new dependency).

## Paths

- `frontend/static/js/app_sidebar.js` (new)
- `frontend/static/css/style.css`
- `frontend/pages/dashboard.html`
- `frontend/pages/characters.html`
- `frontend/pages/music_library.html`
- `frontend/pages/settings.html`
- `frontend/pages/step1_config.html`
- `frontend/pages/step2_script.html`
- `frontend/pages/step3_learning.html`
- `frontend/pages/step4_tts.html`
- `frontend/pages/step5_video.html`
- `frontend/pages/step6_thumbnail.html`
- `frontend/pages/step7_youtube.html`
- `tests/test_app_sidebar_browser.py` (new)
- `tests/test_brand_assets.py` (the header assertions move to the sidebar)

## File-Level Plan

1. **Markup (one block, 11 pages):** `aside.app-sidebar` with `nav[aria-label="Main"]`, the brand, 4 links,
   `button#sidebar-toggle[aria-expanded]`; the top bar loses `a.brand` and `nav.app-nav` and gains
   `button#sidebar-open` (narrow screens only). The 11 pages are edited by one script and verified by test.
2. **`app_sidebar.js`:** toggles `body.sidebar-collapsed`, persists the state, drawer open/close with focus
   handling (the first link is focused on open, the menu button on close), Escape and outside click.
3. **`style.css`:** the sidebar (deep green `#0f2a1a`, lime active item, white text, AA contrast tested), the
   body padding, the collapsed rail (icons only, tooltips from `title`), the drawer with a backdrop, the
   transition (disabled under `prefers-reduced-motion`).
4. **Tests:** `test_app_sidebar_browser.py` (Playwright): every page has exactly one sidebar and one link of
   each name; the current page is `aria-current`; the toggle collapses and a reload keeps it; at 700 px wide
   the drawer opens, closes on Escape, and the page has no horizontal scroll; `#step-nav` is still a sibling
   of `header.topbar` on step 1. Existing browser tests that touch the header run unchanged.

## Verification

- The new browser test and the existing navigation tests green, then the full suite (about 16 minutes).
- Screenshots (light/dark, expanded/collapsed, desktop/narrow) looked at by Claude.

## Out of scope

The grid libraries (27.3), the studio frame polish (27.4), and the video intro/outro (27.5).
