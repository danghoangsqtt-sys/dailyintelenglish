# Task 93.1 — Tokens and fonts

See [PLAN.md](../PLAN.md), D138–D142, and the look in `.viepilot/ui-direction/session-2026-11-03-alt/e/`.

## Design (written before code)

- `frontend/static/css/tokens.css` (new, loaded first on every page): direction E's tokens (light on `:root`, dark on
  `[data-theme="dark"]`, the existing toggle contract): page, surface, sunk, line, ink 1-3, brand / brand-deep / brand-tint,
  sun (yellow), states (wait, err, run with tints), radii, Baloo 2 + Be Vietnam Pro `@font-face` from `/static/fonts`.
- The existing variables in `style.css` (`--bg`, `--bg-canvas`, `--surface*`, `--text*`, `--accent*`, `--border*`,
  `--success/warning/danger/info*`, `--font`, `--font-display`) are pointed at the new tokens, so every existing page
  takes the look without changing its markup; brand tokens kept (`--brand-green` ..., tested).
- Base components restyled from the tokens: buttons (one chunky primary), panels and cards, inputs, tabs, chips, state
  pills, focus ring, 16 px body, heading scale, reduced motion.
- Fonts: Baloo 2 (variable) and Be Vietnam Pro (400/500/600/700) TTF from the Google Fonts GitHub repository, with their
  OFL texts.

## Paths

`frontend/static/css/tokens.css`, `frontend/static/css/style.css`, `frontend/static/css/studio.css`, `frontend/static/fonts/*`, `frontend/pages/*.html` (one `<link>`)

## Verification

`tests/test_brand_assets.py` (AA contrast in both themes, still passes); a new test that every page loads tokens.css first and the fonts exist with their licences.
