# Phase 81 state

Status: implemented_verified (2026-10-28). Not pushed, not installed.

| Task | Scope | Status |
|---|---|---|
| 81.1 | Backend | done — styles, prompts, translation_vi, slow speed 0.8, flashcard words in the lesson, line-drawn props; 7 new tests, related 180 passed |
| 81.2 | Renderer scenes | done — SlowPodScene, FlashcardScene, routing, batch samples; Vitest 190, tsc clean; stills checked |
| 81.3 | UI | done — Step 1 cards, Channel plan, Automation labels, batch kind cards + preview, Step 2 translation field, Step 5 note, VI copy; UI suites 38 + 1 new passed |
| 81.4 | Verify and records | done — real Shorts: slow podcast 43.1 s, flashcards 38.9 s (after the deck fix); full pytest 2201 passed + 3 fixed |

Verification 2026-10-28: real Shorts made through the Shorts batch 'Make videos now' in a temporary sandbox (removed). Slow podcast: 8 lines, each with translation_vi, speed 0.8, 43.1 s 1080x1920. Flashcards: the first run wrote prose; fixed by building the script from a schema-checked deck (commit ae0b875); second run 8 cards with part of speech, IPA and Vietnamese meaning from the lesson, 38.9 s. Frames in `docs/operations/phase81-screens/`. Full pytest: 2201 passed, 3 failed -> 2 tests counted 9 Step 1 template cards (now 11), 1 Step 1 browser test passed alone (load); after the fix those files 11 passed.

Install 2026-10-28 (owner: "Build the new Full edition with Phase 81 and install it into the app, keeping backups like last time"): Full 2.0.0 from e1cb759 (clean) in `dist/2.0-phase81-20261028/` (ZIP SHA-256 6ade9db79d13d11862c62d6dac0b2643154751520c30426a1f0df181e4d5803f); installed with `scripts/install_desktop.ps1` (idle-job preflight; `app.before-upgrade.db`, `app.at-exit.db`, previous app and shortcut in `data/backups/desktop-20261028-081715-544/`). Restarted PID 42060 (slow first start, ~45 s); dashboard 200, build e1cb759, Step 1 and batch show both formats, renderer ready, SQLite integrity ok, 66 projects, 0 FK issues. Not pushed.
