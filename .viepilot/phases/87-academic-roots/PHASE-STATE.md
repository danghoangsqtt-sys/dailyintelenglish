# Phase 87 state

Status: in_progress (2026-11-03). Plan committed before implementation; the owner said "Chạy Phase 87", self-implemented in this session.

| Task | Scope | Status |
|---|---|---|
| 87.1 | VieNeu engine (isolated worker) | done — persistent worker, Whisper word timings aligned in the app; real run on this machine: 3 lines, monotonic timings, 11 s first line (model load) then ~3 s; setup script fixed for Windows PowerShell 5.1 stderr, interrupted venvs and hub symlinks (ONNX Runtime refuses them) |
| 87.2 | `roots` template: data and script | done — word family schema, checked list (32 roots, 20 prefixes, 20 suffixes), beats vi/en, narrator switched to VieNeu for Vietnamese narration, Step 2 keeps the cards, batch rule |
| 87.3 | `RootsScene` renderer | in_progress — task card written |
| 87.4 | Line-art pictures | in_progress — task card written |
| 87.5 | UI wiring | planned |
| 87.6 | Verify | planned |
