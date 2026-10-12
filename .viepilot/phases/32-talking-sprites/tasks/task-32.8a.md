# Task 32.8a: Prefer the speaking character's activity pictures (BUG-029, D76)

## Why

Gate B-22 (2026-10-12): the Demo Episode used only generic pictures although 25 approved pictures each exist for Alex and
Lina. Both callers pass a character to `activity_matcher.match_activity` only when `beat.speakers` holds exactly one index,
and the storyboard AI sets `speakers: []` for inserts (prompt rule for objects, places and crowds) — all three Demo inserts.

## Plan

- New shared helper (in `app/services/visuals/activity_matcher.py`, pure): `beat_character_id(beat, lines, cast_by_index,
  speaker_index_of_line)`:
  1. `beat.speakers` has exactly one index → that cast member (unchanged behaviour).
  2. Otherwise the speaker(s) of the beat's lines `line_from..line_to`: one distinct speaker → that character.
  3. Two speakers → the speaker of the line whose text contains the beat's action words (same `_contains` rule as
     scoring); if none or several do, the speaker of the first line.
  4. No cast mapping → `None` (generic only, as today).
- Use the helper in both callers so render and Step 5 coverage agree:
  `app/services/video_renderer_remotion.py` (sprite props builder, ~line 357) and `app/api/visuals.py` (~line 508).
- Matcher scoring and the rule "a character picture beats a generic one, the other character's pictures never match" stay.
- No prompt change: `speakers: []` keeps meaning "no person drawn on screen" for the old storyboard image path.

## Paths

- `app/services/visuals/activity_matcher.py`
- `app/services/video_renderer_remotion.py`
- `app/api/visuals.py`
- `tests/test_activity_library.py`

## Verification

Unit tests: an empty-`speakers` beat on an Alex line about stretching picks Alex `exercise`; a Lina line picks Lina's
picture; no character picture for the action → generic; a two-speaker beat follows rule 3; Lina's pictures are never
chosen for Alex. Coverage endpoint test shows the same choice. Full suite + Ruff.
