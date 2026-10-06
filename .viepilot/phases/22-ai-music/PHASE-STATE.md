# PHASE-STATE — Phase 22: Background music (ENH-016), re-scoped by D50

- **Status:** re-scoped 2026-10-05. **D50 (owner):** stop AI music generation; use free music
  libraries downloaded by hand, with the licence recorded. The AI code is reverted, and
  `venv-music` and `models/music` are deleted (18.3 GB freed).
- **Plan:** `docs/implementation/phase-22-ai-music.md` (D43–D49, § Re-scope D50, § Smart music D51).
- **D51 (owner 2026-10-06):** auto-select by topic + length; fit start/end to the video; volume under the voice; fade out at the video end. Old AI tracks deleted (`data/tmp/music-spike`, 1.8 GB). Order 22.7 → 22.4 → 22.8 → 22.5 → 22.6.

| Task | Description | Owner | Status |
|---|---|---|---|
| 22.1 | Spike: ACE-Step 1.5 install, VRAM, speed, quality | Claude + owner | ❌ **FAIL** 2026-10-05: owner "nhạc quá tệ" (messy, wandering rhythm, worst in upbeat/acoustic); superseded by D50 (card `tasks/task-22.1.md`) |
| 22.2 | AI music worker, engine, jobs, provenance, Library "Generate" | Claude | ↩️ built 2026-10-05, **reverted** by D50 (card `tasks/task-22.2.md`) |
| 22.3 | AI music brief + Step 4 previews → pick → full length | Claude | ↩️ built 2026-10-05 (full suite 1396 passed), **reverted** by D50 before push (card `tasks/task-22.3.md`) |
| 22.7 | Library track details (mood, tags, measured length, licence, credit) + free-source guide | Claude | ✅ done 2026-10-06: details rows + PATCH + Library UI + guide; full suite 1380 passed (card `tasks/task-22.7.md`) |
| 22.4 | Smart bed: fit to video length (trim / crossfade loop), loudness-normalised, speech-aware ducking, fade-in + fade-out at the video end; full-video soundtrack for both renderers (D51) | Claude | ✅ done 2026-10-06: bed + voice stem + full-video soundtrack on both renderers; real check lengths exact, open ~7 LU under voice, ducked −14 dB, fade to silence; 1399 passed; **owner OK on timing** 2026-10-06 (levels pending real tracks) (card `tasks/task-22.4.md`) |
| 22.8 | Auto-select a track by topic + length ("✨ Auto" in Step 4, AI pick among top candidates, rule fallback, reason shown) (D51) | Claude | ✅ done 2026-10-06: score + AI pick among top 5 + Step 4 Auto default; real Gemini picks on 3 real projects; 1410 passed (card `tasks/task-22.8.md`) |
| 22.5 | YouTube description credit line from the episode's music | Claude | ✅ done 2026-10-06: credit line added on read/export (never stored); 1413 passed (card `tasks/task-22.5.md`) |
| 22.9 | Automatic track classification (pace from onset density, ~BPM, energy, brightness, mood suggestion) + rhythm-aware auto-select | Claude | **in_progress** 2026-10-06 (card `tasks/task-22.9.md`) |
| 22.6 | Gate B-17 (owner listening test on a real episode) | Owner | planned |
