# PHASE-STATE — Phase 37: Vertical video for YouTube Shorts and TikTok

- **Status:** planned 2026-10-13 (`docs/brainstorm/session-2026-10-13.md`, D98–D101). Starts after Phase 36 (reuses its
  learning pack, hashtags and cover composition).

| Task | Description | Main paths | Status |
|---|---|---|---|
| 37.1 | Remotion 1080x1920 composition: illustration top, big karaoke captions middle, both characters below (D81/D82), reusing sprites, segments and karaoke | `video-renderer/src/`, `app/services/video_renderer_remotion.py` | planned |
| 37.2 | Highlight clips: AI proposes 1–3 complete 30–90 s passages with a hook title; owner trims and approves; each clip renders | new clip model/service/API, Step 5 UI | planned |
| 37.3 | Full episode in vertical for TikTok | `video_service.py`, Step 5 | planned |
| 37.4 | Separate Shorts and TikTok packages + vertical cover; copy buttons; downloads | `youtube_service.py`, Step 7 | planned |
| 37.5 | Tests, real clips, Gate B-25 | — | planned |
