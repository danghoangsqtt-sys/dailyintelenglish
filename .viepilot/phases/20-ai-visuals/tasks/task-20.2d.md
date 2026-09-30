# Task 20.2d — Caption style option (outline / box / bottom shade), user-selectable

- **Status:** design (Coder, doc-first, 2026-09-30). Implementation follows in a separate
  commit.
- **Owner:** Coder
- **Priority:** P1. This is the prerequisite for image backgrounds behind the Remotion
  captions (Phase 20 in-video scenes).
- **Authorization:** owner, 2026-09-30, after the 20.2b layout mockups
  (`docs/operations/phase20-layout-mockups-fullbleed.png`).
  - The owner rejected the framed "window" layout (C) as wasted space.
  - The owner asked how subtitled films handle text over busy images.
  - Then: *"tạo sao không cho người dùng sự lựa chọn cả ba phương án bạn đưa ra đều hợp lý
    đặc biệt là phương án phụ đề giống phim netflix"* — why not give the user the choice
    of all three? All three are reasonable, especially the Netflix-like subtitles.
- **Touches Phase 19 files** (the Remotion renderer + Step 5). It is filed under Phase 20
  because it exists for Phase 20's image backgrounds. It does not change Gate B-12 /
  19.8–19.9 scope; see D20.2d-f.

## Goal

The user picks one of three caption treatments for the Remotion (Enhanced) render. Each
keeps captions legible on any background, including detailed AI scenes, without shrinking
the picture.

| id | UI label | Look |
|---|---|---|
| `outline` **(default)** | Film style (outline) | White bold text with a solid black outline and a soft shadow, as film and streaming subtitles do. |
| `box` | Caption box | Text on a semi-transparent black rounded box (the YouTube caption convention). |
| `shade` | Outline + bottom shade | `outline`, plus a soft dark gradient over only the bottom ~30% of the frame. |

## Design decisions

- **D20.2d-a: data path, additive and optional everywhere.**
  1. `GenerateVideoRequest.caption_style: Literal["outline","box","shade"] = "outline"`.
  2. `video_service.generate_video(caption_style=...)`.
  3. `video_renderer_remotion.render_via_remotion(caption_style=...)`.
  4. `_build_input_props` → `props["captionStyle"]`.
  5. zod `captionStyle: z.enum([...]).default("outline")`.

  Old clients and old props files keep rendering: every layer has the default.
- **D20.2d-b: the ffmpeg (Standard) path ignores `caption_style`.** Its libass subtitles
  are unchanged, byte for byte. The option is Remotion-only, like the karaoke and the
  vocab cards.
- **D20.2d-c: the renderer design.**
  - A pure module, `video-renderer/src/captionStyle.ts`, maps a style id to:
    - the caption text CSS;
    - an optional box CSS;
    - whether the bottom shade is drawn.
  - It is unit-tested with vitest.
  - The outline is an 8-direction 2 px black `text-shadow` plus the existing 6 px glow.
    That approach is robust in headless Chrome, whereas `-webkit-text-stroke` eats into
    the glyph fill.
  - The active karaoke word keeps its yellow colour and gets the same outline, so it
    stays readable on light backgrounds.
  - The shade is drawn once for the whole audio window (no flicker between lines),
    behind the captions. It is bottom-only, so it never touches the speaker chips (top
    left) or the vocab card (top right, already on an 85% dark card).
  - `StillFrame` shares `AudioWindowContent`, so the thumbnail still uses the same
    style.
- **D20.2d-d: the Step 5 UI.**
  - A new chip group "Caption style" sits under the renderer toggle.
  - It is enabled only while Enhanced (Remotion) is selected. Otherwise it is disabled,
    with a tooltip saying it applies to Enhanced only.
  - The choice is remembered in `localStorage` (`die-caption-style`), exactly like the
    renderer choice.
  - `Api.generateVideo` sends `caption_style` **only when the renderer is `remotion`**.
    Standard-render request bodies stay byte-identical, so the existing browser-test
    body assertions are untouched.
  - The UI copy is English (D19.7n1-b: UI localization was dropped).
- **D20.2d-e: not persisted in the DB.** It is a per-render request field, the same as
  `renderer`. No migration.
- **D20.2d-f: the visible effect today, stated honestly.**
  - Remotion's background is still the flat near-black `MIDNIGHT_BACKGROUND`. On it,
    `outline` and `shade` look almost identical to the Gate B-12-signed captions (a
    black edge on near-black), and `box` adds a visible box.
  - The real benefit arrives with image backgrounds.
  - The default changes from "glow only" to "outline + glow" by the owner's explicit
    preference. On the current background that is visually negligible.

## Allowed files

- `video-renderer/src/types.ts`, `video-renderer/src/Episode.tsx`
- **New** `video-renderer/src/captionStyle.ts`, `video-renderer/src/captionStyle.test.ts`
- `app/models/video.py`, `app/api/video.py`, `app/services/video_service.py`,
  `app/services/video_renderer_remotion.py`
- `frontend/pages/step5_video.html`, `frontend/static/js/step5_video.js`,
  `frontend/static/js/api.js`
- Tests:
  - `tests/test_video_service_remotion.py`: new tests, plus the one `_fake_success` stub
    accepts the new keyword. That is a disclosed fold-in.
  - `tests/test_video_api.py`: new tests.
  - `tests/test_video_studio_browser.py`: a new test.
- This card, Phase 20 `PHASE-STATE.md`, `CHANGELOG.md` (one bullet).

**Not touched:**
- the ffmpeg render path;
- the DB schema;
- `StillFrame.tsx` (it inherits through `AudioWindowContent`);
- `Root.tsx` (its `calculateMetadata` passes the props through).

## Verification

1. vitest: new style-mapping tests plus the existing 28; `tsc --noEmit` clean.
2. pytest:
   - the request default and validation (`"neon"` → 422);
   - the props carry `captionStyle`;
   - `generate_video` forwards the style to Remotion;
   - the ffmpeg path is unaffected;
   - the full suite, with no new failures.
3. Browser (Playwright):
   - the chip group is disabled on Standard and enabled on Enhanced;
   - the POST body includes `caption_style` only for Enhanced.
4. Real Remotion stills of all 3 styles, rendered in the cloud with the preinstalled
   Chromium, attached to the report. The owner confirms on their machine with the next
   runbook.
