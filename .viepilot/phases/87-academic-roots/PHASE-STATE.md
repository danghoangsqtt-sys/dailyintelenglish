# Phase 87 state

Status: implemented_verified and installed (2026-11-03). Installed (owner: "Nghe xong, cài đi", 2026-11-03): Full 2.0.0 from b820d22 (source_dirty false), package dist/2.0-phase87-20261103 (Full ZIP SHA256 830f817db28ffd48eca5506847ca73203f1daf66e14d5541a7383f0f9d54147a), backup data/backups/desktop-20261103-110605-034; the running app reports commit b820d22 and the same data instance; VieNeu available with 25 voices; the word-roots template, batch kind and preview are served. Found before building: backend/content/data was not in the PyInstaller spec (fixed in b820d22). Not pushed. Plan committed before implementation; the owner said "Chạy Phase 87", self-implemented in this session.

| Task | Scope | Status |
|---|---|---|
| 87.1 | VieNeu engine (isolated worker) | done — persistent worker, Whisper word timings aligned in the app; real run on this machine: 3 lines, monotonic timings, 11 s first line (model load) then ~3 s; setup script fixed for Windows PowerShell 5.1 stderr, interrupted venvs and hub symlinks (ONNX Runtime refuses them) |
| 87.2 | `roots` template: data and script | done — word family schema, checked list (32 roots, 20 prefixes, 20 suffixes), beats vi/en, narrator switched to VieNeu for Vietnamese narration, Step 2 keeps the cards, batch rule |
| 87.3 | `RootsScene` renderer | done — Bangers + Patrick Hand (OFL, Vietnamese glyphs), split with "+", self-drawing underline, wheel, karaoke caption; stills of the sample checked; vitest 198 passed |
| 87.4 | Line-art pictures | done — Qwen line art drawn at render (cached, kept in the library as 16:9 `lineart`), 145 Tabler line icons drawn stroke by stroke as the fallback |
| 87.5 | UI wiring | done — Step 1 / batch / channel / automation / Step 2 / Step 4 VieNeu picker / Step 5; card written after the code (noted in it) |
| 87.6 | Verify | done — three sandbox runs (v1–v3), 8 real-run problems fixed; v3: PRESS 82.2 s, -tion 122.6 s, every word drawn; full pytest 2277, vitest 198 |
