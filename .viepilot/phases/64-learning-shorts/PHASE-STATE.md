# PHASE-STATE — Phase 64: quick-learning Shorts

- **Status:** implemented_verified_pending_owner_review 2026-10-22. Full pytest: 1979 passed, 1 failed under load (`test_phase58_browser.py::test_settings_has_a_left_menu_with_language_and_theme`, Settings page, untouched here; passes alone 2/2). Vitest 163 (5 new), tsc clean.
- **Real sandbox Shorts (cloud AI, Edge TTS, Remotion, 1080×1920):** Don't say / Say "bored vs boring" — 2 pairs as comparison cards, 60 s, rendered in 129 s; Word of the day "resilient" — IPA and the Vietnamese meaning from the learning pack, an example with the word highlighted and a memory tip, 65 s; Top 5 phrases for small talk — a 5→1 countdown with progress dots, 71 s (the AI's script ran past the 45 s target; Shorts allow it). Fixes after reviewing the frames: the band labels no longer wrap, a "VI" tag replaces the 🇻🇳 flag (Windows has no flag emoji).
- **Tasks:** 5/5.

| Task | Scope | Status |
|---|---|---|
| 64.1 | Contracts | implemented_verified |
| 64.2 | Prompts | implemented_verified |
| 64.3 | Renderer LearnScene | implemented_verified |
| 64.4 | Step 1 / Channel / editor | implemented_verified |
| 64.5 | Verification + real Shorts | implemented_verified |
