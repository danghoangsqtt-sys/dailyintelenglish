# Task 26.1: UI audit (done 2026-10-06)

- **Method:** 44 screenshots (11 pages × light/dark × desktop 1440 / narrow 420) of the real data,
  taken with `scripts/ui_audit_screens.py`.
- **Contact sheets:** `docs/operations/ui-audit/before-light.png`, `before-dark.png`.

## Findings

1. **Three different top bars:**
   - Dashboard and steps 2–7 use a "D" square mark;
   - step 1, Music and Settings use a 🎙️ emoji logo with their own page CSS;
   - the navigation differs per page ("← Dashboard" ghost buttons, a lone ⚙️ icon on the
     dashboard).
2. **The app does not match the brand approved for the videos (Phase 25):** the DI violet → cyan
   mark and Montserrat.
3. **The dashboard project cards show a grey "Project preview" placeholder** even when the episode
   has shots and thumbnails, and the hero is plain.
4. **Music, Characters and Settings are a narrow centred column** with no shared navigation.
5. **Mixed language:** the dashboard hero is Vietnamese, everything else is English.
6. **Constraints from tests** (must keep):
   - the dashboard keeps a link named "Character Library";
   - step 5 has exactly one link named "Character Library";
   - on step 1, `#step-nav` sits right after `header.topbar` and before `main.main`.
