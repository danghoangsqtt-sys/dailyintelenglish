# Phase 90 state

Status: implemented_verified (2026-11-03, sandbox; not built, installed or pushed). Owner: "Chạy Phase 90" with the default choices D128–D130. Task cards written and
committed before code; self-implemented in this session.

| Task | Scope | Status |
|---|---|---|
| 90.1 | Beats API | done — GET (cards + live preview props, silent with estimated timings until the audio matches), PUT cards (checked by kind, text and audio kept, video out of date), PUT one line's text (only its audio cleared), redraw one word picture; 5 tests |
| 90.2 | "Sửa trên video" editor | done — beat list, 9:16 preview player beside it (edits show at once), form per card kind (chips with colour role, table grid, add / move / remove cards), scene-wide header and shared-card edits, autosave, undo / redo, spoken line save, redraw picture; Bangers / Patrick Hand copied to the app fonts (the browser preview had no font); 2 browser tests |
| 90.3 | Only the changed lines' audio | done — "Tạo lại giọng (N)" synthesizes only lines whose voice no longer matches, then mixes; real run: 1 line + mix in 9 s; test |
| 90.4 | Verify | done — grammar edit (rule card + one spoken line) → voice 9 s + render ~52 s, both in the video; roots meaning edited once → all its beats; 4 problems found and fixed; 8 tests |
