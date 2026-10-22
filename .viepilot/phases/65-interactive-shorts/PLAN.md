# PLAN — Phase 65: interactive Shorts (ENH-047)

Status: execution_authorized 2026-10-22 — the owner asked for the four templates of the brainstorm's group D.

Design — two families on the existing pipelines, all 9:16 under a minute:
- **One narrator (voice-only, like Phases 63–64):** `explainer_style` **`quiz`** (countdown quiz) and **`listen`** (listening challenge). Their plans use existing visuals: a quiz question is a `text_card` (title = the question, bullets = the options "A …", "B …", "C …", emphasis = the right option); a listening item is a `quote` (text = the sentence, highlight = the tricky words).
- **Two voices (a conversation, the owner's D7 rule):** `explainer_style` **`chat`** and **`wyr`** on a 2-character **conversation** project. No visual plan is needed: the video is drawn from the script lines themselves — chat bubbles (left/right per speaker, typing dots before each message, the spoken word highlighted), or the Would-you-rather screen (the two options parsed from "Would you rather … or …?", a 3-2-1 timer, then the other character's choice and reason). The main render is vertical with no sprites.

| Task | Scope |
|---|---|
| 65.1 | Contracts: the four styles (`quiz`, `listen` for Solo; `chat`, `wyr` for a 2-speaker conversation) in the project and Channel schemas, the Short checks (60 s, vertical main render), the render props carry the conversation Short style; the conversation Shorts need no storyboard (automation skips that step) |
| 65.2 | Prompts: script SHORT blocks — quiz: 2–3 questions, each with three options said as "A …, B …, C …", "Three, two, one", "The answer is …" and one-line why; listen: 2–3 short sentences, each "Listen." + the sentence said once naturally, "One more time." + again, then "Here is the sentence:"; chat: a short real-life text-message conversation between the two characters in short messages; would you rather: the first character asks "Would you rather <A> or <B>?" (2–3 rounds), the second picks one and gives a reason. Plan prompt blocks for quiz / listen |
| 65.3 | Renderer: `InteractScene` (quiz: question card, options popping in, a ring timer during "three, two, one", the right option turning green and the others fading at "the answer is"; listen: an ear and a sound wave while listening with the captions hidden, the sentence revealed with its tricky words highlighted at "here is the sentence"); `ChatScene` (a phone-like generic chat with avatars by initials and colours, typing dots, bubbles appearing with their line, auto-scroll) and `WouldYouRatherScene` (two halves red/blue with the options, a timer, the chosen half growing with a check, the reason as the caption) |
| 65.4 | UI: four more Shorts template cards on Step 1 (chat / would-you-rather need two characters; quiz / listen one narrator); Channel series options; Step 5 shows "no visual plan needed" for chat / would-you-rather; Vietnamese strings |
| 65.5 | Tests (contracts, prompts, parsers and timing helpers), real sandbox Shorts of the four templates sent to the owner, full pytest + Vitest |

Kept: conversation and Solo videos unchanged (a conversation without a Short style renders exactly as before); no branded chat UI; no invented poll numbers. No version bump; CHANGELOG `[Unreleased]`.
