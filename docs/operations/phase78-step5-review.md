# Phase 78 — Step 5 Video studio: UI review and real 9:16 render (2026-10-26)

Sandbox: server `studio-p78` (port 8030, `DIE_DATA_DIR=D:\DataAdmin\p78-sandbox-data`, an online copy of the owner DB with read-only links to the libraries). The installed app and `data/app.db` were not written.

Project: The Office Startup · Ep. 1 (`5b1667a3-b47b-4c4b-b989-dddd3cb44b03`), Vietnamese UI.

## Screens (`phase78-screens/`)

| File | What it shows |
|---|---|
| `01-step5-desktop.png` | Step 5 at 1600×1100 |
| `02-storyboard-16x9.png`, `02b-insert-beat-16x9.png` | storyboard with per-beat 16:9 sketches, visible lines, aligned form |
| `03-beat-9x16.png`, `03b-beat0-9x16.png` | the same beats as 9:16 sketches (picture, caption band, characters) |
| `04-shorts-section.png`, `04b-clip-card.png` | Shorts & TikTok: a clip before rendering with its 9:16 sketch and hook |
| `05-mobile-390.png` | phone width 390 px: one column |
| `06-rendered-clip-frames.png` | frames of the real rendered clip at 0.3 / 1.5 / 5 / 20 / 40 / 60 s |
| `07-rendered-clip-cover.jpg` | the clip's 9:16 cover |
| `08-rendered-clip-card.png` | the clip card after rendering (player, downloads, texts) |

## Real render

Clip "How to break the ice at work" (lines 12–16) approved and rendered through the UI's API with talking characters and outline captions: 73 s wall time; output 1080×1920, H.264, 30 fps, 63.6 s, AAC audio (mean −19.6 dB, peak −2.1 dB). The hook banner shows alone at the start (the speaker chips no longer sit under it) and the chips come back after it; the scene, characters and captions match the clip sketch.

Found during this review and fixed: the Shorts/TikTok texts' "📋 Mô tả" button sat on the TikTok heading's line (a `<details>` element does not lay out as a grid); the texts now have their own grid body.

Owner acceptance of the look is still pending.
