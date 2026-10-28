# Brainstorm — Slow English podcast & Vocabulary flashcard Shorts (2026-10-28)

workflow_version: 2.19.0
Status: scope locked — ready for `/vp-evolve` → `/vp-auto`

## Request

Owner (Vietnamese original): "Tôi muốn làm thêm các dạng video giống như thế này", with four TikTok screenshots:

1. **Slow English podcast** — a beige paper background, one large bold English sentence ("and welcome back to my slow English podcast.") and its Vietnamese translation in smaller type underneath ("và chào mừng trở lại với kênh podcast tiếng Anh nói chậm của tôi."). One sentence per screen.
2. **Vocabulary flashcards** — a header pill "Sinh hoạt hằng ngày (P1)", a small "FLASHCARD TỪ VỰNG" tag, a cover card ("Từ vựng chủ đề: Sinh hoạt hằng ngày — Phần 1"), then one white card per word with a counter ("03 / 22"), the word ("wash up"), part of speech ("v."), IPA ("/wɑːʃ ʌp/") and a green meaning card ("Rửa tay rửa mặt"); neighbouring cards peek at the sides like a deck.

## Decisions (owner, AskUserQuestion 2026-10-28)

| Topic | Decision |
|---|---|
| Podcast voice | **English only, slow** (≈ −20 % rate). The Vietnamese translation is shown, not read. Uses the existing Edge voices. |
| Flashcard voice | **The English word read twice** (optionally one short example sentence); part of speech, IPA and Vietnamese meaning shown on the card. No Vietnamese voice. |
| Content source | **AI from a topic** (word list / monologue, split into Part 1, 2, 3…) **and owner-pasted lists** (AI only adds IPA, part of speech, meaning, example). |
| Length / format | **Shorts only, ≤ 1 minute, vertical 9:16.** A long topic becomes several parts (P1, P2…). |
| Look | **Beige paper + Daily Beyond English green** accents (title, part of speech, meaning card), bold black type. |
| Podcast content | **Short monologue on an everyday topic**, short easy sentences, opening like "welcome back to my slow English podcast". |
| Where | **Shorts batch (two new kind cards) and Step 1 / Channel plan**, like the other Short templates. |

## Phases

### Phase 1 (this request)
- Two new Short templates, keys `slowpod` (Slow English podcast) and `flashcards` (Vocabulary flashcards), as Solo voice-only Short styles beside Word of the day / Listening.
- **Slow podcast**
  - Script: a narrator monologue of ~8–10 short sentences (A2–B1), one sentence per line, opening with the "slow English podcast" greeting line and ending with a follow line; ≤ 1 min at the slow rate.
  - Each line carries its Vietnamese translation (`translation_vi`), written by the AI with the script and editable in Step 2.
  - Voice: the narrator's Edge voice at a slower rate for this style only.
  - Scene: one sentence per screen — large bold English (karaoke highlight of the spoken word), Vietnamese below, beige paper background, small logo; no characters.
- **Flashcards**
  - Data: a deck of 8–10 entries `{word, part_of_speech, ipa, meaning_vi, example?}` plus deck title / part number; from AI (topic) or a pasted list (AI completes the fields); long lists are split into parts.
  - Narration: the word twice per card (example sentence optional), a short title line on the cover card, a follow line at the end.
  - Scene: header pill (topic + part), "FLASHCARD TỪ VỰNG" tag, cover card, then card N/total with word, part of speech, IPA, green meaning card; cards slide in like a deck with neighbours peeking.
- Both: in the Shorts batch kind cards (topic → parts; or pasted list), in Step 1 Short templates and Channel plan; the Phase 80 short brand (no intro, 2 s end card, logo) and "Make videos now" apply; Vietnamese UI copy; silent preview on the batch page.
- Tests: script/deck validation (counts, ≤ 1 min estimate, translation present), renderer math (card timing, sentence pages), browser test of the batch kind cards, real renders of both in a sandbox.

### Phase 2 (not requested now — candidates)
- Vietnamese voice (Edge vi-VN) to read meanings / translations.
- 16:9 long slow podcast (10–20 min) for YouTube.
- Decks taken from an existing episode's lesson (Step 3).

## Technical notes (from the codebase)

- Fits the existing Solo Short pipeline: `SOLO_SHORT_STYLES` / `SHORT_STYLES` in `backend/schemas/project.py`, the Short prompt blocks in `backend/ai/prompts/script/solo_explainer.txt`, the explainer plan + `renderer/src/LearnScene.tsx`-style scenes, `sampleShort.ts` for the batch preview, `batch_service.TEMPLATES`.
- `source_kind = "vocabulary"` already parses owner word lists (`parse_vocabulary`) — reuse for pasted flashcard lists.
- New data: a per-line Vietnamese translation for `slowpod` (script line field or language notes) and a deck structure for `flashcards` (the learning pack's vocabulary already has `word`, `part_of_speech`, `ipa`, `definition_vi`, `example_sentence`).
- Voices are English-only (Phase 77, Edge); a per-style speed is needed for the slow podcast (the voice settings already carry speed).
- Phase 80's Short brand and line split apply automatically; the flashcard narration should not be split mid-card.

## Open questions

- Flashcards: include the example sentence by default, or only the word twice? (Default: word twice; example optional per deck.)
- Exact slow rate for the podcast (−15 % / −20 % / −25 %) — confirm after hearing a sample.

## Project meta intake (FEAT-009)

Waived: existing project with `.viepilot/PROJECT-META.md` and an established brand profile (Daily Beyond English); no new profile needed.

## Next step

`/vp-evolve` to add Phase 81 from this session, then `/vp-auto` to implement (doc-first plan commit, then tasks).
