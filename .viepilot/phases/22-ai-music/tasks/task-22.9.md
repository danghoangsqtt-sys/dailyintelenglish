# Task 22.9: Automatic track classification (pace, tempo, energy) + rhythm-aware auto-select (doc-first card)

## Owner request (2026-10-06)

> "Tôi đã bỏ nhạc tải từ Pixabay vào … music_library … có thể thêm cả tính năng phân loại nhạc để
> tạo một thuật toán chọn nhạc tự động phù hợp với thời lượng và nhịp điệu của chủ đề"
> — then "OKEY" to the proposal (tempo/energy analysis with librosa, a mood suggestion, rhythm
> matching per topic).

## Spike (`scripts/spike_music_analysis.py`, the owner's 6 Pixabay tracks)

- **librosa is already in the main venv.** It takes ~0.5 s per track (a 90 s window); the first
  call takes ~10 s to import.
- **BPM is ambiguous.** The same track gives 83 or 123 (2:3), and 74 or 144 (2×), depending on the
  tempo prior. A known limit of automatic tempo, so BPM is **shown as an estimate only**.
- **Onset density is stable:** two different 60 s windows of one track agree within ±0.3/s. It
  separates the tracks in line with their names:

  | Track | Onsets/s |
  |---|---|
  | nastelbom corporate-upbeat | 7.3 |
  | cinematic-soul upbeat | 6.3 |
  | corporate background | 4.7 |
  | corporate | 4.4 |
  | motivation | 4.3 |
  | news intro | 3.9 |

  So **pace** (calm / medium / lively) is classified mainly from onset density.

## Objective

Each library track is **analysed automatically**:

- pace (calm / medium / lively);
- an estimated BPM;
- energy (RMS dB);
- brightness (spectral centroid);
- a **suggested mood** shown as "(auto)".

The owner's own mood choice always wins, and pace can be overridden.

Auto-select (22.8) adds a **rhythm** part: each genre has preferred paces. For example, small talk
and directions are lively/medium; news, informational and opinion are calm/medium. The AI prompt
sees each candidate's pace and BPM.

## Paths

- `app/db/migrations/014_music_analysis.sql` (new)
- `app/services/music_analysis.py` (new; librosa imported lazily)
- `app/services/music_library_service.py`
- `app/models/music.py`
- `app/api/music.py`
- `app/services/music_select_service.py`
- `prompts/music/music_pick.txt`
- `frontend/static/js/music_library.js`
- `frontend/pages/music_library.html`
- `tests/test_music_analysis.py` (new)
- `tests/test_music_select.py`
- `tests/test_music_meta.py`
- `scripts/spike_music_analysis.py` (spike, kept)

## File-Level Plan

1. **Migration 014** adds to `music_tracks`:
   - `bpm`, `onset_rate`, `energy_db`, `brightness_hz`;
   - `pace` (auto or owner);
   - `pace_source` (`auto` | `owner`);
   - `mood_auto`, `analysed_at`.
2. **`music_analysis.analyse(path)`** (blocking):
   - mono 22 050 Hz, a 90 s window from the middle;
   - onset rate, tempo (default prior), RMS dB, median centroid;
   - pure `classify_pace(onset_rate)` with thresholds calm < 4.2 ≤ medium < 5.8 ≤ lively
     (calibrated on the spike);
   - pure `suggest_mood(pace, brightness, energy)`:

     | Pace | Brightness | Suggested mood |
     |---|---|---|
     | lively | bright | upbeat |
     | lively | not bright | inspiring |
     | medium | bright | inspiring |
     | medium | darker | acoustic |
     | calm | darker | lofi |
     | calm | otherwise | calm |

   - Unreadable audio → `None`.
3. **Service + API:**
   - `POST /api/music/analyse` analyses every track with no `analysed_at` (in a thread) and
     returns the updated list.
   - Upload does not block on analysis. The page calls `analyse` after rendering when a track
     still needs it.
   - The details PATCH accepts `pace`, which sets `pace_source=owner`. An empty value returns it
     to auto.
   - The track view adds `effective_mood` (the owner's mood or `mood_auto`), `mood_is_auto`,
     `pace`, `bpm` and `energy_label`.
4. **Auto-select:**
   - `GENRE_PACES`: the preferred paces, best first;
   - a `rhythm` score part: 2 / 1 / 0;
   - the mood score uses `effective_mood`;
   - the rule reason mentions the pace;
   - the prompt lines add the pace and "~N BPM".
5. **Library UI:**
   - badges for pace ("Lively"), "~123 BPM" and the mood (with "auto");
   - an "Analysing tracks…" note while the analyse call runs;
   - the details form gains a Pace select (Auto / Calm / Medium / Lively).

## Verification

- **Unit tests:**
  - pace thresholds and the mood rules;
  - analysis of synthetic click tracks (a known onset rate gives the expected pace; silence or
    garbage gives `None`).
- **API tests:** `analyse` fills the rows once, an owner pace or mood wins, and the scoring rhythm
  part works.
- Browser tests: badges and the analyse flow.
- The full suite is green.
- **Real check:**
  - the owner's 6 Pixabay tracks are classified, and the table is recorded;
  - auto-select on 3 real projects of different genres (real Gemini);
  - the owner reviews the pace labels.

## Progress (2026-10-06, paused at the usage limit)

- **Done and committed:** commits `abb6d79`, `8d0d006` and the loop-penalty fix.
  - Analysis (median of three windows; an absolute onset floor stops steady tones reading as
    medium).
  - `POST /api/music/analyse`.
  - Owner pace/mood override.
  - Rhythm score.
  - Library badges, updated in place (no playback reset).
  - Music tests 45/45, twice.
- **Real check:** the owner's 6 Pixabay tracks, classified in 4.5 s:

  | Track | Pace | ~BPM | Auto mood |
  |---|---|---|---|
  | cinematic | lively | 123 | upbeat |
  | nastelbom | lively | 117 | inspiring |
  | motivation | medium | 103 | acoustic |
  | corporate | medium | 144 | inspiring |
  | corporate-background | medium | 117 | inspiring |
  | news-intro | calm | 117 | lofi |

- **Open issues:**
  1. Real Gemini still picks the 68 s news-intro for a 9.6-min interview (loops 9×), despite the
     rule ranking it last and the prompt showing "loops 9 times". Proposed fix: drop candidates
     that need more than ~4 loops when longer ones exist, or let the rule veto the AI pick when it
     is far below the top score.
  2. A Gemini reason claimed a wrong length ("4 minutes 19 seconds covers the video" for a 2:19
     track). Proposed fix: show the rule's own fit text in the UI instead of trusting length
     claims from the AI.
- **Not run yet:** the full suite after `8d0d006`, the Library screenshot with the real tracks,
  and the closing docs (PHASE-STATE / TRACKER / CHANGELOG).
