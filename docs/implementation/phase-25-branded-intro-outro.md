# Phase 25 — Branded intro and outro: morph slides with a female voice greeting (ENH-017)

**Status:** planned 2026-10-06 (`/vp-auto`, owner request).
**Version:** closes at 1.3.0-beta together with Phase 22, if Gate B-18 passes.

## 0. Owner request and decisions (2026-10-06)

> "tạo cho tôi 1 slide video hiệu ứng morph chuyên nghiệp mở đầu cho mỗi video và lời chào đầu video
> giọng nữ Welcome to Daily Intel English Channel! và một lời chúc bằng tiếng Anh bất kỳ như chúc học
> tốt, chúc bạn thành công ... Tương tự với phần kết thúc Video cũng cần sự đẹp và chuyên nghiệp đồng bộ"

| ID | Decision |
|---|---|
| D52 | Every Enhanced video opens with a professional **morph-style slide sequence** and a **female voice**. The voice says "Welcome to Daily Intel English Channel!" followed by an English **wish** chosen per episode (good luck with your studies, wishing you success, ...) |
| D53 | The **outro matches** the intro (same look, same voice): morph slides plus a spoken **farewell** ("Thanks for watching Daily Intel English! ...") |
| D54 | **No logo file yet.** Claude designs a typographic logo ("Daily Intel English" + a simple mark) in the app's colours. It can be replaced by a real logo later |
| D55 | **The voice is picked by the owner** from 3 female samples (spike 25.1) |

## 1. What exists today

`Episode.tsx` has a static **Intro** (2.5 s: title, speakers, `[CEFR] topic` on a flat midnight
background with fades) and a static **Outro** (5 s: CTA text). Both are silent apart from the music
bed (Phase 22.4). The Standard (ffmpeg) renderer has no intro or outro, and this phase leaves it
unchanged: Enhanced is the default renderer.

## 2. Design

### Morph

"Morph" here means PowerPoint-style transitions: the **same elements stay on screen and smoothly
change position, size, colour and shape** between slides, with spring easing, instead of cutting
or fading between unrelated slides. It is built in Remotion with `spring`/`interpolate`.

### Intro (about 6–8 s; it follows the voice length)

1. **Brand.** The logo mark and the wordmark "Daily Intel English" sit centred and large on a
   rich gradient background with soft animated shapes.
2. **Morph to the episode.** The logo shrinks into the top-left corner and the wordmark becomes a
   header. The background shapes glide to new positions and colours. The episode title, the CEFR
   badge, the topic and the speaker chips rise into place.
3. **The wish** appears as a line under the title while the voice says it. Then the slide
   dissolves into the episode.

The **voice** is the greeting plus the wish, starting about 0.4 s in. The intro length is
`max(6 s, 0.4 + voice + 1.0 s)`.

### Outro (same style, mirrored)

The last frame dissolves into the brand background. The logo morphs back to the centre with
"Thanks for watching!". Subscribe / Like / Share chips pop in, then the next-episode line. The
voice says the farewell plus a short sign-off. The music bed already fades out on the last frame
(22.4).

### Texts

There is one curated list of wishes and one of farewells, short and natural. The pick is
deterministic per project (a hash of the project id), so a re-render keeps the same lines. Each
episode varies.

### Audio

- The greeting and farewell are synthesised with the chosen Edge TTS female voice and cached per
  text + voice.
- The full-video soundtrack (22.4) places the greeting in the intro and the farewell in the
  outro, and the music ducks under them too.

### Fonts

A clean, bundled open-licence font (OFL) for the brand texts, not Arial. The download needs the
owner's approval; that request is part of 25.1.

## 3. Tasks

| Task | What | Accept when |
|---|---|---|
| 25.1 | **Spike:** 3 female Edge TTS voice samples (greeting + wish, farewell). A rendered preview MP4 of the morph intro + outro on a real project | owner picks the voice and approves the look (or asks for changes) |
| 25.2 | **Build:** texts + per-episode pick; greeting/farewell TTS (cached); variable intro/outro length; `BrandIntro`/`BrandOutro` morph components; soundtrack with the greeting/farewell voices ducking the music; tests | tests green; real render on 1 project |
| 25.3 | **Gate B-18:** the owner watches 2 real episodes | owner PASS |
