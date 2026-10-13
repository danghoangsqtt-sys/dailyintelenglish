# PHASE-STATE — Phase 37: Vertical video for YouTube Shorts and TikTok

- **Status:** in progress 2026-10-13 (owner /vp-auto: finish the whole project) (`docs/brainstorm/session-2026-10-13.md`, D98–D101). Starts after Phase 36 (reuses its
  learning pack, hashtags and cover composition).

| Task | Description | Main paths | Status |
|---|---|---|---|
| 37.1 | Remotion 1080x1920 composition: illustration top, big karaoke captions middle, both characters below (D81/D82), reusing sprites, segments and karaoke | `video-renderer/src/`, `app/services/video_renderer_remotion.py` | in_progress |
| 37.2 | Highlight clips: AI proposes 1–3 complete 30–90 s passages with a hook title; owner trims and approves; each clip renders | new clip model/service/API, Step 5 UI | planned |
| 37.3 | Full episode in vertical for TikTok | `video_service.py`, Step 5 | planned |
| 37.4 | Separate Shorts and TikTok packages + vertical cover; copy buttons; downloads | `youtube_service.py`, Step 7 | planned |
| 37.5 | Tests, real clips, Gate B-25 | — | planned |

## Implementation notes (before coding)

- 37.1: props gain `layout` ("horizontal" default | "vertical") and `audioOffsetSec` (default 0, the audio and soundtrack
  start there -- a clip is a window of the mixed episode). Vertical (1080x1920): the scene/illustration fills the top 56%,
  a dark band holds big karaoke captions (54 px) in the middle, the two characters stand in the bottom 44% at x 27%/73%
  with the video's placement and mirroring; the vocabulary card sits top-centre; the illustrated (shots) mode uses the same
  top area. `video_renderer_remotion.render_via_remotion(..., layout, clip)` builds the same props, sizes 1080x1920, and for a
  clip keeps only its lines (times shifted), a short hook intro (title = hook) and a short outro.
- 37.2: migration 024 `short_clips` (project, line_from, line_to, hook, status proposed|approved|rendered, mp4_path, cover
  path, created/updated). `shorts_service.propose` asks the AI for 1-3 complete passages of 30-90 s (measured from the
  audio timestamps) with a hook title, keeps only valid ones; owner edits range/hook, approves; `render_clip` renders it.
- 37.3: `POST /video/vertical` renders the whole episode vertical into `video_vertical.mp4` (`mp4_path_vertical`); the
  `mp4_vertical` download comes back.
- 37.4: per clip: a 9:16 cover from `thumbnail_compose` (hook as headline), a Shorts package (title <= 100 chars with
  #Shorts, short description with 3 learning items and the full episode's link when published, hashtags) and a TikTok
  caption (hook, two lines, <= 5 hashtags); Step 5 "Shorts & TikTok" section with copy buttons and downloads.
