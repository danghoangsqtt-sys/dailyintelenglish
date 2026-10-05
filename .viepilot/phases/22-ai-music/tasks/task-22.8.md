# Task 22.8: Auto-select a library track by topic and length (D51, doc-first card)

## Objective

In Step 4, the music dropdown gains **"✨ Auto (best match)"**. It is the default whenever the
library has tracks.

- The app picks the track that best fits the episode's **topic** (genre → mood, topic words →
  tags/title, then an AI choice among the top candidates) and **length** (a track that covers the
  whole video beats one that must loop, and fewer loops are better).
- It avoids repeating the music of the last episodes.
- The pick and a one-line reason are shown before generating, and the owner can still choose any
  track or None.
- Generate sends the concrete filename, so the audio job, the video and the credit line all use
  the real file.

## Paths

- `app/models/music.py`
- `app/services/music_select_service.py` (new)
- `prompts/music/music_pick.txt` (new)
- `app/core/prompt_loader.py`
- `app/api/music.py`
- `frontend/pages/step4_tts.html`
- `frontend/static/js/step4_tts.js`
- `frontend/static/js/api.js`
- `tests/test_music_select.py` (new)
- `tests/test_music_auto_browser.py` (new)

## File-Level Plan

1. **`app/models/music.py`:** `GENRE_MOODS`, an ordered list of preferred moods for each of the 10
   genres. Example: interview → acoustic, lofi, calm.
2. **`music_select_service.py`:**
   - **`target_seconds(project, audio_job)`:**
     - the real mix length when the audio exists, else the planned minutes;
     - plus the Enhanced intro + outro (7.5 s), the longest video either renderer makes.
   - **`score(track, project, target, recent)`:**

     | Part | Points |
     |---|---|
     | mood rank | 3 / 2 / 1, 0 if the mood is unknown or other |
     | topic words found in tags/title | +1 each, at most 3 |
     | length: covers the video | +2 |
     | length: must loop | −0.5 per extra loop, at least −1 |
     | used by one of the last 3 audio jobs of other projects | −1.5 |

     A track with an unknown length gets −2. Each score returns its parts, so the reason can be
     explained.
   - **`suggest(db, project_id, router)`:**
     - ranks every library track (details from 22.7);
     - with ≥2 candidates, asks the AI once to choose among the top 5. The AI sees the topic,
       genre, level, and each candidate's title, mood, tags and length.
     - The answer must be one of the candidate filenames, else one repair, else the top score.
     - AI I/O runs outside any transaction.
     - It returns `{filename, title, reason, path: ai|ai_repaired|rule|single|none, target_s,
       candidates[top 5 with score parts]}`.
3. **`prompts/music/music_pick.txt`** asks for JSON `{"filename", "reason"}`, with a reason of at
   most 20 words.
4. **API:** `POST /api/projects/{id}/music/suggest`. It returns a 404 for an unknown project, and
   `path: none` for an empty library.
5. **Step 4:**
   - The dropdown is ordered: Auto, None, then the tracks. Labels show the title, mood and length.
   - When Auto is selected, the app fetches the suggestion and shows "Auto pick: Title (mood,
     m:ss): reason" under the dropdown.
   - Generate sends the picked filename. If the suggestion failed or the library is empty, Auto
     falls back to None, and the line says why.
   - The timeline's music lane shows the picked title.

## Best practices

- The storyboard and brief pattern for the AI: validated against a closed set, one repair,
  deterministic fallback, FakeProvider in tests.
- The scoring is pure and unit-tested.
- The audio API is unchanged: it still receives a filename.

## Verification

- Unit tests:
  - mood, topic, length and recency parts;
  - the empty library;
  - a single track (no AI call);
  - AI pick, invalid pick → repair → rule.
- Browser: Auto is the default with tracks; the pick line is shown; Generate sends the picked
  filename; None and a manual pick still work.
- The full suite is green.
- **Real check** on the real project with real Gemini and a few library tracks.

## Results (2026-10-06)

- **Built as planned.**
  - `music_select_service.score` (pure; mood / topic / length / recent parts) and
    `suggest` (AI among the top 5, one repair, rule fallback; `single` with one track, `none` for
    an empty library).
  - `POST /api/projects/{id}/music/suggest`.
  - Step 4:
    - Auto is the default with tracks;
    - an "Auto pick: Title (mood, m:ss) — reason" line;
    - track labels show title, mood and length;
    - the timeline shows "✨ Title";
    - Generate waits for the pick and sends its filename.
- **Refactor:** the library listing and details moved from `api/music.py` into
  `music_library_service` (`list_tracks`), so the selector does not import the API layer. The API
  keeps thin aliases, and `test_music_api` is unchanged.
- **Fix found by reading the output:** the rule reason said "suits a interview episode". It now
  reads "suits interview episodes".
- **Real check:** real Gemini on 3 real projects (DB copy) with 5 library tracks carrying
  owner-style details. Each pick took 8.6–11.4 s, including one Gemini backoff.
  - "The best way to start your morning" (small_talk) → morning_coffee: "acoustic tone and morning
    theme".
  - "What do you have in your evening?" (interview) → quiet_night: "calm mood … evening routines
    at home".
  - "The rise of remote work…" (interview) → big_dreams: "inspiring tone … work and career".
    This 150 s track loops ~4× for the 487 s video. The AI weighs topic over length; the owner
    can override.
- **Tests:**
  - `tests/test_music_select.py` (9);
  - `tests/test_music_auto_browser.py` (2);
  - the existing Step 4 browser tests (8) still pass.
- **Full suite: 1410 passed** (2026-10-06).
