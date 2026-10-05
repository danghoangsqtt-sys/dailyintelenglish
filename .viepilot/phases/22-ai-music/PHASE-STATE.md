# PHASE-STATE — Phase 22: Background music (ENH-016), re-scoped by D50

- **Status:** re-scoped 2026-10-05. **D50 (owner):** stop AI music generation; use free music
  libraries downloaded by hand, with the licence recorded. The AI code is reverted, and
  `venv-music` and `models/music` are deleted (18.3 GB freed).
- **Plan:** `docs/implementation/phase-22-ai-music.md` (D43–D49, then § Re-scope D50).

| Task | Description | Owner | Status |
|---|---|---|---|
| 22.1 | Spike: ACE-Step 1.5 install, VRAM, speed, quality | Claude + owner | ❌ **FAIL** 2026-10-05: owner "nhạc quá tệ" (messy, wandering rhythm, worst in upbeat/acoustic); superseded by D50 (card `tasks/task-22.1.md`) |
| 22.2 | AI music worker, engine, jobs, provenance, Library "Generate" | Claude | ↩️ built 2026-10-05, **reverted** by D50 (card `tasks/task-22.2.md`) |
| 22.3 | AI music brief + Step 4 previews → pick → full length | Claude | ↩️ built 2026-10-05 (full suite 1396 passed), **reverted** by D50 before push (card `tasks/task-22.3.md`) |
| 22.7 | Licence metadata for library tracks + free-source guide | Claude | planned (card to write) |
| 22.5 | YouTube description credit line from the episode's music | Claude | planned |
| 22.4 | Speech-aware ducking + intro/outro levels | Claude | planned |
| 22.6 | Gate B-17 (owner listening test on a real episode) | Owner | planned |
