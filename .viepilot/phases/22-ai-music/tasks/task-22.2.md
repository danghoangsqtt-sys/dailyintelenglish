# Task 22.2: music worker, engine, jobs, `music_tracks` provenance, Library UI v2 (doc-first card)

## Objective

The Music Library can generate an instrumental track from a style family plus a short brief, using
ACE-Step 1.5 in its own worker process under the GPU lease. Every track records where it came
from:

- an AI track records its style, brief, caption, seed, duration, model and licence;
- an uploaded track is recorded as an upload.

The Library page shows this, and it offers a standalone **Generate from a brief** form. Project
wiring (the AI brief and Step 4 previews) is Task 22.3; loudness and ducking are Task 22.4.

## Assumption while 22.1 awaits the owner's ears

The length strategy and the LM mode are **settings**, not code paths baked in:

- `MUSIC_LENGTH_STRATEGY="full"` (generate the whole length in one piece);
- `MUSIC_LM="none"` (DiT-only).

These defaults are Claude's spike recommendation. If the owner picks "loop" or an LM, only the
defaults change. In either strategy, a request longer than ACE-Step's 600 s limit is always made
by looping a segment with 3 s equal-power crossfades, which is the spike's `loop_with_crossfade`.

## Paths

- `app/db/migrations/012_music_tracks.sql` (new)
- `scripts/music_worker.py` (new; runs in `venv-music`)
- `app/services/music/__init__.py` (new)
- `app/services/music/engine.py` (new)
- `app/services/music/tracks.py` (new)
- `app/services/music/pipelines.py` (new)
- `app/core/config.py`
- `app/main.py`
- `app/api/music.py`
- `app/models/music.py` (new)
- `frontend/pages/music_library.html`
- `frontend/static/js/music_library.js`
- `frontend/static/js/api.js`
- `tests/test_music_api.py`
- `tests/test_music_generate.py` (new)
- `tests/test_music_generate_browser.py` (new)

## File-Level Plan

1. **`012_music_tracks.sql`** (additive). It creates the table `music_tracks`:
   - columns:
     - `filename TEXT PRIMARY KEY` (the library file name, unique in the folder);
     - `source` (`upload` | `ai`), `style`, `brief`, `caption`, `seed`, `duration_s`, `model`,
       `licence`, `strategy`, `job_id`, `created_at`.
   - Files on disk stay the source of truth for the listing. A file with no row is shown as
     `source: "upload"` with no provenance, which covers every track uploaded before this task.
2. **`scripts/music_worker.py`.** It uses the same line-delimited JSON protocol as
   `image_worker.py`:
   - stdout isolation;
   - a `ready` / `unavailable` handshake, where a CPU-only torch build is reported as
     unavailable;
   - one response per request; a bad request never kills the worker.
   - Commands:
     - `load {lm}`: DiT turbo, plus the optional 0.6B or 1.7B LM in metadata-only mode, offloaded
       to the CPU, as measured in 22.1;
     - `generate {caption, duration_s, seed, strategy, output_path}`: writes a WAV;
       - `full` makes the whole length in one piece when it is ≤600 s;
       - otherwise, a segment of `min(150, duration)` s is made and looped with crossfades;
     - `stats` and `unload`.
   - Every response reports the wall time and the torch peak VRAM.
3. **`app/services/music/engine.py`:**
   - `WorkerMusicEngine`:
     - takes `get_gpu_manager().lease("music", min_free_mb=GPU_MIN_FREE_MB_MUSIC)`;
     - runs one worker per session and kills it if it hangs. This mirrors `visuals/engine.py`.
   - `FakeMusicEngine` writes a deterministic short sine WAV with the stdlib `wave` module, with
     the worker's response shape and no GPU.
   - `generation_available()` and `require_generation()` raise a `ConflictError` when the feature
     is disabled or `venv-music` is missing.
4. **`app/services/music/tracks.py`** handles the provenance rows: `record_upload`, `record_ai`,
   `rows_by_filename`, `delete_row`.
   - It also has `place_without_overwrite`, moved from `api/music.py` so the pipeline and the
     upload use one helper.
5. **`app/services/music/pipelines.py`** registers the `music_track` job handler on the
   existing `ImageJobRunner`. A single runner serialises all GPU work.
   - Steps:
     - boundary;
     - engine session → generate a WAV in `DATA_DIR/music_library/.work/`;
     - ffmpeg → MP3 192k (an 8-minute WAV is 184 MB);
     - place the MP3 in the library without overwriting;
     - `record_ai`;
     - clean up the work files, which also happens on failure.
   - The filename is `<style>-<slug of the brief>-<seed>.mp3`, or `<style>-<seed>.mp3` when there
     is no brief.
6. **`app/models/music.py`:**
   - `MUSIC_STYLES`: the three D49 families, each with the spike's base caption.
   - `MusicGenerateInput`:
     - `style` must be one of the three families;
     - `brief`: ≤200 characters, stripped;
     - `duration_s`: 10–1200;
     - `seed`: optional, 1..2³¹−1;
     - extra fields are forbidden.
7. **`app/api/music.py`:**
   - `GET /api/music/options` (styles, limits, whether generation is available);
   - `POST /api/music/generate` enqueues a job;
   - `GET /api/music/jobs/{id}` and `POST /api/music/jobs/{id}/cancel`, which only accept
     `music_track` jobs;
   - the list includes `source` + `provenance`; upload records `upload`; delete removes the row.
   - The new routes are declared before the `/{filename}` routes.
8. **`config.py`:**
   - `AI_MUSIC_ENABLED=True`, `MUSIC_ENGINE` worker|fake;
   - `MUSIC_LENGTH_STRATEGY` full|loop, `MUSIC_LM` none|0.6B|1.7B;
   - `GPU_MIN_FREE_MB_MUSIC=8192`: the measured whole-card peak was 7.4–8.4 GB, including about
     0.5 GB of desktop use, and the lease evicts Ollama first.
9. **`main.py`** registers the handler.
10. **Frontend (Library UI v2):**
    - each card shows a source badge (AI / Uploaded); an AI card also shows its style, brief,
      length, seed and model + licence;
    - a "Generate from a brief" panel: style select, brief, length (minutes:seconds) and
      Generate;
    - the panel shows progress by polling the job, has a cancel button, and reloads the list when
      the job is done;
    - the panel is hidden or disabled with a reason when generation is unavailable.

## Best practices

- Same patterns as Phase 20:
  - doc-first;
  - fake engine in tests;
  - writes inside `write_transaction`;
  - blocking IO in `asyncio.to_thread`.
- No new dependencies in the main venv (`wave`/`math` only).
- Never overwrite a library file.
- The worker never keeps VRAM after its lease.
- Real runs use a copy of the DB, never `data/app.db`.

## Verification

- `pytest tests/test_music_api.py tests/test_music_generate.py tests/test_music_generate_browser.py`
  is green, and so is the full suite.
- **Real run** (worker engine, isolated `DIE_DATA_DIR`): one 60 s track and one 900 s track,
  where 900 s exercises the loop path. Each lands as an MP3 in the library with a provenance row.
  Record the wall time, VRAM and a "no vocals" spot check.

## Results (done 2026-10-05)

- **Worker driven directly over its protocol** on the RTX 3060. Every branch was checked:
  - bad command; generate before load;
  - load, reload of the same LM, switch to the 0.6B LM, unknown LM;
  - full 20 s; loop 200 s;
  - stats; unload, which falls back to 8 MB allocated.
  - No `.raw-*` work folders are left behind.
- **Real run through the API** (worker engine, isolated temp `DATA_DIR`; `data/app.db` not touched):

  | Request | Job wall time (incl. model load) | Generation | Torch peak | Result |
  |---|---|---|---|---|
  | acoustic, 60 s, seed 11 | 27.1 s | 5.4 s | 6.5 GB | MP3 1:00.00, 48 kHz stereo 192k, strategy `full` |
  | lofi, 900 s, seed 12 | 45.1 s | 13.0 s | 6.5 GB | MP3 15:00.00, strategy `loop` (over the 600 s limit) |

  - Both tracks got provenance rows (`ai`, model `ACE-Step 1.5 acestep-v15-turbo (lm none)`, MIT).
  - GPU memory was back to ~0.7 GB after each job, so the worker had exited.
  - The MP3s were copied to `data/tmp/music-spike/app_*.mp3` for the owner to listen to.
  - The "no vocals" check is the owner's listen (22.1 owner actions). Claude cannot hear the audio.
- **Tests:**
  - `tests/test_music_generate.py` (16) and `tests/test_music_generate_browser.py` (3) are new.
  - In `tests/test_music_api.py`, the list payload now carries `source` + `provenance`.
  - The full suite collects 1384 tests and reports no failures.
- **Visual check:** screenshots of the Library at desktop and narrow widths. After the first look
  the generate panel was left-aligned.
- **Deviations:**
  - There is no `app_version` provenance column: the app has no Python version constant. The model
    id + licence + job id are recorded instead.
  - `pytest.ini` gained `testpaths = tests`. Without it, a bare `pytest` collected the ACE-Step
    checkout under `models/music/` and stopped on its missing `loguru`.
