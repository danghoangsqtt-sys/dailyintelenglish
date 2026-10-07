# Phase 29, Task 29.2: inserts with a character (ENH-020)

Owner feedback (Gate B-20): the illustration shots should be able to show a character.

**Cause:** the storyboard already allowed `speakers` on an insert beat, but the render ignored it: every insert was plain
text2img with no face reference, so a person in it was a stranger.

**Fix:** an insert that names a cast speaker is drawn in a second text2img session with that character's face
(IP-Adapter, scale 0.5, the character sheet's recipe), a prompt with the character's identity, locked outfit and the action
(`recipes.insert_person_prompt`, within the 77-token budget), and `negative_for(character)`. An insert with no speaker is
unchanged. The storyboard prompt now tells the AI to name the speaker when a person does the thing (phone, oatmeal,
stretching) and to leave `speakers` empty only for objects, places and crowds.

**Real run** (data copy, three Gate B-20 inserts, speakers set, only those regenerated): `docs/operations/phase29-inserts.png`.
Minh (all black) checks a phone, Lan (all white) stretches by a window and eats oatmeal. Outfits and faces are right; the
man looks at the lens in the phone insert, which is natural for a portrait insert.

Tests: `tests/test_visuals_inserts_character.py` (2), storyboard shot and propose suites green.
