# Phase 80 state

Status: implemented_verified (2026-10-27). Not pushed, not installed (owner decides).

| Task | Scope | Status |
|---|---|---|
| 80.1 | Short brand | done — is_short_video rule, no intro, 2 s end card, logo watermark; 11 new tests + Vitest; real render check in 80.5 |
| 80.2 | Short content | done — one-paragraph scripts split (7 lines vs 1), no welcome, card bullets drawn, visible scene, unimported photo → card in Automation; real Ep.2 Short 37.4 s for 35.4 s speech |
| 80.3 | Video types in the batch | done — backend + kind cards |
| 80.4 | Make now + results | done — maker, results panel (players, status, folder) |
| 80.5 | Verify | done — real batch Shorts via 'Make videos now': conversation 41.5 s, presenter 35.7 s (after 3 fixes), Vox waits for owner fact check by design; full pytest 2194 passed |
| 80.6 | Main save folder | done — app-wide main folder, auto Topic/Series/Ep folder for new projects (Step 1, Channel, Automation, Shorts), explicit apply-to-rest; panel on Settings/Channel/Automation; 4 new tests |
| 80.7 | Shorts batch page redesign | done — guided 4-step page, VI copy; batch browser + maker tests 6 passed; screens in docs/operations/phase80-screens |

Verification 2026-10-27: real Shorts made in a temp sandbox through the page API (create batch -> make now -> results). Fixes found by it: short lessons need no idiom; batch presenter Shorts self-review the generic fact flag; Automation arranges presenter layouts before approval. Owner report fixed alongside: a Solo plan naming an unoffered activity/scene is repaired instead of failing (commit 3249a2c). Full pytest 2193 passed + 1 stub fixed (2194). Temp sandbox and the leftover folders D:\DataAdmin\p78-sandbox-data, p78-sandbox-out, pip-cache removed (junctions unlinked first); 4 orphan test-run folders (audio/tts_cache of two Word-of-the-day projects, 26 Oct) removed from data/.
