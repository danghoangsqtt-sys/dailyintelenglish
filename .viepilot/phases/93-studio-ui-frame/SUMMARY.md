# Phase 93 summary — the new studio look: frame and main areas (2026-11-04)

Owner: "Chạy Phase 93" with the defaults D138–D142. Built in the sandbox (`studio-p87`, port 8030, its own data folder);
not built, installed or pushed.

## What changed

- **Tokens and fonts (93.1):** the palette moved to direction E (tinted neutrals, one green accent `#18733e` / dark
  `#5cc98a`, amber / red / blue states, both themes, AA contrast kept), Baloo 2 headings and Be Vietnam Pro text
  bundled with their OFL texts (no font CDN), 16 px text, buttons with one chunky primary. `tokens.css` adds the `e-`
  components the new pages use.
- **One rail (93.2):** `app_sidebar.js` draws the rail on all 18 pages from one list — Create video, Today, Channel,
  Videos, Library, Settings — lights the area of the current page (old addresses light their new area), collapses to
  icons (remembered), shows the number of videos waiting, and becomes a tab bar at the bottom under 780 px.
- **Today (93.3):** `/` is the new Home — Lina's band (her half-body frames cut on the server from her library sprites by
  `GET /api/assistant/frames/{name}.webp`; she waves, then stands, breathes and blinks), the topic box that opens Create
  video with the topic, Waiting for you (the review board's waiting, needing-a-fix and changes-asked videos, then the
  channel's to-do actions), In progress (making / in progress, the video to continue with its 7-step strip, the next
  planned episode with "Create its project"), and This week (at most three items a day).
- **Create video (93.4):** `/create` — One video or Many Shorts at once, a Lina note, group chips and the Short / 16:9
  switch, the gallery by purpose with the Phase 92 clips playing on hover or focus; a card opens Step 1 with the kind
  (and Home's topic) chosen (`step1_prefill.js`).
- **Channel (93.5), Library (93.7), Create:** the pages of an area get tabs at the top (`area_tabs.js`): Publishing plan /
  Automation; Characters / Scenes and pictures / Music / Voices and brand; Templates / Many Shorts at once. Each page
  keeps its address, IDs and script (the plan's redirects were not needed).
- **Videos (93.6):** `/videos` is the former dashboard's project list, now laid out as table rows (filters, search, pages,
  actions unchanged), with a second view, By step: the production board and the channel roadmap.
- **Library (93.7):** `/library` lists the voices (local VieNeu and Edge, by language) and the brand.
- **Copy (93.8):** Vietnamese for every new label (98 texts, 8 patterns; existing translations kept).

Every cockpit feature is still there: stats on the Channel page, actions and the next planned episode on Home, the
production board and the roadmap on Videos, the calendar on Home and Channel.

## Verification

- New tests: `tests/test_studio_look.py` (tokens before the main stylesheet on every page, the fonts and licences, no
  font CDN), `tests/test_studio_pages_browser.py` (no sideways scroll at 375 px on 11 pages, both themes from the tokens,
  Baloo 2 headings, Home without an assistant character, Home's topic to Create to Step 1, the rail's focus ring, area
  tabs). Updated: the sidebar test (new links, areas, collapse, phone tab bar), the dashboard tests (now on `/videos`),
  the cockpit test (its parts on Home and Videos), the brand test (the brand drawn by the rail).
- Sandbox: Home, Create, Videos, Library, Channel, Automation in English and Vietnamese, light and dark, 1440 px and
  375 px.
- Full pytest: 2360 passed; 3 tests that looked for the old sidebar items or the grid on `/` were pointed at the new
  areas and pass.
- Design self-audit on the 10 criteria: see PHASE-STATE (Today 90, Create 89, Library 86, Videos 86; the step pages and
  the former pages 70–78 until Phase 94).
