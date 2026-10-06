# Phase 25 spike — morph intro and outro + female voice samples (Task 25.1)

**Date:** 2026-10-06.
**Files** (`data/tmp/brand-spike/`, not in git):

- `brand_preview.mp4`: 16.6 s = intro 7.6 s + a 1.5 s placeholder for the episode + outro 7.5 s.
  It uses the real project "Good Morning" (A2, "How do you start a new day?", Alex + Luna) and
  the Ava voice. Remotion render: 55 s.
- `contact.png`: 8 key frames.
- Voice samples: `<voice>_greeting.mp3` and `<voice>_farewell.mp3`.

## Voices (Edge TTS, female)

| Voice | Greeting | Farewell |
|---|---|---|
| `en-US-AvaMultilingualNeural` (US, warm, newer) | 6.19 s | 5.66 s |
| `en-US-JennyNeural` (US, the app's current female voice) | 6.53 s | 6.55 s |
| `en-GB-SoniaNeural` (British) | 6.14 s | 6.24 s |

- **Greeting:** "Welcome to Daily Intel English Channel! Wishing you a wonderful time learning
  English today."
- **Farewell:** "Thanks for watching Daily Intel English! Keep practising, and see you in the next
  lesson."

## The look (proposed)

The background is a deep navy-to-indigo gradient with three soft blurred colour blobs (violet,
cyan, pink/amber) that drift slowly and glide to new places at each morph.

The logo is a typographic mark: a "DI" rounded square in a violet→cyan gradient, with the wordmark
"Daily Intel / ENGLISH".

**Intro:**

1. The logo pops in, centred and large.
2. It morphs (springs) into a small top-left header while the blobs move.
3. The title rises in.
4. The CEFR badge, topic and speaker chips appear.
5. The wish appears in italics.
6. Fade into the episode.

**Outro:**

1. The header logo morphs back to the centre.
2. "Thanks for watching!" appears.
3. The Like / Subscribe (red) / Share chips pop in one after another.
4. "See you in the next lesson".
5. The voice farewell plays and the outro fades out.

## Found while checking the frames

- **The header wordmark is small and cramped** ("ENGLISH" at ~12 px). It will be enlarged in 25.2.
- **The font is the system Segoe UI.** For a branded look, a bundled open-licence font (for
  example Montserrat or Poppins, SIL OFL) is proposed. It needs a small download (~200 KB) with
  the owner's approval.

## Owner decisions needed

1. **The voice:** Ava, Jenny or Sonia.
2. **The look:** keep it, or say what to change (colours, logo, layout, speed).
3. **Bundled font:** approve the Montserrat/Poppins download, or keep the system font.
