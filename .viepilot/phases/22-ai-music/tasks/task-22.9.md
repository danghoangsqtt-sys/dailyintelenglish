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

## Deeper analysis of the open issues (2026-10-06) and the fix

**Method:** `debug_pick.py` recorded the exact prompt and real Gemini answers, 5 repeats.

**Findings:**

1. **The pick is not stable.** With the same prompt (already showing "loops 9 times"), Gemini chose
   corporate-background (4 loops) 5/5. The run just before chose the 68 s news-intro (9 loops).
   Answers vary between calls.
2. **The AI's reasons can be factually wrong.** "Fewest loops" was claimed when cinematic loops
   3×; an earlier run said "4 minutes 19 seconds covers the video" for a 2:19 track.
3. **The AI could pick any of the top 5**, including the track the score ranked last. Nothing
   stopped it.

**Fix** (commit after `8d0d006`): the deterministic score is the guard rail.
`music_select_service.eligible()` keeps:

- the best-scored track;
- any other track within `SCORE_MARGIN = 3` points of it, **and**
- looping at most `EXTRA_LOOPS_ALLOWED = 2` times more than the least-looping track. A track of
  unknown length is out when other lengths are known.

The AI chooses only among those, with `temperature = 0.2`. If only one remains, there is no AI
call. Step 4 shows the app's own measured fit ("loops 4 times"), never the AI's length claims.

**Real check after the fix:** 3 real projects × 5 real Gemini picks, on the owner's library.

| Project | Video | Allowed | Picked |
|---|---|---|---|
| morning (small talk) | 5.1 min | 2 tracks | motivation 5/5 (3 loops) |
| evening (interview) | 9.8 min | 3 tracks; the 9-loop jingle excluded | corporate-background 5/5 (4 loops) |
| remote work (news) | 8.1 min | 5 tracks | cinematic 5/5 (2 loops) |

Every case was stable, and no pick looped more than 4×.

**Remaining limit (the library, not the code):**

- Every track is at most 4:11, and there is no long calm track.
- So a news episode has to choose between a calm track that loops 8× and a livelier one that loops
  2×.
- Recommendation for the owner: add a few **longer (4–6 min) calm and acoustic** tracks, and fill
  in tags.

**The intermittent 337/338-error full-suite runs (investigated):**

- Twice (at 22.5 and after the guard rail), every test from a fixed position onward errored. The
  same count from the end means the same trigger: the module right before the break is
  `test_storyboard_browser.py`.
- **Mechanism:** its live server not stopping within the 10 s join leaves its DB connection open,
  and the conftest stale-connection guard (BUG-023) then refuses every later app test. The guard
  is correct.
- **Not reproduced:**
  - 6 isolated runs (teardown 0.2–0.35 s);
  - 8 runs of the pair with the next module;
  - 3 full runs with `--maxfail=1`, all 1433 passed.
- **Plausible cause:** uvicorn's unbounded graceful shutdown waiting on a connection left by a
  closed browser, under full-suite load.
- **Fix (test harness only, guard unchanged):** `timeout_graceful_shutdown=5`, join 20 s.
- **Earlier record corrected:** the 22.5 note called the 337 errors "cause not determined". It is
  this same, now-located failure.

**Tests:** `test_music_select.py` 11 (+2 guard-rail tests) and the auto browser test 2.
**Full suite: 1433 passed.**
