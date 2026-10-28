# Phase 82 — Shorts that carry their message (knowledge/news length, self-contained clips)

Owner (2026-10-28, Vietnamese original): "các video short tạo từ hệ thống, video short cắt từ 16:9 đều có vấn đề nội dung rất cụt, và khó hiểu, không truyền tải được thông điệp và nội dung đặc biệt là các video truyền đạt kiến thức, tin tức."

Owner decisions (AskUserQuestion 2026-10-28): knowledge/news Shorts use a **full 55–60 s** with a message structure; clips cut from 16:9 episodes: **choose self-contained passages** (no context line or end card requested).

## Evidence (owner database)
- Clips of "The Office Startup": lines 12–16 open with "I certainly agree with that perspective, Jack." / "Precisely."; lines 20–22 end on "We truly hope these practical strategies help you…" (an episode sign-off). The proposal only checks 30–90 s; the prompt's "complete moment" rule was ignored.
- Generated Shorts aim at 0.75 min (~90 words): Word-of-the-day Shorts have 36–39 s of speech; news asks for 3–6 facts in that space.

## Tasks
1. **82.1 Message Shorts** — `MESSAGE_SHORT_STYLES = news, blur, mistakes, top5, presenter, vox` get 0.95 min (~57 s; ≤ 60 s with the 2 s end card) wherever a Short's length is set (Channel/batch project creation, Step 1 default for those templates); their prompts get a message structure: hook question/claim → one context sentence → two or three key points each with a concrete example or fact → a takeaway that answers the hook → follow line. Quick-learning templates (wordday, flashcards, slowpod, quiz, listen, chat, wyr) stay at 0.75. Paths: `backend/schemas/project.py`, `backend/channel/channel_service.py`, `backend/channel/batch_service.py`, `backend/ai/prompts/script/solo_explainer.txt`, `frontend/static/js/step1_config.js`, tests.
2. **82.2 Self-contained clips** — after the AI proposal, each clip's boundaries are checked: a first line that depends on earlier talk ("I agree…", "Precisely", "That…", "Exactly", "Yes,", "So,"…) moves the start back (up to 3 lines, within 90 s); a last line that is an episode sign-off ("hope these…", "thanks for watching", "see you…") is dropped when the clip stays ≥ 30 s; a last line that asks the other speaker a question extends the end by one line within 90 s; a clip still opening on a dependent line is dropped. The prompt states the rule with examples. Paths: `backend/content/shorts_service.py`, `backend/ai/prompts/shorts/clip_proposal.txt`, `tests/test_shorts.py`.
3. **82.3 Verify** — real Shorts (news-style/presenter) length and script read-through, a real clip proposal on The Office Startup, related + full pytest, records.

## Risks
- Heuristic openers in other wordings: the list covers the common ones; the AI rule still applies; a clip is never made longer than 90 s.
- Longer scripts may exceed 60 s with a slow voice: target 57 s leaves room; Step 4 reports a Short over 60 s as before.
