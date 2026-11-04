# Phase 96 — Word of the day: one word, its picture, said six times (plan, written before code)

Owner (2026-11-04), about the TikTok clip of "meticulous": "đọc ra 1 từ, tạo ảnh có liên quan tới từ thay vì chỉ là một nền
xanh, từ vựng được đọc đi đọc lại 5-6 lần và 1 câu ví dụ, phần giải thích từ vựng bằng tiếng Anh hoặc tiếng Việt".

## Decisions

- D147: this upgrades the existing **Word of the day** template; no new kind of video (keep old features, no new modes).
- D148: the Short is drawn from its lines (`LINE_DRAWN_STYLES`), like word roots: one schema-checked word from the AI, no
  storyboard or visual plan. Old Word-of-the-day projects with an approved plan still render with their plan.
- D149: spoken: the word six times (one line each), then one example sentence; no hook or follow line. Under 20 seconds.
  The voice stays English, as the audience setting says.
- D150: the explanation is on screen and follows the audience setting: English definition (international), Vietnamese
  meaning (Vietnamese), both (both). The example's translation shows only when Vietnamese is shown.
- D151: the picture fills the 9:16 frame, drawn by Qwen from the AI's description (no text, no visible faces, per D123). No
  Qwen (Lite): the closest approved library picture; none: the brand background. The video is always made.

## Tasks

- 96.1 Backend: `backend/content/word_repeat.py` (schema, prompt, beats), `_run_wordday_job`, `language_notes.wordday`,
  `backend/media/word_picture.py` (draw, library fallback, redraw), render props; old projects keep their plan.
- 96.2 Renderer: `WordRepeatScene.tsx`, `wordRepeatMath.ts` (word copies appear one per repetition), Episode wiring, sample.
- 96.3 Front end: Step 5 and Step 2 treat it as drawn from lines; the beat editor edits its texts and redraws the picture;
  card descriptions and Vietnamese labels.
- 96.4 Verify: unit, Vitest and browser tests; a real Short in the sandbox with a real AI word, voice and Qwen picture.

Not installed or pushed until the owner asks.
