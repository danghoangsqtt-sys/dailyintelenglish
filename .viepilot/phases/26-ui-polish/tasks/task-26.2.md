# Task 26.2: Brand tokens, typography and one shared top bar (doc-first card)

## Paths

- `frontend/static/css/style.css`
- `frontend/static/fonts/Montserrat-Variable.ttf` (new; the same SIL OFL file as the video
  renderer)
- `frontend/static/fonts/OFL.txt` (new)
- `frontend/pages/*.html` (the 11 headers)
- `scripts/ui_audit_screens.py` (the screenshot helper, new)

## File-Level Plan

1. **Tokens** in `style.css`:
   - `--brand-violet #7C3AED`, `--brand-cyan #22D3EE`, `--brand-gradient`;
   - the accent moves to the brand violet;
   - dark surfaces move to the indigo of the video intro (`#0B1026` / `#151339`);
   - `--font-display: Montserrat` for headings, buttons and the brand;
   - a focus ring.
2. **One top bar on every page:**

   ```html
   <a class="brand" href="/">
     <span class="brand-mark">DI</span>
     <span class="brand-word"><b>Daily Intel</b><small>English Studio</small></span>
   </a>
   ```

   - The page title or project name follows.
   - `<nav class="app-nav">` holds Dashboard · Characters · Music · Settings, with the current
     page marked `aria-current="page"`.
   - Each page's own actions stay (the dashboard "Character Library" link, step 5's link, the
     theme toggle).
   - "← Dashboard" ghost buttons are removed, since the nav replaces them.
   - The page-level `.topbar` / `.logo` CSS in step 1, Music and Settings is removed so the shared
     style applies.
3. **Components:**
   - the primary button gets the brand gradient;
   - cards get a softer border and elevation;
   - headings use Montserrat.

## Verification

- The full suite is green (behaviour unchanged).
- After screenshots on the same 44 views are compared with before.
