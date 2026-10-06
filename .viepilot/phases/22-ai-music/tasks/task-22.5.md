# Task 22.5: Music credit line in the YouTube description (doc-first card)

## Objective

The YouTube description (Step 7: shown, copied and exported in `metadata.txt`) ends with a credit
line for the episode's real background music. The track is the one in the project's completed
audio job. The credit is added when the package is **read or exported**, never stored into the
AI-written text, so changing the music changes the credit without regenerating the package.

- When the track's details hold credit text: `🎵 Music: <credit text>`.
- Otherwise, the line is built from the details:
  `🎵 Music: "Title" by Artist — Source (Licence) <link>`. Missing parts are left out.
- No music, or no audio yet: no line. A description that already contains the exact line is not
  doubled.

## Paths

- `app/services/music_library_service.py` (`music_credit`)
- `app/services/youtube_service.py` (`with_music_credit`)
- `app/api/youtube.py`
- `frontend/static/js/step7_youtube.js` (show a "Music credit added" hint when present)
- `tests/test_music_credit.py` (new)

## File-Level Plan

1. **`music_credit(db, project_id)`:**
   - reads `audio_jobs.background_music` (status complete) and the track's details row;
   - returns the line or None;
   - a deleted track with no row still yields a title guessed from the filename.
2. **`with_music_credit(package, credit)`:** a pure function. It returns a copy with the
   description + a blank line + the credit, plus `music_credit`. It is idempotent.
3. **`api/youtube.py`:** GET, generate and export all apply it. The export's `metadata.txt` then
   carries the credit.
4. **Step 7:** a small note under the description when a credit was added.

## Verification

- Unit tests for the formats (attribution / built / partial / none / idempotent).
- API tests: GET and export include the line; changing the job's music changes it.
- The full suite is green.

## Results (done 2026-10-06)

- **Built as planned:**
  - `music_library_service.credit_line` / `music_credit`;
  - `youtube_service.with_music_credit` (pure, idempotent, never stored);
  - GET, generate and export apply it;
  - Step 7 shows "🎵 The music credit was added from the Music Library".
- **Tests:** `tests/test_music_credit.py` (3). The existing YouTube tests (54) are unchanged and
  pass.
- **Full suite:**
  - **First run:** `1077 passed, 337 errors` in 6:20, about half the usual time. It was run
    without `-rE`, so the error text was not kept.
  - **Rerun** of the unchanged code, with `-rE`: **1413 passed, 0 errors** (14:09).
  - A subset run in between also passed. The 337 errors were a transient environment failure
    (fixture setup errors, not test failures). Its cause is not determined.
