# Phase 88 state

Status: implemented_verified and installed (2026-11-03). Installed (owner: "Xem xong, cài đi", 2026-11-03): Full 2.0.0 from 8dff263 (source_dirty false), package dist/2.0-phase88-20261103 (Full ZIP SHA256 de284e353f1d58d985cf80437476d438f4bf152b8228355773985738add762be), backup data/backups/desktop-20261103-144553-097; the running app reports commit 8dff263, 118 projects kept; VieNeu available; the easy-grammar Step 1 card, batch kind and silent preview are served. Not pushed. Owner: "tiếp tục thực hiện nội dung tiếp theo /vp-auto" after Phase 87 was pushed.
Task cards written and committed before code; self-implemented in this session.

| Task | Scope | Status |
|---|---|---|
| 88.1 | `grammar` template: data and script | done — lesson model, second-pass review (kept when it fails), beats vi/en with cumulative cards, narrator switched to VieNeu, Step 2 keeps the cards, batch kind; 7 tests |
| 88.2 | `GrammarScene` renderer | done — pill, title, stacking cards (formula chips, compare, table filling row by row, example marks, sticker, stamp over the rote formulas, lego, quiz countdown), karaoke; sample stills checked, cards enlarged after the first stills; vitest 202 |
| 88.3 | UI wiring | done — Step 1 card (1.5/2/2.5 min), Shorts batch kind + silent preview, channel plan, automatic, Step 2 (no editor review, cards kept), Step 5, Vietnamese copy; 3 browser tests, kind counts updated |
| 88.4 | Verify | done — runs v1–v4, 7 real-run problems fixed; v4: Câu bị động 69.4 s, Thì hiện tại hoàn thành 56.0 s; full pytest 2285 (+3 browser tests that fail only under render load and pass alone), vitest 203 |
