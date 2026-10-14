# PHASE-STATE — Phase 42: Vertical video inside the platform safe zone + vertical intro/outro (D121)

- **Status:** in progress 2026-10-14. Owner Gate B-25 review of `video_vertical.mp4`: the vertical video does not keep its
  content in the safe area of TikTok / Reels / YouTube Shorts (the app's buttons, tabs and captions cover it), and the
  intro/outro are the horizontal slides zoomed (logo cut, title off-centre) — they need their own vertical version.

| Task | Description | Status |
|---|---|---|
| 42.1 | `renderer/src/safeZone.ts`: the 1080x1920 safe zone (owner's TikTok template, stricter bottom for captions) + a check helper; Vitest that every vertical element box lies inside it | in_progress |
| 42.2 | Vertical episode layout rebuilt on it: picture top (decoration may run under the UI), speaker chips, vocabulary card, hook banner and captions inside the zone (captions clear of the right button column), characters' faces above the bottom caption area | in_progress |
| 42.3 | `BrandIntroVertical` / `BrandOutroVertical`: logo, title, level, cast, greeting and Like/Subscribe/Share stacked and centred inside the zone | in_progress |
| 42.4 | Real vertical render + a clip, frames with the safe-zone overlay; Gate B-25 re-run | in_progress |

## Safe zone (1080x1920 pixels)

From the owner's TikTok template (1080x1920): covered = top 0–115 (status/tabs), the "Following / For You" box
x 313–762 y 133–216, sides 0–46 and 1033–1080, bottom 1545–1920, and the right button column x 886–1033 from y 958.
The ads spec the owner also sent covers the bottom 600 px (username, caption, music, CTA), so we keep **key content**
(faces, captions, titles, cards, buttons) within: x 72–1008, y 232–1320, and x ≤ 864 below y 900. Backgrounds and
bodies may run under the UI.
