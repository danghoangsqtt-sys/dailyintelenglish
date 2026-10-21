# PLAN — Phase 60: greeting, topic preview, thanks + subscribe, smiles (ENH-042)

Status: execution_authorized 2026-10-22 — the owner asked for it directly; the design follows the request (no options to choose). Done while Phase 59 (VOX) is in progress; it touches only prompts and their tests.

| Task | Scope |
|---|---|
| 60.1 | Script prompts: `outline.txt` plans the opening/closing into the first/last section objectives; `section.txt` makes the first section open with the greeting + who is speaking + today's topic preview and the last section end with thanks for watching + like/subscribe/comment + goodbye; `solo_explainer.txt` replaces its "brief friendly sign-off" with the same opening/closing for one presenter/narrator |
| 60.2 | Smiles: `storyboard/storyboard.txt` — beats covering the opening and the closing use `smile` (or `laugh`); `storyboard/explainer.txt` — the first and last segments get a `wave` gesture at the greeting/goodbye tokens; `explainer_vox.txt` — the first and last cards carry the welcome and the thanks |
| 60.3 | Tests: rendered prompts contain the rules for first/last sections (conversation, Solo, VOX); full pytest |

Not changed: word-for-word dialogues (Phase 57 verbatim), the word budgets, the Solo layout rules. No version bump; CHANGELOG `[Unreleased]`.
