# Phase 88 — "Easy grammar" Short (2026-11-03, planned)

Follows Phase 87 (VieNeu voice D125, length D126, brand colours D127). Source: sample B in the
[brainstorm](../../../docs/brainstorm/session-2026-11-03-academic-roots-grammar.md) — break rote formulas, give one rule
that explains them, build cards scene by scene, end on a summary table.

## Tasks

1. **88.1 `grammar` template: data and script** — Short style `grammar`; a lesson `{point, hook{pain_vi, formulas[],
   promise_vi}, scenes[{label_vi, title_vi, subtitle_vi, cards[]}], summary{columns, rows}, core_rule_vi/en, quiz?}` with
   card kinds compare / formula (fixed colour chips) / table / rule / example (EN + VI) / sticker / stamp / lego. Kinds
   now: one grammar point "in essence", and errors carried over from Vietnamese ("I very like", missing tense, missing
   article). Same-meaning pairs stay in `mistakes`. Fact check on rules and examples. Paths: `backend/schemas/project.py`,
   `backend/schemas/` (lesson model), `backend/ai/prompts/script/grammar.txt`, `backend/content/script_pipeline.py`,
   `backend/content/script_editor.py`, tests.
2. **88.2 `GrammarScene` renderer** — paper background, coloured scene pill + bold title + subtitle, rounded cards that
   stack down as the narration reaches them, fixed colour code (BE blue, -ing orange, V3 yellow sticker, modal purple,
   S/V/O), red "forget it" stamp, summary table that fills row by row, karaoke captions. Paths:
   `renderer/src/GrammarScene.tsx`, `renderer/src/grammarMath.ts`, `Root.tsx`, `types.ts`, `sampleShort.ts`, vitest.
3. **88.3 UI wiring** — Step 1, Shorts batch kind card (a list of grammar points → one Short each), Channel plan,
   Automatic; optional quick quiz reusing the `quiz` countdown. Browser tests.
4. **88.4 Verify** — tests; two `grammar` Shorts (passive voice, present perfect) with transcript and frame checks.

Task cards are written when the phase starts.
