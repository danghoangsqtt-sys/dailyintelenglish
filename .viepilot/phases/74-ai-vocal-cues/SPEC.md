# SPEC — Phase 74: AI vocal cues and expressive Edge TTS

Source: [owner decisions D1–D4](../../../docs/brainstorm/session-2026-10-23-tts-emotion.md). Planned 2026-10-23. This is a plan, not an implementation or acceptance record.

## Goal

AI-generated English dialogue arrives with occasional, context-appropriate vocal directions. The selected Edge voice renders them as audible approximations. Editors can change or remove cues in Step 2; captions, transcripts and learning material contain only dialogue.

## Requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R74-01 | AI may insert 0–2 cues per minute, never forced; avoid inappropriate laughter or repeated events. | Structured annotation plan, quota/context validation and reviewed sample scripts. |
| R74-02 | Annotation cannot alter spoken words, speaker IDs, language notes, CEFR validation or script budget. | Compare clean script before/after stripping cue tags; checkpoint and repair behavior retained. |
| R74-03 | Existing `[cười]`, `[thở dài]`, `[hắng giọng]` keep working; add editable `[cười:ha-ha]` and `[cười:hi-hi]`. | Parser and editor compatibility review. |
| R74-04 | A laugh variant uses the selected speaker voice; sigh/ahem are short; ahem lowers the following short clause then restores configured pitch. | Real voice listening matrix, measured audio and word timing evidence. |
| R74-05 | Save and Listen preview the latest script, and failed optional annotation leaves clean dialogue usable. | Browser and worker failure/restart scenarios. |
| R74-06 | Cues never leak to captions, karaoke text, learning or YouTube outputs; WordBoundary timing remains aligned. | Mix/SRT/transcript inspection and measured boundary checks. |
| R74-07 | Changing cue recipes invalidates relevant cached audio without changing unaffected lines. | Cache fingerprint and stale-completion checks. |

## Boundaries

- Edge TTS remains the sole TTS engine; no Azure key or local TTS model is added.
- These cues are phonetic/voice approximations. Natural nonverbal laughter or sighing is not guaranteed by Edge TTS.
- No schema migration or new settings toggle is required for the first version. If implementation discovers a durable data need, amend this plan before code changes.
- No EXE/release publication in Phase 74 planning; owner listening approval and packaging are separate gates.

## Delivery gates

1. Parse and render all old/new tags; one untagged line retains its existing synthesis path.
2. Annotate only after the validated script is final, outside database write locks, with final staleness/cancellation recheck before publication.
3. Preserve a valid script when optional annotation fails; record a visible/traceable warning.
4. Manual listening on representative pinned voices and accents; document failed pronunciations and chosen fallbacks before owner review.
