# PLAN — Phase 68: live preview on the Shorts batch page (ENH-050)

Status: execution_authorized 2026-10-22 — the owner chose the live template preview.

| Task | Scope |
|---|---|
| 68.1 | Renderer: `sampleShort.ts` builds silent sample props for any Shorts template from one idea (title, brief, level): a few sample segments in that template's visuals (news headline + fact cards, blur words, a Don't say / Say pair taken from the quoted phrase of the title, the word of the day, a 5→1 countdown, a quiz with A/B/C and its "three, two, one / the answer is", a listening item with "Listen / One more time / Here is the sentence", chat messages, would-you-rather rounds), timed words for the captions and the VOX 9:16 geometry; the preview bundle exposes it (`window.ShortsSample.props`) and plays without sound (a tiny silent audio file) |
| 68.2 | Page: the Shorts batch page gets a sticky 9:16 preview column on the right (stacks on narrow screens); clicking an idea row (or a story) selects it; the template select, the level and edits to the selected idea refresh the preview; a small note says it is a preview of the look — the real Short is written by the AI and voiced |
| 68.3 | Tests: Vitest for the sample builder (every template gives a valid payload, the timeline covers the words, chat/wyr give a conversation Short), a browser test (the preview appears, follows the template and the selected idea), full pytest + Vitest; a screenshot check |

Kept: nothing is saved or sent to the AI by the preview. No version bump; CHANGELOG `[Unreleased]`.
