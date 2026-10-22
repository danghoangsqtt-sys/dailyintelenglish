# PHASE-STATE — Phase 68: live preview on the Shorts batch page

- **Status:** implemented_verified_pending_owner_review 2026-10-22. Full pytest 2000 passed; Vitest 179 (10 new); tsc clean.
- **Browser check (sandbox, VI):** the preview column plays the chosen template with the typed topic or the selected idea; changing the template (Don't say / Say → Quiz) or the selected row updates it at once; it opens on a frame with content (2.2 s). Found: the interface translator translated the words inside the player ("Stop" → "Dừng") — the player is now `translate="no"`; the same fix applied to the Step 5 Solo/VOX preview player, which had the same problem since Phase 58.
- **Tasks:** 3/3.

| Task | Scope | Status |
|---|---|---|
| 68.1 | Sample builder + bundle | implemented_verified |
| 68.2 | Preview column on the page | implemented_verified |
| 68.3 | Verification | implemented_verified |

- **Layout amendment (owner 2026-10-22, "Điều chỉnh lại kích thước, bố cục"):** one 12-column form grid with fixed spans and 42 px controls, the tabs as a segmented control below the intro, card padding, a preview column that shrinks (270–340 px) before it stacks under 980 px. Checked at 1024, 1100 and 1600 px; full pytest 2000 passed.
