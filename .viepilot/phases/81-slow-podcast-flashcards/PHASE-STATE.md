# Phase 81 state

Status: implemented_verified (2026-10-28). Not pushed, not installed.

| Task | Scope | Status |
|---|---|---|
| 81.1 | Backend | done — styles, prompts, translation_vi, slow speed 0.8, flashcard words in the lesson, line-drawn props; 7 new tests, related 180 passed |
| 81.2 | Renderer scenes | done — SlowPodScene, FlashcardScene, routing, batch samples; Vitest 190, tsc clean; stills checked |
| 81.3 | UI | done — Step 1 cards, Channel plan, Automation labels, batch kind cards + preview, Step 2 translation field, Step 5 note, VI copy; UI suites 38 + 1 new passed |
| 81.4 | Verify and records | done — real Shorts: slow podcast 43.1 s, flashcards 38.9 s (after the deck fix); full pytest 2201 passed + 3 fixed |

Verification 2026-10-28: real Shorts made through the Shorts batch 'Make videos now' in a temporary sandbox (removed). Slow podcast: 8 lines, each with translation_vi, speed 0.8, 43.1 s 1080x1920. Flashcards: the first run wrote prose; fixed by building the script from a schema-checked deck (commit ae0b875); second run 8 cards with part of speech, IPA and Vietnamese meaning from the lesson, 38.9 s. Frames in `docs/operations/phase81-screens/`. Full pytest: 2201 passed, 3 failed -> 2 tests counted 9 Step 1 template cards (now 11), 1 Step 1 browser test passed alone (load); after the fix those files 11 passed.
