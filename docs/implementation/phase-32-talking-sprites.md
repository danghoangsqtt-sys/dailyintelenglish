# Phase 32: Talking characters as sprites (visual-novel style), ENH-023

Owner idea (2026-10-07): instead of drawing or importing a new picture of Alex and Lina for every shot, make the two characters
**sprites made once** (high quality pictures made outside the app) that change expression, move their mouth with the speech
(lip-sync), enter and leave and take turns, like the characters of a visual novel (the two screenshots the owner attached), over the
owner's high-quality scene backgrounds.

## 1. Why it fits

- The speech already has **word timestamps** and the storyboard already has an **expression and an action per beat**: everything
  needed to choose a face and to open the mouth at the right time exists.
- The face and the clothes never drift (the pictures are made once and approved once), which is the weak point of generated shots.
- A talking video then costs **no GPU time** and renders in about two minutes (like the podcast modes).
- The Shot Library stays useful for what sprites cannot do: wide shots (walking through a market), scenes where they sit, and the
  illustration inserts.

## 2. What a sprite set is

Per character, transparent PNGs on **one canvas size** (for example 1024 x 1536, half body, facing the other person), the body, clothes
and pose identical in every picture; only the face changes:

| Picture | Minimum set | Full set |
|---|---|---|
| Expressions | calm, smile, surprised | calm, smile, laugh, surprised, thinking, worried, serious |
| Mouth | closed and open for each expression | closed, half and open |
| Blink | one picture with the eyes closed | one per expression |
| Gestures (optional) | none | 2 or 3 arm poses (talking with a hand, pointing, hand on chin), each closed and open |

Minimum set: 3 x 2 + 1 = **7 pictures per character** (14 for the pair). Full expression set: 15 per character.

**Gestures need one picture each:** the head is identical in every picture, so the importer takes the face region (the pixels that
differ between the expression pictures) and lets any gesture picture wear any face, with a feathered mask. The full pack is 44 pictures
for the pair; `docs/operations/sprite-asset-spec.md` lists them, the canvas (1280 x 1536, transparent PNG) and prompt templates.

Names: `<character>__<expression>__<mouth>.png` (`alex__smile__open.png`, `lina__calm__closed.png`, `lina__blink.png`,
`alex__gesture-hand__open.png`) in the inbox folder `data/library/sprites_inbox`, imported like the shot pictures.

## 3. How the video is made

- **Layers:** background (the scene plate of the beat, a short cross-fade when the scene changes), the two sprites (the first speaker
  on the left, the second on the right), the name label, the captions and the vocabulary card (already there), the chapter bar.
- **Places:** the first speaker (Alex) on the left facing right, the second (Lina) on the right facing left.
- **Turns:** the speaking sprite is full colour and a little larger with a small hop when the turn starts; the listener is dimmed and
  still. A sprite **enters** (slide and fade, 12 frames) at the first line of a scene and **leaves** at its end.
- **Expression:** the beat's expression (calm when there is none), refined per line by simple rules (a question mark thinks, an
  exclamation smiles, "oh no" worries); the owner can override a line later.
- **Lip-sync:** the mouth opens and closes from the **loudness of the speech** (RMS of each line's audio per frame, thresholds with a
  hold so it does not flicker); with three mouth pictures the loudness picks closed, half or open. Pauses between words close it.
- **Life:** a slow breathing bob, a blink every 3 to 5 seconds (a fixed pseudo-random pattern, so a render is repeatable), an optional
  gesture picture on a stressed word or a beat action.
- **Cutaways:** an insert still cuts to its full-frame illustration; a beat with a library picture of both (a walk in the market) may
  show it instead of the sprites.

## 4. Tasks

| Task | What | Accept when |
|---|---|---|
| 32.1 | **Sprite library:** model (`character_sprites`: character, expression, mouth, picture), inbox import by file name (PNG with alpha, equal canvas size checked, cut-out by the worker when the picture has no alpha, alignment to the calm-closed picture), a Sprites page | tests; the owner's first set imports |
| 32.2 | **Speech to mouth and expression:** per-line loudness curve (ffmpeg / pydub) to mouth states per frame; the expression plan per line (beat expression plus the rules) | pure functions tested; the plan printed for the demo episode |
| 32.3 | **Remotion composition `Sprites.tsx` + `spriteTimeline.ts`:** layers, turns, enter and leave, blink, breathing, mouth; props schema; vitest | vitest green, `tsc` clean |
| 32.4 | **API and Step 5:** `visual_mode = "podcast_sprites"` (Enhanced only), the props builder (backgrounds from the storyboard beats, sprites, mouth and expression plans), a chip "Podcast: talking characters" | tests; browser test |
| 32.5 | **Real render** of the demo episode with the owner's first sprite set | owner sees the video |
| 32.6 | **Gate B-22:** the owner compares it with the story-picture video | owner PASS |

## 5. Decisions and risks

- **First pack findings (2026-10-08):** Alex's 22 pictures (all tiers) are complete and look right but are not aligned with each other
  (torso 20 to 100 px, hands moved); Lina's old pack was aligned. `scripts/check_sprites.py` measures this; the importer must also align
  each picture to the reference by its torso (scale and shift) and may take only the head of an expression picture.
- **Consistency of the variants is the risk:** a variant where the body moved a few pixels shows as a jump. The importer aligns each
  picture to the calm-closed one and the composition cross-fades faces for 2 frames; pictures that cannot be aligned are refused with
  the reason. Ask the image tool to "change only the face, keep everything else identical".
- Half-body sprites suit **seated and standing talk**; a walking scene still needs the library pictures.
- The composition needs the **Enhanced (Remotion) renderer**; the Standard (ffmpeg) renderer cannot do it.
- Open owner questions: sprite size and framing (waist-up is proposed), whether to start with the minimum set, and whether the
  speaker's gesture pictures are wanted in the first version.
