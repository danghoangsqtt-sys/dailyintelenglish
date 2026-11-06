# Phase 98 — Doodle story: a whole story in English, told over hand-drawn pictures (plan, written before code)

Owner (2026-11-05): "tôi muốn hệ thống của tôi có thể làm được dạng video này", then, on the content: "kết hợp giữa một chủ đề lịch sử,
thần thoại, chuyên môn, hay một nội dung truyện ngắn tự tạo kết hợp với tiếng anh thay vì chỉ là nội dung không đầu không đuôi".
Analysis, measurements and the Qwen test: [session](../../../docs/brainstorm/session-2026-11-05-doodle-explainer.md). Formulas only, none of
the sample's words or pictures.

## The sample, in numbers

10:24, 112 still pictures (median 4.9 s, 16 spoken words each), a 0.4 s crossfade, no movement inside a picture, one voice, no music, capitals
in groups of 3-5 words with the spoken word in a black pill. Its faults are not copied: one picture held 59 s, prompt words drawn into
pictures, white captions unreadable on cream paper.

## Decisions

- **D161, one new kind.** `doodle` ("Doodle story"), a voice-only Solo style beside VOX. 16:9, 3-12 minutes, 8 by default; never a Short in this
  phase. VOX, its look and every other kind stay as they are; a new test proves a VOX plan is unchanged.
- **D162, four kinds of story.** `explainer_subject` also takes `history`, `myth` and `story`, valid only for `doodle`, which also uses the
  existing `field` (a specialised subject). The column is plain text, so no migration. The creator gives a topic, or pastes material (an
  article, notes, or their own story) as the source; it is rewritten in new words. `source_kind` "article" stops being news-only for this
  kind. Breaking news is not a kind of this phase.
- **D163, a beginning, a middle and an end.** One arc, chosen before the script is written, and one opening and one ending only:

  | Kind | The arc |
  |---|---|
  | History | a puzzle or striking moment, the world then, the people and what they wanted, the turn, what followed, the answer to the opening |
  | Myth | the question the myth answers, the world, the hero and the wish, the trial, the price, the meaning, and which culture tells it |
  | Field | an everyday mystery, the wrong explanation, the investigation, one key idea with one picture-able comparison, the answer, why it matters |
  | Short story | an ordinary moment and a want, the problem, things get worse, the choice, the result, a last line that echoes the first |

- **D164, English inside the story, not beside it.** 5-8 target words for the level are chosen **before** the script, and the story is written
  to need them. A check requires each word to be spoken at least 3 times, spread across the video. Its first use shows a term card over the
  picture (the word, IPA, its meaning by audience setting; 4-5 s). The last 30-45 s retell the story's end using the words, then the list goes in
  the YouTube description. Pace follows the project's CEFR level (B1: 125 words a minute, the sample's 175 is too fast for learners). This
  extends the owner's "film + term cards" choice.
- **D165, truth by kind.**
  - History and field: the existing fact check, numbers and names flagged, and "not confirmed" said aloud where it applies.
  - Myth: named as a myth with its culture, told as "the story says", never as fact.
  - Short story: invented and said to be, with no real people, places as settings only, and no fact check.
  - Real deaths are told with respect. The owner reviews every video before export.
- **D166, the pictures.** Aged paper, ink line, earth colours, small green and yellow accents. Dot-face stick people are an exception to D123 for
  this kind only; the channel's cast is never drawn. Story and myth keep the same hero through a short look line repeated in every prompt ("a
  stick figure with a red scarf"). Labels are English, at most three per picture, and given exactly; the plan's prompt holds a description, never
  a title of the picture. Doodle pictures do **not** go in the Activity Library (`pipelines.py` keeps every Qwen picture there today and they would
  appear in other videos). Qwen saves each group before starting the next one. The implementation uses groups of 20 to reduce model reloads.
- **D167, the picture on screen.** Full frame, still, a 0.4 s crossfade, a new picture at most every 24 spoken words and 12 s. New caption style
  `pill` (capitals, 3-5 words, spoken word in a black pill, with an outline so it reads on paper): the default of this kind, offered as an option
  elsewhere, with `outline` still the default of every other kind. No music by default; the existing music choice still works.

## Cost

Pictures are about one for every 16 words at about 30 s each. B1: 3 min about 24 pictures (12 min of drawing); 8 min about 62 (31 min); 12 min about 94
(47 min). A Lite computer uploads or pastes pictures from an outside AI, as VOX does.

## Tasks

- 98.1 **The kind:** `doodle` and the three subjects in `schemas/project.py`, and the kind's card with its four story types in Create and Step 1,
  with a sample clip.
- 98.2 **Script:** target words first (`learning_pipeline.py`), the arc prompts in `script/solo_explainer.txt`, one arc through a long script
  (`script_pipeline.py`), and the checks: one opening and one ending, words said 3 times, length, the ending answers the opening.
- 98.3 **Plan and pictures:** `storyboard/explainer_doodle.txt`, the split at 24 words, `qwen_doodle_prompt` with the hero's look, groups of 20, no
  library copy, a check that no prompt carries a picture's title.
- 98.4 **On screen:** `DoodleScene.tsx` (full frame, crossfade, term card, recap), the `pill` caption with paging of 3-5 words, the renderer's wiring,
  the 12 s check.
- 98.5 **Truth and editing:** the rules of D165 in `fact_check.txt` by kind; on Step 5 see, redraw or upload each picture and edit the cards.
- 98.6 **YouTube:** the word list and, for a short story, a line saying it is fiction.
- 98.7 **Tests and real videos:** the VOX unchanged test, full pytest and Vitest, then real runs in this order: a 3-minute myth, a 3-minute short story, an 8-minute
  history. Look at every picture and listen to the end. The owner watches them and decides; install and push only when the owner asks.

Later, if the owner accepts this: Automation, Channel and Shorts batch (Phase 99), then Shorts cut from a long video.

## Risks

- A long script may come back short or restart its formula (VOX did both, Phase 86). If the AI cannot hold 8 minutes after the prompt work, the
  default drops to what real runs prove, and the owner is told.
- Words forced in sound unnatural: a word that cannot be used naturally is replaced before the script, not pushed into it.
- The hero's look may drift over 60+ pictures, and Qwen may draw wrong shapes or letters: only 6 pictures have been tested. Every picture can be redrawn,
  and each real run reports how many had to be.
- History can be wrong even after the check, which only compares with the source given: the owner reads every history video before export.
- The term card must not cover the picture's labels: its place is fixed and checked on the real videos.
