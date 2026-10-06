# Task 27.3a: Music Library: add many tracks at once, clearer listening

## Owner request (2026-10-06)

"Add the function to add background music and to listen to it (preview)" on the Music Library page.

## What exists and what is missing (read from the code and checked on the live page)

- The page already has an upload zone and a player (`<audio controls>` + waveform) on every track.
- **Missing 1:** the zone uploads **one file at a time**: `input.files[0]` and `dataTransfer.files[0]` mean that
  choosing or dropping several files uploads only the first, silently. The owner downloads tracks in batches.
- **Missing 2:** only `.mp3` and `.wav` are accepted for upload, although the library listing already supports
  `.ogg` and `.m4a` (`AUDIO_EXTENSIONS`); the page says "MP3 or WAV".
- **Missing 3:** listening means using the small native control of each card; nothing stops several tracks
  playing together, and there is no obvious Play button.

## Plan

1. **Many files at once** (`music_library.js`, `music_library.html`): the input gets `multiple`; choosing or
   dropping N files queues them and uploads **one after another** (the API stays one file per request). A
   queue panel shows each file with its state (waiting, uploading, added, skipped with the reason: wrong type,
   empty, over 50 MB, duplicate name kept, error). One summary line at the end ("3 added, 1 skipped"). A
   failure of one file does not stop the others. The list is reloaded once at the end.
2. **More formats:** the API accepts `.ogg` and `.m4a` too (`UPLOAD_EXTENSIONS`, with their signatures: `OggS`
   for ogg, `ftyp` at byte 4 for m4a, checked like the MP3/WAV signatures) and the page text and the file
   input say "MP3, WAV, OGG or M4A". Files already in the folder are unchanged.
3. **Listening:** each track card gets one clear **Play / Pause button** (large, with the title as its
   accessible name) beside the waveform; starting a track **pauses every other** track (one at a time); the
   waveform stays clickable to seek. The existing `<audio>` element stays the single player of the card, so the
   waveform code and the tests that use it keep working.
4. **Tests:**
   - API (`tests/test_music_api.py`): an `.ogg` and an `.m4a` with the right signature upload, a fake one with the
     wrong signature is refused, `.flac` is refused with the new message;
   - browser (`tests/test_music_upload_multi_browser.py`): choosing 3 valid files adds 3 tracks; a mixed batch
     (valid, wrong type, empty) shows the right states and the summary and still adds the valid ones; the
     input is `multiple`; playing track B pauses track A; the Play button toggles `aria-pressed`/label;
   - the existing music browser tests run unchanged (`test_music_library_browser`, `..._waveform_...`,
     `test_music_meta_browser`).

## Paths

- `app/api/music.py`
- `frontend/pages/music_library.html`
- `frontend/static/js/music_library.js`
- `frontend/static/js/api.js`
- `tests/test_music_api.py`
- `tests/test_music_upload_multi_browser.py` (new)

## Verification

- New and existing music tests green; then the full suite (about 18 minutes).
- On the live page: upload 3 real MP3 copies from a temp folder (a throw-away copy of the data folder, never
  the real `data/music_library`), see the queue and the summary, play two tracks and see the first pause.
  Screenshots looked at.

## Out of scope

The grid + detail-panel layout of the library (that is Task 27.3b together with characters and scenes), a global
mini-player, and the music auto-selection logic.

## Implementation notes (2026-10-06)

- Done as planned: `UPLOAD_EXTENSIONS` + OGG/M4A signatures and the new message in `app/api/music.py`; the zone takes
  many files (`multiple`), a per-file queue (waiting / uploading / added / skipped / not added, with the reason or
  "saved as <name>" for a renamed duplicate), one summary line; one round, one list reload; a single file keeps its
  old messages and has no queue.
- Listening: one round Play/Pause button per track (red while playing), `aria-pressed` and "Play/Pause <title>"
  labels, and starting a track pauses the others; the `<audio>` element and the waveform are unchanged.
- Tests: 3 API (ogg and m4a stream back, spoofed ones refused, the message) and 7 browser
  (`tests/test_music_upload_multi_browser.py`); all 12 existing music browser tests pass unchanged.
- Screenshot on a throw-away instance with three real tracks and one wrong file:
  `docs/operations/ui-audit/music-27-3a.png`. The real library was not touched.
