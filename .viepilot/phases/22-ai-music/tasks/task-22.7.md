# Task 22.7: Music Library track details: mood, tags, measured length, licence and credit (doc-first card)

## Objective

The owner downloads free tracks by hand and uploads them (D50). Each library track gets editable
details, so that auto-select (22.8) can match a topic and a length, and the credit line (22.5) can
credit the track:

- title, artist;
- **mood** (`lofi` | `acoustic` | `upbeat` | `calm` | `inspiring`) and **tags** (free words);
- source site, licence, attribution text, source URL;
- a **measured duration** (ffprobe), never typed by hand.

The page warns when a licence needs a credit and none is written. A short Vietnamese guide explains
where to download safe free music.

## Paths

- `app/db/migrations/012_music_library_meta.sql` (new)
- `app/models/music.py` (new)
- `app/services/music_library_service.py` (new)
- `app/api/music.py`
- `frontend/pages/music_library.html`
- `frontend/static/js/music_library.js`
- `frontend/static/js/api.js`
- `docs/user/free-music-sources.md` (new)
- `tests/test_music_api.py`
- `tests/test_music_meta.py` (new)
- `tests/test_music_meta_browser.py` (new)

## File-Level Plan

1. **`012_music_library_meta.sql`** (additive) creates the table `music_tracks`:
   - `filename` PK;
   - `title`, `artist`, `mood`, `tags`;
   - `source`, `licence`, `attribution`, `source_url`;
   - `duration_s`, `created_at`, `updated_at`.
   - Files on disk stay the source of truth for the listing. A file with no row gets one lazily.
2. **`app/models/music.py`:**
   - `MOODS` with labels;
   - `SOURCES`: youtube_audio_library, pixabay, mixkit, incompetech, free_music_archive, other;
   - `LICENCES`, each with a label and an `attribution_required` flag:

     | Licence | Credit required |
     |---|---|
     | `youtube_audio_library` | no |
     | `youtube_audio_library_attribution` | yes |
     | `pixabay` | no |
     | `mixkit` | no |
     | `cc0` | no |
     | `cc_by_4` | yes |
     | `other` | owner decides |

   - `MusicTrackPatch`:
     - all fields optional;
     - extra fields forbidden;
     - text is stripped, with length caps;
     - `source_url` must be http(s);
     - tags are normalised to lower-case, comma-separated and deduplicated.
3. **`music_library_service.py`:**
   - `probe_duration(path)`: ffprobe, next to `FFMPEG_PATH`, with a timeout. It returns None on
     failure.
   - `guess_title(filename)`: "calm_morning-piano.mp3" → "Calm morning piano".
   - `ensure_rows(db, files)`: inserts missing rows with the guessed title and the measured
     duration, and fills a NULL duration.
   - `rows_by_filename`, `patch_track`, `delete_row`.
   - `track_view(file, row)` adds a `needs_attribution` warning flag.
4. **`api/music.py`:**
   - the list returns the details. Missing rows are created in a write transaction, and the
     probing runs off the event loop.
   - upload creates the row (title guess + duration).
   - `PATCH /api/music/{filename}` edits the details (404 for a missing file).
   - delete removes the row.
5. **Library UI:**
   - each card shows the title, artist and mood badge, the length (m:ss), the licence, and a
     "Credit needed" warning when it applies;
   - an "Edit details" button opens an inline form (mood, title, artist, tags, source, licence,
     attribution, URL) with Save / Cancel;
   - the licence select shows whether a credit is required;
   - a link to the guide.
6. **`docs/user/free-music-sources.md`** (Vietnamese): YouTube Audio Library, Pixabay Music,
   Mixkit, Incompetech (CC BY 4.0, with the credit format) and Free Music Archive. For each:
   - how to download;
   - the licence;
   - whether a credit is needed;
   - the Content ID caveats (keep the download page link);
   - avoiding NC/ND licences for a monetised channel.
   - It also covers how to fill in the details here.

## Best practices

- Additive migration.
- Writes inside `write_transaction`.
- ffprobe in `asyncio.to_thread` with a timeout.
- Never trust a typed duration.
- No new dependencies.
- The existing upload and delete safety behaviour (magic bytes, no overwrite, path guards) stays
  unchanged.

## Verification

- New and updated tests:
  - lazy rows + real ffprobe duration on a generated MP3;
  - title guess;
  - PATCH validation;
  - attribution warning;
  - upload/delete keep the rows in step;
  - browser: edit and save the details, the warning shown and cleared.
- The full suite is green.
- **Visual check** with screenshots of the Library page.

## Results (done 2026-10-06)

- **Built as planned.**
  - Every library file gets a `music_tracks` row lazily, with a guessed title and an ffprobe
    duration.
  - `PATCH /api/music/{filename}` edits the details: only the fields sent change, and an empty
    value clears.
  - `GET /api/music/options` lists the choices.
  - Upload and delete keep the rows in step.
- **Library UI:**
  - each card shows the title (and artist), the file and size, a length badge, the mood (or "No
    mood yet"), the licence, and "⚠ Credit needed";
  - an inline "Edit details" form;
  - an in-page "Where to find free music safely" summary. A link to GitHub was dropped, since the
    repo may be private and the doc is not on main yet.
- The guide is `docs/user/free-music-sources.md` (Vietnamese).
- **Tests:**
  - `tests/test_music_meta.py` (13, with real ffprobe on generated MP3s);
  - `tests/test_music_meta_browser.py` (2);
  - `test_music_api.py` and `test_music_library_browser.py` updated for the title-first card.
  - **Full suite: 1380 passed.**
- **Visual check:** a screenshot of the Library showed two generated tracks, the badges, the
  warning and the open form.
- **Known limit:** a file ffprobe cannot read keeps `duration_s` NULL and is re-probed on each
  listing. This is cheap, since the failure is fast.
