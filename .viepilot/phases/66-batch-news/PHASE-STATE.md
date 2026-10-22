# PHASE-STATE — Phase 66: Shorts in batches and today's news ideas

- **Status:** implemented_verified_pending_owner_review 2026-10-22. Full pytest 1997 passed (8 new); Vitest 169.
- **Real sandbox run:** `GET /api/news/today` read 40 stories of the last 36 h from BBC World and NPR News in 3.2 s (no feed problem); the AI picked 5 with hooks in 16 s; 3 chosen articles read (1085 / 77 / 139 words); 5 "Don't say / Say" ideas for "ordering food" in 12 s, all distinct; a 3-Short news batch (dated 23–25 Oct) and a 5-Short mistakes batch (22–26 Oct) saved under the "Shorts" playlist; Automation "Run now" took the one due today, made the project, script, learning and audio, and **stopped at the visual plan**.
- **Open owner decision (found here):** the AI marks every Solo / VOX / Short segment "review its knowledge claims" (the generic fact-review flag), and Phase 62 approves a plan only with no issue and no fact flag — so a night run never finishes a voice-only Short or a Solo video; only conversation, chat and would-you-rather Shorts finish unattended. **Owner decided (2026-10-22): yes** — the night run clears the generic flag for the English-teaching Shorts (mistakes, word of the day, top 5, quiz, listening, blur) and approves; news, VOX and Solo presenter still wait; any specific issue stops. Re-run: the mistakes batch Short went to "waiting for review" unattended. Full pytest 1998 passed.
- **Tasks:** 5/5.

| Task | Scope | Status |
|---|---|---|
| 66.1 | Data | implemented_verified |
| 66.2 | Batch API | implemented_verified |
| 66.3 | News API | implemented_verified |
| 66.4 | Shorts batch page + Step 1 news | implemented_verified |
| 66.5 | Verification + real run | implemented_verified |
