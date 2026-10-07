# Task 27.5: Video intro and outro with the Daily Beyond English brand

## Owner decisions (2026-10-06 and 2026-10-07)

- The channel is **Daily Beyond English** (D57); the owner's avatar logo and green / yellow / white palette (D60); the
  name applies to the video intro and outro and to Jenny's greeting (D62).
- The owner approved the Phase 25 morph and Jenny's voice; only the logo, the name and the palette change.
- The owner did not want the "New videos every Wed & Sat" line.
- Order set by the owner on 2026-10-07: this task first, then one full real episode (Gate B-20).

## Facts (read from the code)

- `video-renderer/src/Brand.tsx`: `BrandIntro`, `BrandOutro`, `Logo` (a violet-to-cyan rounded square with "DI",
  wordmark "Daily Intel" over "ENGLISH"), `Background` (indigo gradient + three violet / cyan / pink blobs), pills in
  amber, a red Subscribe chip. Colours are constants at the top.
- `app/services/brand_service.py`: `GREETING = "Welcome to Daily Intel English Channel!"`, `FAREWELL = "Thanks for
  watching Daily Intel English!"`; the synthesised voice is cached by `voice | text` (`brand_voice_cache`), so new text
  makes new audio automatically.
- `.gitignore` of `video-renderer`: `public/*` is ignored except `public/fonts/`; the render stages episode files under
  `public/remotion-render/` and loads them with `staticFile()`.
- `tests/test_brand_service.py` pins the two old sentences; `brand.test.ts` pins only the pure helpers.

## Plan

1. **Logo asset:** `video-renderer/public/brand/logo.png` (512 px, from the owner's file) and an exception in
   `video-renderer/.gitignore` (`!public/brand/`), loaded with `staticFile("brand/logo.png")`.
2. **`Brand.tsx`:**
   - the mark is the owner's circular logo (an `<Img>` that appears, then glides to the header like the old square;
     the render waits for the image with `delayRender`-safe `Img`), with a soft lime glow;
   - wordmark: "Daily Beyond" in white and "ENGLISH" in the logo's yellow `#FFD60A`;
   - background: deep green (`#0A1F12` -> `#0F2A1A` -> `#17361F`), blobs in green `#3A9D3F`, lime `#9BD13C` and yellow
     `#FFD60A` (the pink blob goes), the same vignette;
   - the CEFR pill becomes yellow with dark text, the speaker ring colours become yellow and lime, the Subscribe chip
     stays red (`#E5322D`); the text colours stay readable (white on deep green >= 12:1, muted `#CFE8D2`);
   - the intro title and the farewell are unchanged in timing.
3. **`brand_service.py`:** `GREETING = "Welcome to Daily Beyond English Channel!"`, `FAREWELL = "Thanks for watching Daily
   Beyond English!"`.
4. **Constants for tests:** `Brand.tsx` exports `BRAND_PALETTE`, `BRAND_NAME` and `LOGO_PATH`.
5. **Tests:**
   - `tests/test_brand_service.py`: the new sentences;
   - `video-renderer/src/brand.test.ts` (vitest): the palette has no violet or cyan and every text / background pair
     is at least AA (4.5:1); the name text; `mixColor` on the new greens;
   - a Python test that the logo file exists at 512 px and is not git-ignored;
   - `tsc --noEmit` clean.
6. **Real check (Remotion):** render stills of the intro (hero, mid-morph, final) and the outro (start, mid, end) from the
   real composition with real props, and look at them; then render the whole intro and outro to a short video, check its
   length against `brand_timing`, and send the stills to the owner. Jenny's new greeting is synthesised once to confirm
   the cache and the timing (a network call to Edge TTS, the same service the app already uses).

## Paths

- `video-renderer/src/Brand.tsx`
- `video-renderer/src/brand.test.ts`
- `video-renderer/public/brand/logo.png` (new)
- `video-renderer/.gitignore`
- `app/services/brand_service.py`
- `tests/test_brand_service.py`
- `tests/test_brand_assets.py`
- `docs/operations/phase27-brand-video.md` (the report)

## Verification

- `npm test` and `npm run typecheck` in `video-renderer`, the Python brand and video tests, then the full suite.
- The stills and one short render looked at by Claude; length of the rendered intro and outro equals the timing the app
  computes.

## Out of scope

The Remotion pictures of the episode itself (the shots), the YouTube thumbnail templates (Step 6 keeps its own
templates), and any new voice.
