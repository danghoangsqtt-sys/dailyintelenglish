# Phase 81 — Slow English podcast & Vocabulary flashcard Shorts

Source: [brainstorm 2026-10-28](../../../docs/brainstorm/session-2026-10-28-slow-podcast-flashcards.md). Owner: "Run /vp-evolve to add the phase from this brainstorm, then /vp-auto to build both formats." Mode: Add Feature. Doc-first: this plan and the task files are committed before code. No version bump (local 2.0.0 line, like Phases 78–80); no push.

## Owner decisions (locked)
- Two new Short templates (≤ 1 min, 9:16): **`slowpod`** (Slow English podcast) and **`flashcards`** (Vocabulary flashcards).
- English voice only. Slow podcast: the narrator reads slowly (default speed 0.8), the Vietnamese translation is shown, not read. Flashcards: the English word read twice per card.
- Content from the AI (topic, split into parts) or an owner-pasted list.
- Look: beige paper + Daily Beyond English green accents, bold black type, small logo (Phase 80 short brand).
- In the Shorts batch (kind cards), Step 1 Short templates and the Channel plan.

## Design
- Both are Solo voice-only Short styles (`SOLO_SHORT_STYLES`) drawn **from their script lines** (like chat / would-you-rather): no AI visual plan, no fact review. `_build_input_props` gives them `shortStyle`, the lines (with each line's `translation`), the learning pack; Automation's `has_visual_plan` is true for them; Step 5 says no visual plan is needed.
- **Slow podcast**: the script prompt writes 8–10 short sentences, one per line, opening with the "welcome back to my slow English podcast" line, ending with a follow line, each line with `language_notes.translation_vi`. `LanguageNotesOut` gains an optional `translation_vi` (stored in the existing JSON column; no migration). Step 2 shows and edits it for this style. The narrator's speed defaults to 0.8 for a new slow-podcast project.
- **Flashcards**: the script is a cover line ("Vocabulary: <topic>, part <n>."), one line per card ("<word>. <word>."), and a follow line; 8–10 cards. An owner list (`source_kind = vocabulary`) gives the words in order. The lesson step must cover every card word (required vocabulary = the card words), so each card gets part of speech, IPA and Vietnamese meaning from the learning pack. Lines are never split by the Phase 80 paragraph split.
- Renderer: `SlowPodScene` (paper background, one sentence per screen, karaoke English, Vietnamese below) and `FlashcardScene` (header pill, "FLASHCARD TỪ VỰNG" tag, cover card, card N/total with word, part of speech, IPA, green meaning card, deck slide with neighbours peeking); `Episode.tsx` routes `shortStyle` to them. `sampleShort.ts` gives the batch page a silent preview of both.

## Tasks
1. **81.1 Backend** — styles, prompts, `translation_vi`, slow default speed, flashcard required vocabulary, props, Automation/plan skip, batch templates, tests.
2. **81.2 Renderer** — the two scenes, routing, sample previews, Vitest + tsc.
3. **81.3 UI** — Shorts batch kind cards, Step 1 / Channel plan options, Step 2 translation field, Step 5 note, Vietnamese copy, browser tests.
4. **81.4 Verify** — real renders of both (temporary sandbox in the session scratchpad, removed afterwards), related + full pytest, records.

## Paths / allowed_files
- `backend/schemas/project.py`, `backend/content/script_service.py`, `backend/content/script_pipeline.py`, `backend/ai/prompts/script/solo_explainer.txt`, `backend/ai/prompts/script/section.txt`, `backend/content/learning_pipeline.py`, `backend/media/video_renderer_remotion.py`, `backend/media/video_service.py`, `backend/automation/runner.py`, `backend/channel/batch_service.py`, `backend/channel/channel_service.py`, `backend/library/explainer_service.py` (style lists only).
- `renderer/src/SlowPodScene.tsx` (new), `renderer/src/FlashcardScene.tsx` (new), `renderer/src/flashcardMath.ts` (new), `renderer/src/Episode.tsx`, `renderer/src/types.ts`, `renderer/src/sampleShort.ts`, tests `renderer/src/flashcard.test.ts` (new).
- `frontend/static/js/shorts_batch.js`, `frontend/static/js/step1_config.js`, `frontend/static/js/channel.js`, `frontend/static/js/step2_script.js`, `frontend/static/js/step5_video.js`, `frontend/static/js/i18n_vi.js`, `frontend/pages/*.html` (only where a style list lives).
- `tests/test_slowpod_flashcards.py` (new), existing batch/automation/script tests as needed.
- `.viepilot/phases/81-slow-podcast-flashcards/**`, `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`, `CHANGELOG.md`.

## Risks
- A card word missing from the learning pack: the card still shows the word; part of speech / IPA / meaning are blank (logged). Required vocabulary makes this rare.
- AI forgets `translation_vi`: validation for `slowpod` asks once more (repair); a line still without it shows English only.
- Slow speed changes timing: the length check uses the measured audio; a project over 60 s is reported in Step 4 like other Shorts.

## Verification
- `pytest tests/test_slowpod_flashcards.py` + batch / automation / script / learning suites; renderer `npx vitest run`, `npx tsc --noEmit`; real renders of both styles (frames + duration ≤ 60 s); full pytest.
