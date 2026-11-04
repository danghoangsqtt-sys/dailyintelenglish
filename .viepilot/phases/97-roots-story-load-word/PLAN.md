# Phase 97 — Two more viral formulas: the root with a story, and "load the word" (plan, written before code)

Owner (2026-11-04): "Phân tích 2 mẫu video này và đưa vào hệ thống tạo video". Formulas only, none of the clips' words or pictures.

## Sample 1 (91 s, 16:9): "Why is September month 9 when its root means 7?"

A puzzle as the hook, the promise of a whole family of words, the root and its parts in colour, a short true story over pictures that
answers the puzzle, then each word of the family, and a quiz. It already matches our **Word roots** Short except for the puzzle and
the story.

D158: this upgrades `roots`; no new kind. The AI may add a `puzzle` and a `story` of up to four lines with pictures, **only for a true,
well-documented origin**; otherwise the Short is as it is today. The line-art look of the Short stays. It stays 9:16: the long 16:9
academic video is Phase 89, still planned.

D158 amended after four real runs: asked for a story, the AI gave none, drifted away from the word and invented origins ("seven reeds
as a compass"). Stories now come **only from the checked list** `word_roots.json`, written by hand: sept, oct and dec so far. The AI is not
asked for one, so it cannot invent one; more can be added to the list.

## Sample 2 (25 s): "Nạp từ vào trí nhớ"

One word said over and over, faster and faster, on a wall of that word with its meaning, a bar counting up to 100%, then the word with its
IPA, meaning and one example.

D159: a new Short, `loadword` ("Load the word"), 9:16 like all our Shorts (the sample is 4:3). Black background, as in the sample: here the
wall of words is the picture. Spoken: the word looped for 16 seconds, in five steps from normal speed to twice as fast, then the word once
and one example. D160: the loop is built in the audio mix from the word's own voice clip, at the same pitch; other videos are unchanged.

## Tasks

- 97.1 `loadword`: `load_word.py`, the loop in the mix, `LoadWordScene.tsx`, wiring in every list, sample clip, real video.
- 97.2 `roots`: `puzzle` and `story` in `word_family.py` and its prompt, the two beats in `RootsScene.tsx`, the editor, real video.
- 97.3 Full tests; install and push only when the owner asks.

## Risks

- The AI could invent a story: the prompt forbids it unless it is sure, but nothing checks the facts. The owner should read each story.
- Two times the speed may sound harsh: decide by listening to the real video.
