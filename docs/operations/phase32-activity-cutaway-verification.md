# Phase 32.6f — Activity cutaway verification

Date: 2026-10-09
Project: `b330d37f-a212-4cf7-a779-7a109098bd6c` (`Demo Episode`)

## Result

Task 32.6f passes. The production Remotion path rendered the Demo Episode with exactly
three approved generic activity cutaways, no renderer fallback, continuous captions and
overlays, and a continuous audio stream. The original talking-sprites preview remains in
place for Gate B-22 comparison.

## Automated verification

| Check | Result |
|---|---|
| Phase 32.6a–e targeted Python/API/browser suite | 42 passed, 2 warnings |
| Python tests without browser files | 1,411 passed, 2 warnings in 744.45 s |
| All 42 browser files, one pytest process per file | 235 passed; 42/42 files passed |
| Combined Python coverage | 1,646 passed |
| `video-renderer` Vitest | 65 passed in 9 files |
| `video-renderer` TypeScript | `npx tsc --noEmit` passed |
| Ruff on the 9 Phase 32 Python files | passed |
| Full video decode | `ffmpeg -v error ... -f null -` completed with no errors |

Two monolithic `pytest tests/ -x -q` attempts encountered different Playwright
`page.goto` 30-second timeouts after accumulating browser processes:

- `test_thumbnail_browser.py::test_edit_re_render_serializes_one_trailing_save_with_latest_draft`
  after 1,306 tests had passed. The exact test then passed three consecutive isolated runs
  in 5.11, 5.25 and 6.57 seconds.
- `test_app_sidebar_browser.py::test_every_page_has_one_sidebar_with_one_link_of_each_name[/step1]`
  after 264 tests had passed. The exact test then passed three consecutive isolated runs
  in 5.45, 4.53 and 4.86 seconds.

The complete suite was therefore rerun as all non-browser tests in one process and every
browser file in its own process. Both previously timed-out files passed in this complete
segmented run (`test_thumbnail_browser.py`: 6/6; `test_app_sidebar_browser.py`: 15/15).
This is non-regression evidence for a cumulative Playwright resource flake rather than a
Phase 32 failure.

## Real coverage and render

The three approved insert beats reported 3 matched / 0 missing before render:

| Beat action | Match | Score | Activity ID |
|---|---|---:|---|
| `morning routine` | generic | 80 | `8948723e-1e67-4d88-9461-12e61cc9f037` |
| `exercise` | generic | 80 | `6ed77000-7895-4b0a-8bc3-9f75e42e6815` |
| `cooking breakfast` | generic `cooking` | 80 | `0dfa3a8c-b112-42f8-9ee8-cc1648e6680c` |

Production API result:

- Video job: `4b365646-c954-48ce-a085-5d9db2f64439`
- Status/mode: `complete` / `remotion`
- Render time: 156.784 seconds
- Fallback: `false`
- Output: `data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/video_remotion.mp4`
- Baseline preserved: `data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/video_sprites_preview.mp4`
- Pre-render database backup:
  `data/backups/app-before-phase32-demo-20261009-113348.db`

The successful API transaction advanced the project to `video_generated`, created one
usage-history row for each beat and raised each selected image's `use_count` to 1.

## Media probe

- Candidate: 192.256 s, 66,694,830 bytes, H.264 1280×720, AAC stereo 48 kHz.
- Baseline: 183.573 s, 68,351,270 bytes, H.264 1280×720, AAC stereo 48 kHz.
- Candidate audio: 9,012 packets from 0.000 to 192.256 s.
- Maximum positive packet gap: 0.000001 s; gaps over 1 ms: 0.
- Full decode produced no ffmpeg errors.

The longer candidate duration comes from the current 7.62-second branded intro and
8.54-second branded outro. Activity images do not alter the narration timeline.

## Manual visual evidence

Frames were extracted to
`data/video/b330d37f-a212-4cf7-a779-7a109098bd6c/phase32_evidence/`.
For each beat, the transition sheet is ordered:
`before | fade-in | midpoint | fade-out | after`.

Visual inspection confirms all three sequences return cleanly from sprites to the
full-frame activity and back. Speaker chips, vocabulary cards and subtitles remain above
the cutaway at the midpoint and through both 0.3-second transitions. Detailed timings and
observations are in `phase32-demo-cutaway-notes.md`.

## Remaining gate

Task 32.7 / Gate B-22 remains owner-controlled. Phase 32 must not close and Phase 33 must
not open until the owner explicitly compares the baseline and candidate and records PASS.
