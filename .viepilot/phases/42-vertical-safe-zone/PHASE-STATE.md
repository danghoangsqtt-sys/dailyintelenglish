# PHASE-STATE — Phase 42: Vertical video inside the platform safe zone + vertical intro/outro (D121)

- **Status:** 42.1–42.4 implemented and sandbox renders checked with the safe-zone overlay 2026-10-14; owner Gate B-25 re-run pending. Opened 2026-10-14. Owner Gate B-25 review of `video_vertical.mp4`: the vertical video does not keep its
  content in the safe area of TikTok / Reels / YouTube Shorts (the app's buttons, tabs and captions cover it), and the
  intro/outro are the horizontal slides zoomed (logo cut, title off-centre) — they need their own vertical version.

| Task | Description | Status |
|---|---|---|
| 42.1 | `renderer/src/safeZone.ts`: the 1080x1920 safe zone (owner's TikTok template, stricter bottom for captions) + a check helper; Vitest that every vertical element box lies inside it | done |
| 42.2 | Vertical episode layout rebuilt on it: picture top (decoration may run under the UI), speaker chips, vocabulary card, hook banner and captions inside the zone (captions clear of the right button column), characters' faces above the bottom caption area | done |
| 42.3 | `BrandIntroVertical` / `BrandOutroVertical`: logo, title, level, cast, greeting and Like/Subscribe/Share stacked and centred inside the zone | done |
| 42.4 | Real sandbox vertical render + clip, frames with safe-zone overlay | done; Gate B-25 pending owner |

## Safe zone (1080x1920 pixels)

From the owner's TikTok template (1080x1920): covered = top 0–115 (status/tabs), the "Following / For You" box
x 313–762 y 133–216, sides 0–46 and 1033–1080, bottom 1545–1920, and the right button column x 886–1033 from y 958.
The ads spec the owner also sent covers the bottom 600 px (username, caption, music, CTA), so we keep **key content**
(faces, captions, titles, cards, buttons) within: x 72–1008, y 232–1320, and x ≤ 864 below y 900. Backgrounds and
bodies may run under the UI.

## As built (2026-10-14)

- `renderer/src/safeZone.ts` (zone + `insideSafeZone` + the vertical layout in pixels) and `safeZone.test.ts` (4 tests:
  chips, vocabulary card, hook banner, captions, both faces, intro/outro columns inside the zone).
- Episode: chips at y 244 (CSS-zoom offsets unscaled), vocabulary card left-aligned x 72–864 y 316–776, hook banner y 330,
  captions x 72–864 y 790–1040 (left of the button column), characters' heads from y 1045, faces above y 1270, centres
  x 270 / 640; picture 0–790.
- `BrandIntroVertical` / `BrandOutroVertical`: logo, title, level, topic, cast, greeting, Thanks/Like/Subscribe/Share and
  the farewell centred inside the zone (wide column above y 900, narrow centred column below).
- Sandbox: the full vertical episode (4:01) and a clip rendered and checked frame by frame with the owner's TikTok template
  overlaid (`data/tmp/phase42/*.jpg`).
