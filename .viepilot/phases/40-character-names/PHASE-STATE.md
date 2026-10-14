# PHASE-STATE — Phase 40: Character names follow the chosen profile (D119)

- **Status:** ✅ complete 2026-10-14 (full suite 1,694 + 7 updated browser tests). Opened 2026-10-14 (owner: "đã lựa chọn cơ chế nhân vật theo profile rồi mà lại cố định 2 cái tên Alex và
  Lina — đáng lẽ phải là Character 1 và Character 2, và sau khi chọn thì dùng tên của nhân vật đó trong video luôn").

| Task | Description | Status |
|---|---|---|
| 40.1 | Step 1 and the channel plan: no Alex/Lina preselection; slots read "Character 1..N" until a profile is chosen | done |
| 40.2 | Backend `rename_speaker`: the speaker takes the character's name and the old name is replaced in the script lines; the project is marked "script changed" (audio to redo); used by the Step 5 cast change and by the speaker rename | done |
| 40.3 | Step 5 notice after a rename; generic hints in Step 5 and the Shot Library; tests | done |

## Implementation notes (before coding)

- Found: `step1_config.js` `preselectDefaults` picks the profiles named "Alex"/"Lina" for every new project; `channel.js`
  preselects them for the plan; Step 5 keeps the speaker's old name after a cast change (only a manual "Use character name"
  button, which renames the label but not the dialogue nor the audio).
- 40.2: `project_service.rename_speaker(db, project_id, speaker_id, new_name)` — case-sensitive whole-word replacement of the
  old name in this project's `script_lines.text` (possessives keep working), rename the speaker row, then
  `mark_script_changed` when anything changed (truthful status: audio and video are stale). `visuals.set_cast` calls it for
  each member whose speaker name differs from the character's; `PATCH /speakers/{id}` routes a name change through it.
  The response reports the renames so Step 5 can say "names changed in N lines — regenerate the audio in Step 4".
- Tests: rename + replacement + status downgrade; cast change renames; no-op when names match; Step 1 has no preselection.

## As built

- Step 1 / channel plan: no preselection, "Character N" slots; `project_service.rename_speaker` (whole-word, case-sensitive,
  script lines + speaker row, `mark_script_changed` only when a script exists); `set_cast` renames and reports `renamed`;
  `PATCH /speakers/{id}` accepts `name` (it was silently ignored before — the Step 5 "Use character name" button never
  saved); Step 5 shows "Renamed X → Y in N lines — regenerate the audio in Step 4"; generic hints.
- Tests: `tests/test_phase40_character_names.py` (4) + 7 browser tests updated to the new behaviour.
