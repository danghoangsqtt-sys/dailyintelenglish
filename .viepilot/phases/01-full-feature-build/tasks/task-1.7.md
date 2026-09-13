# Task 1.7: Step 5 — Video Studio

## Meta
- **ID**: 1.7
- **Phase**: 1
- **Status**: done (2026-09-13) for both sub-tasks (1.7a backend, 1.7b UI) — the only
  remaining item is Level 3 LivePortrait, which was never part of the sub-task split and
  stays blocked on a user avatar-image-sourcing decision (see Acceptance Criteria item 2)
- **Priority**: medium
- **Assignee**: AI

## Paths
- `app/services/video_service.py`
- `app/api/video.py`
- `frontend/pages/step5_video.html`
- `frontend/static/js/step5_video.js`

## Acceptance Criteria
- [x] Level 2 video: Background image (from a fixed template set, not a looping video) +
  burned-in subtitles + SRT export — Sub-task 1.7a, 2026-09-13
- [ ] Level 3 video: LivePortrait lips-sync on portrait avatar — deferred, blocked on a
  user decision (where do per-speaker avatar images come from?), same class of blocker as
  OmniVoice's `ref_audio`
- [ ] Safe fallback from Level 3 to Level 2 on error/VRAM limit — moot until Level 3 exists
- [x] Video Studio UI with preview player and export options — Sub-task 1.7b, 2026-09-13
  (background-template selector only — no avatar/lips-sync controls, since that backend
  path doesn't exist; see acceptance criterion 2)

## Forbidden Scope
- No synchronous ffmpeg calls on event loop
- No failure to generate fallback when lips-sync fails

## Verification Commands
- `venv\Scripts\python -m pytest tests/`

## Implementation Notes (2026-09-13, Sub-task 1.7a: VideoService backend — Level 2 background+subtitle path)

User is unreachable this session (traveling), explicitly authorized autonomous PM+Implementer
decisions with strict self-verification. Split into sub-tasks matching the established
1.6a/b/c, 1.8a/b, 1.9a/b, 1.10a/b pattern, because Level 3 (LivePortrait avatar lip-sync)
hits the same class of blocker OmniVoice hit: it needs a real per-speaker avatar image
(`speakers.avatar_image_path` is null for every speaker, no upload feature exists, and
there is no "generate an avatar" pipeline either) — inventing placeholder avatar images to
unblock it would be fabricating a production asset, not a legitimate engineering shortcut.
That decision (where do avatar images come from — user upload? AI image generation?) is
for the user, deferred exactly like OmniVoice's `ref_audio` question.

**Real proof-of-concept run before writing any production code** (per this project's
standing "verify before committing to a plan" discipline): built a throwaway background
PNG (Pillow) + tone MP3 (pydub) + hand-written SRT file, ran the real installed ffmpeg with
`-loop 1 -i bg.png -i audio.mp3 -vf "subtitles='<escaped path>'" -c:v libx264 -tune
stillimage -c:a aac -pix_fmt yuv420p -shortest out.mp4`, extracted a frame, and visually
confirmed the burned-in subtitle rendered correctly (libass drop-shadow style, confirmed
`ffmpeg -version` reports `--enable-libass` on this exact build). Also confirmed the
Windows path-escaping rule for ffmpeg's filtergraph syntax needed for the `subtitles=`
filter: `path.replace("\\", "\\\\").replace(":", "\\:")` wrapped in single quotes — the
drive-letter colon and any backslash must be escaped or the filter parser misreads the
path as `key=value` options.

Scope (ROADMAP.md Task 1.7 "VideoService — Background + Subtitle" bullet):
- `generate_video_basic(project_id)` — static background image (one of a fixed set of
  pre-made templates, no custom upload yet — same "template" concept as
  `frontend/static/thumbnail_templates/*.png`: pre-rendered static assets, not
  per-request generated; custom upload is deferred to a later sub-task) + the real
  completed audio mix from Task 1.6 + burned-in subtitles.
- SRT file generation from AudioService's real (measured, not estimated) per-line
  timestamps — this is the *real* transcript-timed subtitle source Sub-task 1.9b will
  later also want for YouTube's full transcript.
- Burned-in subtitles via ffmpeg's `subtitles` filter (libass), proven above.
- `video_jobs` table already exists in `001_init.sql` (`id, project_id, status, mode,
  mp4_path, srt_path, background_image, subtitle_style_json, error_message, started_at,
  completed_at`) — same UPSERT-on-`project_id` pattern as `audio_jobs`/`youtube_packages`.
- Requires the audio mix to already exist (`audio_jobs.status == "complete"`) — this
  service reads `AudioService`'s output, it doesn't regenerate audio.
- Advance `projects.status` `audio_generated -> video_generated` on success, same
  best-effort/current-status-must-match-exactly rule as 1.6b's `audio_generated` advance.

**Small, backward-compatible change to `app/services/audio_service.py`'s existing
timestamps shape**: added a `text` field to each timestamp entry (the script line's actual
spoken text), and `get_lines_for_mixing()` now also selects `text`. Needed because
subtitles must show the real dialogue, not just a speaker label — the alternative
(re-fetching and positionally re-aligning script lines against timestamps in a second
service) is fragile and was rejected in favor of putting the text where it's naturally
generated. Verified this doesn't break any existing 1.6b consumer: no test asserts an
exact/closed timestamp keyset, all read specific keys (`start_sec`/`end_sec`/`label`).

Files:
- `app/services/video_service.py` (new): `generate_srt(timestamps) -> str` (pure,
  independently unit-testable), `list_video_templates() -> list[dict]`,
  `generate_video(project_id, audio_job, template_id) -> dict` (blocking ffmpeg subprocess
  call wrapped in `asyncio.to_thread` — never blocks the event loop, per this task's
  Forbidden Scope), `get_video_job`/`save_video_job` (UPSERT, mirrors `audio_service.py`).
- `frontend/static/video_backgrounds/` (new): 3 pre-rendered static PNG templates
  (1280x720, matching `VIDEO_WIDTH_STANDARD`/`VIDEO_HEIGHT_STANDARD`), generated once via
  a small one-off script and committed as binary assets — same precedent as
  `frontend/static/thumbnail_templates/*.png`. No per-project custom text/branding baked
  in (subtitles carry all the per-episode content); these are deliberately plain.
- `app/api/video.py` (new): `GET /api/video/templates`; `POST
  /api/projects/{id}/video/generate` (body: `{template_id}`; `ValidationError` if the
  audio mix isn't complete yet); `GET .../video/status` (plain polling GET, same
  documented SSE-label deviation as `/audio/status`); `GET .../video/download?format=mp4|srt`.
  Register in `app/main.py`.
- `app/models/video.py` (new): `GenerateVideoRequest`, `VideoJobOut`.
- `app/core/exceptions.py`: `VideoRenderError` already exists, reused as-is.
- `tests/test_video_service.py` (new): `generate_srt` formatting (timestamps, sequential
  numbering, HH:MM:SS,mmm), a real end-to-end ffmpeg render test (real tiny background +
  real tiny audio, not mocked — same "exercise the real local library" philosophy as
  `tests/test_audio_service.py`) asserting a real playable MP4 comes out, and a
  `VideoRenderError` path when the audio mix isn't complete.
- `tests/test_video_api.py` (new): API-level tests (success, 422 when audio not generated
  yet, 404s, unsupported template/format).

Forbidden Scope for this sub-task: no LivePortrait/avatar lip-sync (Level 3 — deferred,
needs a user decision on avatar image sourcing), no Video Studio UI (deferred to a later
sub-task, same split pattern as 1.6b/1.6c), no custom background image upload (deferred —
templates-only for now), no synchronous ffmpeg call on the event loop.

## Sub-task 1.7a Result (2026-09-13) — DONE

Delivered exactly the plan above: `app/services/video_service.py`, `app/models/video.py`,
`app/api/video.py` (registered in `app/main.py`), `scripts/generate_video_background_assets.py`
+ 3 committed PNG templates in `frontend/static/video_backgrounds/`, `VIDEO_TEMPLATE_IDS`/
`VIDEO_TEMPLATE_LABELS` added to `app/core/constants.py` (matching the existing
`THUMBNAIL_TEMPLATE_IDS` convention — defined in constants, not the service module, so
`app/models/video.py` doesn't need to import from `app/services/video_service.py`). Small
backward-compatible addition to `app/services/audio_service.py`: `get_lines_for_mixing()`
now also selects `text`, and each timestamp entry now includes it — needed so subtitles
can show real dialogue, not just a speaker label; verified no existing 1.6b test asserts
an exact/closed timestamp keyset (all 25 pre-existing audio tests still pass unchanged).
20 new tests (9 `tests/test_video_service.py` + 11 `tests/test_video_api.py`).

Real proof-of-concept run *before* writing any production code (see Implementation Notes
above): confirmed the installed ffmpeg build has `--enable-libass` and that a hand-built
background+audio+SRT triple actually burns in readable subtitles, and worked out the exact
Windows path-escaping rule ffmpeg's `subtitles` filter needs. This meant the real
implementation worked on the first full end-to-end smoke run, not through trial and error
against production code.

Live-verified end-to-end with real data (not just the automated test suite): a manual
smoke script created a real project via the real API, saved a real script, ran real Edge
TTS synthesis (network mocked, pipeline otherwise real) for each line, ran the real
`AudioService.mix_project`, then the real `VideoService.generate_video` — producing an
actual playable MP4 in 167ms. Extracted a real video frame and visually confirmed the
burned-in subtitle correctly reads "Alex: Welcome to the show, everyone!" against the
`midnight` template background, with the exact real speaker name and real script text —
not placeholder content. Also verified the 422 rejection path on a project with no audio
generated yet, and that `projects.status` correctly advances
`audio_generated -> video_generated`.

### Verification output

`venv\Scripts\python -m pytest tests/test_video_service.py tests/test_video_api.py -q` (exit 0):
```
9 passed
11 passed
```

`venv\Scripts\python -m ruff check app/ tests/ scripts/` (exit 0): `All checks passed!`

`venv\Scripts\python scripts/generate_video_background_assets.py --check` (exit 0):
```
OK: 3 video background template assets match deterministic sources
```

Not done (deferred): Level 3 LivePortrait avatar lip-sync (needs a user decision on avatar
image sourcing — see task file header), Video Studio UI (`frontend/pages/step5_video.html`,
Sub-task 1.7b), custom background image upload, Shorts (9:16) video export.

## Implementation Notes (2026-09-13, Sub-task 1.7b: Video Studio UI)

User continued autonomous session ("tiếp tục"), same standing authorization.

Scope is deliberately narrower than ROADMAP.md's full "Video Studio UI" bullet list,
matching the backend reality Sub-task 1.7a actually built (no dead/fake controls for a
mode that doesn't work — same principle already applied on `/step4`'s TTS engine
dropdown, which only lists the 2 engines that actually do something):
- **Background selector**: choose one of the 3 fixed templates (`GET /api/video/templates`)
  — no custom upload UI, matching 1.7a's own scope decision (templates-only for now).
- **NOT built**: avatar uploader, subtitle style picker, mode toggle, "copy prompt to
  generate avatar image" — all belong to Level 3 (LivePortrait), which isn't implemented
  and is blocked on a real user decision (see Task 1.7 header). Building UI controls for
  a backend path that always fails would be a fake feature, not a scope cut.
- **Generate button**: synchronous call to `POST .../video/generate` (rendering takes well
  under a second for a typical episode — verified in 1.7a's live smoke test), busy-state
  text while in flight, same pattern as `/step4`'s "Generate All" progress text (no fake
  animated progress bar for a near-instant operation).
- **Preview player**: `<video controls>` once a completed job exists (either just
  generated, or already existed on page load/revisit).
- **Download MP4 / SRT buttons**: plain links to `GET .../video/download?format=mp4|srt`.
- **Empty state**: if no completed audio mix exists yet (Task 1.6), show a message
  directing back to Step 4 instead of a broken/confusing generate attempt — same pattern
  as `/step4`'s own empty-state for a project with no script yet.
- **Pipeline navigation**: add `/step5` route in `app/main.py`; give `/step4` a "Next:
  Video Studio →" forward button (it never had one — Task 1.6's acceptance criteria didn't
  require pipeline nav, but now that Step 5 exists, closing the chain is a natural,
  low-risk addition matching the established Step 2→3→4 pattern exactly) and `/step5` a
  "← Back to Step 4" link.

Files:
- `frontend/pages/step5_video.html` + `frontend/static/js/step5_video.js` (new): same
  visual language and async-safety conventions as `step4_tts.html`/`.js` (friendly-only
  error banner, double-submit lock on Generate, `beforeunload` guard while generating).
- `app/main.py`: new `GET /step5` route serving `step5_video.html`.
- `frontend/static/js/api.js`: add `listVideoTemplates`, `generateVideo`,
  `videoDownloadUrl` (`getVideoStatus` already added in Task 1.9 Sub-task 1.9b).
- `frontend/pages/step4_tts.html` + `step4_tts.js`: add a "Next: Video Studio →" button
  navigating to `/step5?project_id=...`.
- `tests/test_video_studio_browser.py` (new): Playwright E2E with `page.route()` network
  mocking (same pattern as `tests/test_tts_audio_browser.py`) — no real ffmpeg needed for
  a frontend-logic test. Covers: empty state before audio exists, template selection +
  generate happy path, existing-job-shown-on-load, download link hrefs, friendly error on
  a failed generate, and the new Step 4 → Step 5 → (back) navigation links.

Forbidden Scope: no avatar/lips-sync UI, no custom background upload UI, no subtitle style
picker, no fake progress bar for a near-instant operation.

## Sub-task 1.7b Result (2026-09-13) — DONE, closes Task 1.7's sub-task split

Delivered exactly the plan above. New: `frontend/pages/step5_video.html` +
`frontend/static/js/step5_video.js` (registered at `/step5` in `app/main.py`), 3 new
`api.js` methods (`listVideoTemplates`, `generateVideo`, `videoDownloadUrl`). `/step4` now
has a "Next: Video Studio →" button (it never had pipeline nav before — added here since
Step 5 now exists to link to). 7 new Playwright tests (network-mocked, same pattern as
`tests/test_tts_audio_browser.py`), 428/428 total tests pass, ruff clean, all touched JS
files `node --check` clean.

Live-verified with a real end-to-end smoke script (not just mocked route tests): listed
the 3 real templates, created a real project, ran real Edge-TTS-mocked synthesis, real
`AudioService` mix, then called the real `POST .../video/generate` and
`GET .../video/status` through the same TestClient — both returned real success. Also took
a real Playwright screenshot of the rendered page to visually confirm layout/theme
consistency with the rest of the app before calling this done.

**This closes Task 1.7's sub-task split** (1.7a AudioService-consuming backend, 1.7b UI)
— only Level 3 LivePortrait avatar lip-sync remains, which was never part of that split
and stays blocked on a real user decision (where do per-speaker avatar images come from?).

### Verification output

`venv\Scripts\python -m pytest tests/test_video_studio_browser.py -q` (exit 0):
```
7 passed in 15.42s
```

`venv\Scripts\python -m ruff check app/ tests/ scripts/` (exit 0): `All checks passed!`

`node --check` on `api.js`, `step4_tts.js`, `step5_video.js`: all exit 0.
