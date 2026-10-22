# PLAN — Phase 64: quick-learning Shorts (ENH-046)

Status: execution_authorized 2026-10-22 — the owner asked for the three templates of the brainstorm's group C.

Design: three more 9:16 Short templates on the Phase 63 pipeline (voice-only narrator, AI script and plan, approval, vertical render, Channel series and automation): `explainer_style` **`mistakes`** (❌ Don't say … ✅ Say …), **`wordday`** (Word of the day) and **`top5`** (Top 5 phrases). The plan reuses the existing visual kinds, so no schema or editor field changes: a mistake pair is a `diagram` "comparison" with two nodes (Don't say / Say, the phrases as details); the word of the day is a `text_card` (title = the word, bullets = part of speech and a short meaning) and `quote` examples; a Top 5 item is a `text_card` (title = the phrase, one bullet = its meaning).

| Task | Scope |
|---|---|
| 64.1 | Contracts: the three styles in the project / Channel series schemas and every voice-only / Short check (one list in `backend/schemas/project.py`, used everywhere) |
| 64.2 | Prompts: script SHORT sections — mistakes: 2–4 pairs, each "Don't say …, say …" plus why in one sentence, real common learner mistakes only; word of the day: the word, its meaning in simple English, pronunciation tip, 2 example sentences, a memory tip; top 5: a countdown from 5 to 1, each phrase + meaning + one example; all with the hook and the one-line follow. Plan prompt sections mapping each to the visuals above |
| 64.3 | Renderer: `LearnScene` for the three templates on the brand background (green → dark, soft shapes, Phase 61 motion): mistakes — a red "DON'T SAY" card with the wrong phrase struck through, then a green "SAY" card popping in with a check; word of the day — the word big, the IPA and the Vietnamese meaning from the project's learning pack when it has that word, part of speech, the example with the word highlighted; top 5 — a big countdown number (5 → 1) flipping in, the phrase and its meaning; karaoke captions in all |
| 64.4 | UI: three more template cards in the Shorts group on Step 1 (topic or AI ideas); Channel series options; Step 5 editor titles and outside-AI prompts; Vietnamese strings |
| 64.5 | Tests (contracts, prompts, renderer helpers), real sandbox Shorts of the three templates sent to the owner, full pytest + Vitest |

Kept: everything else unchanged; no new visual kind. No version bump; CHANGELOG `[Unreleased]`.
