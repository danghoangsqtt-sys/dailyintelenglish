# Phase 91 summary — edit every kind of video on its video

Done 2026-11-03 on `owner-runs/20261001-r9` (not pushed, not installed). Defaults D131–D133.

## What changed

- **Step 2 keeps unchanged voices** (91.1, D133): a script save keeps the id and the voice of every line whose position,
  speaker and text are unchanged; Step 4, automation and the editors then make only the changed lines' voice.
- **Line-drawn Shorts in the editor** (91.2): slow podcast (the Vietnamese translation under each line), flashcards (a
  card's part of speech, IPA and Vietnamese meaning, saved to the lesson's vocabulary), chat and would-you-rather
  (messages by speaker) use the Phase 90 editor with their own fields and the live 9:16 video.
- **Spoken lines in the existing editors** (91.3, D131/D132): solo explainers (news, blur, mistakes, word of the day,
  top 5, quiz, listening, VOX, presenter) keep their plan editor with its live preview; the conversation 16:9 keeps its
  storyboard (no live video: its talking characters need the renderer's local sprites). Both gain "Các câu đọc": save
  one line, make the voice of the changed lines only; a solo plan is then saved again on the new voice and waits for
  the owner's approval, as after any script change.

## Real checks (sandbox)

| Kind | Edit | Voice | Render | Result |
|---|---|---|---|---|
| Flashcards (sandbox copy) | a card's meaning | — | — | the card on the live video changed at once |
| Slow podcast (sandbox copy) | a translation | — | — | the translation on the live video changed at once; undone |
| News Short (made in the sandbox) | one spoken line | 1 line + mix, 6 s | 48 s (after approving the re-saved plan) | the subtitle and voice carry the edit |
| Chat Short (made in the sandbox) | one message | 1 line + mix, 3 s | 35 s | the bubble carries the edit (`docs/operations/phase91-screens/`) |

Found while checking: after a voice change a solo explainer's preview failed ("The explainer source changed") → the
panel now saves the plan again on the new voice and asks for approval. Projects copied into the sandbox from the real
data show every voice as out of date (their voice files are outside the sandbox folder); in the installed app they
match. Tests: full pytest 2308 passed + 1 test updated for D133 (a re-save of an unchanged line keeps its id) + 1
event-loop test-order flake that passes alone.

Seen, not changed (existing before this phase): the chat Short's "DAILY BEYOND ENGLISH" header label runs under the
channel logo.
