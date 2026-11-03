# Task 91.1 — Step 2 keeps unchanged voices

## Design (written before code)

`script_service.save_script` today deletes every line and inserts new ones (new ids, no audio cache), so one edited line
makes the whole Short's voice again. It will match the saved lines to the current ones by position: a line whose
speaker and text are unchanged keeps its id, `audio_cache_path` and `duration_seconds`; others get a new id and no
cache (as today). Language notes are written as given. Step 4's "Generate all" then synthesizes only the lines without
a matching cache (`tts_service.cache_matches`). Callers that rely on fresh ids (AI script jobs) are unchanged in effect:
an AI script normally changes every line.

## Paths

`backend/content/script_service.py`, `tests/test_script_keeps_voices.py` (new).

## Verification

`pytest tests/test_script_keeps_voices.py tests/test_projects_api.py tests/test_script_pipeline.py -q`.
