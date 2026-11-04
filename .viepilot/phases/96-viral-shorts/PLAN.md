# Phase 96 — Picture-led Shorts from the viral clips (plan, written before code)

Owner (2026-11-04), after the analysis of 8 viral TikTok clips:
- "đọc ra 1 từ, tạo ảnh có liên quan tới từ thay vì chỉ là một nền xanh, từ vựng được đọc đi đọc lại 5-6 lần và 1 câu ví dụ,
  phần giải thích từ vựng bằng tiếng Anh hoặc tiếng Việt";
- "nếu không làm được video quay thật thì ta tạo các ảnh cũng được ... tôi cởi giày thì đi kèm hình cởi giày";
- "Lập kế hoạch Phase 96 gồm cả dạng ảnh theo từng câu".

We copy formulas only: never the clips' words, pictures, logos, film clips or real people's photos.

## Why

Our quick Shorts are words on a green gradient. The viral ones always show something: an object, a painting, a person; one
idea per screen; a challenge at the start; repetition. This phase makes four picture-led Shorts.

## Scope: four Shorts

| # | Short | From clip | New or upgrade | Spoken | On screen |
|---|---|---|---|---|---|
| A | Word of the day | 5 | upgrade `wordday` (D147) | the word six times, one example | full-frame picture, word copies, IPA, explanation by audience |
| B | "What is this called?" | 7 | new `whatis` | the question, a silent 3-2-1, the name; 8-10 objects | object on a plain colour, countdown, name, IPA, meaning by audience |
| C | A picture for each sentence | 6, 8 | new `picstory` | 5-10 short first-person sentences | one full-frame picture per sentence, words coloured as read |
| D | Basic vs Advanced | 3 | new `levelup` | "I'm tired. I'm beat." 5-6 pairs | a red and a blue label, the talking character, a small picture for the phrase |

Not in this phase: faster VOX, line boil and parallax (clips 1, 2, 4): their own phase after these are tested on the channel.
Real footage is not added to the renderer (the owner chose pictures).

## Shared decisions

- D148: all four are drawn from their lines (`LINE_DRAWN_STYLES`): one schema-checked answer from the AI, no storyboard or
  visual plan, like word roots. Old Word-of-the-day projects keep their approved plan.
- D150: the voice is English; explanations on screen follow the audience setting (English, Vietnamese or both).
- D151: pictures are 9:16 and drawn by Qwen when the video is made (about 33 s each on the RTX 3060). No readable text and no
  visible faces (D123). Without Qwen (Lite): the closest library picture, an uploaded one, else the plain background; the
  video is always made and the page says which pictures are missing.
- D152: **first-person framing for C**: only hands and feet are shown, so no two pictures show a different person. The
  same style sentence and one seed per video keep the pictures alike.
- D153: every picture can be checked on Step 5's editor: its description, "Draw again" and **upload** (new, so Lite and a
  picture made with an outside AI work). All four kinds appear in Create, Step 1, Shorts batch, Channel and Automation.
- D154 (new capability B needs): a line may ask for a silent pause after it, for the 3-2-1. The audio mix does not have this
  today.
- D155: C with a closing line "If you understood this, you are an A2 listener" is an option of C for listening practice,
  not a fifth kind. The existing Listening challenge stays as it is.

## Tasks, in order

- **96.1 Word of the day (A):** built, being tested. `word_repeat.py`, `word_picture.py`, `WordRepeatScene.tsx`. Finish: a real
  video, sample clip, full tests. The owner looks at it before 96.3.
- **96.2 Shared picture tools:** one module for 9:16 pictures of a line-drawn Short (draw, cache by description, library
  stand-in, redraw, upload) that A moves onto; the upload route and the editor's button; the missing-pictures note.
- **96.3 Pilot for C, before its template:** draw 8 pictures for one script (taking off shoes, walking on sand...) with the
  first-person recipe. **The owner decides from these pictures** whether the look is good enough. If hands and feet come out
  badly: try another style sentence once, then report instead of building on it.
- **96.4 A picture for each sentence (C):** `picture_story.py` (AI: sentences and a picture description each, the level
  line option), `PictureStoryScene.tsx` (slow zoom, coloured words), wiring.
- **96.5 "What is this called?" (B):** the pause (D154) in the audio mix and timing; `object_quiz.py` (a theme and 8-10 objects),
  `ObjectQuizScene.tsx` (circle countdown, name, IPA); objects drawn on a plain colour, so no background removal is needed.
- **96.6 Basic vs Advanced (D):** `level_up.py` (5-6 checked pairs, real idioms only), `LevelUpScene.tsx`, using the Solo
  presenter's talking character; the character is chosen in Step 1 as usual.
- **96.7 Finish:** sample clips, Vietnamese labels, full pytest and Vitest, browser tests, one real video of each kind in the
  sandbox, both themes and phone for the changed pages.

## Verification for each Short

Unit tests for the schema and lines; Vitest for the maths and sample; a browser test that the kind opens from Create and Step
5 shows it; **one real video** (real AI, voice, Qwen, render), checked frame by frame inside the safe zone at 1080x1920.

## Risks

- AI pictures may show the wrong action or bad hands: the pilot (96.3) and "Draw again" / upload are the answer.
- Still pictures lose the real-life feeling of clip 6, so C may do less well: post it and compare.
- A video of 10 new pictures takes about 6 minutes on this machine and needs 8 GB of VRAM; a batch of many takes long.
- Vertical pictures do not fit the Activity Library (16:9 only), so they stay with their project and are not reused at first.
- D154 touches the audio mix that every video uses: its tests must show that videos with no pause are unchanged.

Not installed or pushed until the owner asks.
