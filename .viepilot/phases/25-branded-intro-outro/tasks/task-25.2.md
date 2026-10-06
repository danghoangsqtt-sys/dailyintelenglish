# Task 25.2: Branded morph intro and outro with Jenny's greeting and farewell (doc-first card)

## Owner decisions from spike 25.1 (2026-10-06)

> "Giọng của JennyNeural là tốt và cân bằng nhất. Màu logo và bố cục di chuyển rất tốt, đồng ý
> với font chữ của bạn"

- **Voice:** `en-US-JennyNeural`.
- **Look:** keep the spike's colours, logo and morph movement as they are.
- **Font:** bundle an open-licence font (download approved). **Montserrat** (SIL OFL 1.1), one
  variable TTF, is committed under `video-renderer/public/fonts/`. It needs a `.gitignore`
  exception, because `public/` is ignored.
- **Fix noted in the spike:** the header wordmark was too small. Make it larger and crisper.

## Objective

Every **Enhanced** video:

- **opens** with the branded morph intro: logo hero → header, the title, CEFR/topic/speakers, a
  per-episode wish, and Jenny saying "Welcome to Daily Intel English Channel!" + the wish;
- **closes** with the matching outro: logo back to the centre, "Thanks for watching!", Like /
  Subscribe / Share, and Jenny's farewell.

The music bed (22.4) ducks under both voices. The Standard (ffmpeg) videos are unchanged.

## Paths

- `app/services/brand_service.py` (new)
- `app/core/constants.py`
- `app/services/audio_service.py`
- `app/services/video_renderer_remotion.py`
- `video-renderer/src/Brand.tsx` (new; production intro/outro, from the spike)
- `video-renderer/src/Episode.tsx`
- `video-renderer/src/types.ts`
- `video-renderer/src/Root.tsx` (remove the spike composition)
- `video-renderer/src/BrandSpike.tsx` (delete)
- `video-renderer/.gitignore`
- `video-renderer/public/fonts/Montserrat-Variable.ttf` (new)
- `video-renderer/public/fonts/OFL.txt` (new)
- `tests/test_brand_service.py` (new)
- `tests/test_music_soundtrack.py`
- `tests/test_video_soundtrack.py`
- `video-renderer/src/brand.test.ts` (new)

## File-Level Plan

1. **`brand_service.py`:**
   - `GREETING` and the curated `WISHES` (12) and `FAREWELLS` (8): short, natural, CEFR-friendly.
   - `pick(project_id, items)` is deterministic (sha256 of the id), so a re-render keeps the same
     lines.
   - `brand_lines(project_id)` returns `{wish, greeting_text, farewell_text}`.
   - `synthesize(text)`:
     - Edge TTS Jenny, with the app's Edge retry;
     - cached at `DATA_DIR/brand_voice/<sha1(voice+text)>.mp3`;
     - returns the path + its duration.
   - `brand_timing(greeting_s, farewell_s)` returns the intro and outro lengths and the voice start
     times:
     - intro = max(6.0, 0.4 + greeting + 1.0);
     - outro = max(6.0, 0.5 + farewell + 1.8).
2. **`audio_service.build_soundtrack`** gains `extra_voices=[(path, start_s), ...]`. They are
   placed on the timeline and added to the duck spans. With no music there is no soundtrack, as
   today, and Remotion plays the voices itself.
3. **Remotion runner:**
   - build the brand props: wish, the greeting/farewell public paths, their start seconds,
     `introSec`, `outroSec`;
   - copy the voices into `public/remotion-render/brand/`;
   - the soundtrack (when there is music) includes the voices, and `brand.voicesInSoundtrack`
     tells the components not to play them a second time.
4. **`Brand.tsx`:**
   - `BrandIntro` / `BrandOutro`, ported from the spike, using Montserrat (`@font-face` +
     `delayRender` until loaded);
   - a larger header wordmark;
   - the pure helpers (`mix`, `mixColor`) are exported for vitest.
   - **`Episode.tsx`** uses them in place of the old `Intro`/`Outro`. Old props without `brand`
     still render: the brand slides without a voice, with a default wish.
5. **Remove the spike composition and file.** The voice spike script stays (not shipped).

## Verification

- pytest: lines are deterministic, the texts, the timing maths, the TTS cache (fake Edge), and the
  soundtrack with extra voices ducks the music under them. The props include brand and the
  lengths.
- vitest + `tsc`.
- The full suite is green.
- **Real Enhanced render of 1 real project** (DB copy) with music: check the length = intro + speech
  + outro, Jenny audible in the intro and outro, the music ducked under her, and key-frame stills.

## Results (done 2026-10-06)

- **Built as planned:**
  - `brand_service` (12 wishes, 8 farewells, deterministic per project; Jenny cached by text);
  - the soundtrack `extra_voices` (normalised to the voice loudness, ducking spans);
  - the Remotion runner `_add_brand`: if Edge is down, the branded slides render silent at 6 s;
  - `Brand.tsx` with Montserrat (bundled SIL OFL, 745 KB variable TTF) and a larger header
    wordmark;
  - `Episode.tsx` uses `BrandIntro`/`BrandOutro`; the spike composition is removed.
- **Fixes found while checking:**
  - Remotion `<Audio>` mounted late does not start at its own beginning, so the brand voice is
    wrapped in a `<Sequence from=…>`.
  - The ratio threshold in the spectral test was set too high, then set to a sound one (~+10 dB).
  - A loudness comparison across two separately normalised soundtracks was meaningless. It was
    replaced by a within-track spectral check.
  - **Mid-morph overlap on the real render:** the wordmark slid under the DI mark at about 2.2 s.
    The mark and the wordmark now have their own springs (intro: mark first; outro: wordmark
    first). Checked on 12 dense stills across both transitions (commit `314f9dc`).
- **Real check:**
  - Real project `b330d37f` (DB copy), real cached Edge TTS lines, the real Pixabay track
    `no-copyright-music-2026-corporate-background-611659.mp3` (178.9 s, so the music loops), and
    Jenny.
  - Enhanced render 78–80 s, no fallback.
  - Wish: "Wishing you a productive and happy day of learning!"; farewell: "Don't forget to
    subscribe, and see you soon."
  - Intro 7.66 s + speech 176.02 s + outro 8.54 s = 192.22 s expected; the video is **192.28 s**.
  - Momentary loudness:

    | Section | Loudness |
    |---|---|
    | Greeting section | −25.3 LUFS |
    | Speech | −23.8 LUFS |
    | Farewell section | −22.1 LUFS |
    | Last 0.4 s (fading out) | −41.2 LUFS |

  - The video is in `data/tmp/brand-check/episode_brand.mp4`; the key frames are in `contact.png`.
- **Tests:**
  - `tests/test_brand_service.py` (8);
  - vitest `brand.test.ts` (2), vitest 44 passed in total;
  - `tsc` clean.
  - **Full suite: 1420 passed** (before the TSX-only morph fix; vitest and `tsc` were rerun after
    it).
