# Sprite pack for Alex and Lina: what to make (like game assets)

Yes: for the talking-characters mode (Phase 32) the app needs **one set of pictures per character, made once**. This is the shortest
list that gives smooth, game-like results. Start with Tier 1 only: it is enough for the first video; add the others later.

## 1. The rules for every picture

- **Transparent PNG** (alpha). If the tool cannot give transparency, use a **plain solid green background (#00B140)**, not white:
  Lina's dress is white. The app cuts the background out.
- **One canvas size for all pictures of both characters: 1280 x 1536 px.** The character is centred, from just above the head to
  mid-thigh (the top of the hair about 6% from the top edge), the same size and the same place in every picture.
- **Same body, same clothes, same lighting** in every picture of a character: Lina in the white mini dress, Alex in the navy suit,
  white shirt and black bow tie. Facing slightly toward the other person (about 15 degrees), like the visual-novel screenshots.
- **The head never moves between pictures** (same position, size and angle). Only the face changes (Tier 1 and 2) or only the arms and
  hands change (Tier 3). This is what lets the app mix them: any gesture can wear any face.
- Make the first picture (**calm, mouth closed**) perfect, then make every other picture by **editing that picture**: "keep everything
  identical, change only ...". Do not generate each one from scratch: the face drifts.

## 2. What to make, in order

### Tier 1: the first video (7 pictures per character, 14 in all)

| File name | What |
|---|---|
| `lina__calm__closed.png` | calm friendly face, mouth closed, arms relaxed in front (the **reference**, make it first) |
| `lina__calm__open.png` | the same, mouth open as if saying "ah" |
| `lina__smile__closed.png` | warm smile, mouth closed |
| `lina__smile__open.png` | smiling and speaking, mouth open |
| `lina__surprised__closed.png` | surprised (wide eyes, raised brows), mouth closed |
| `lina__surprised__open.png` | surprised, mouth open |
| `lina__blink.png` | the calm face with the eyes closed |

The same seven for Alex: `alex__calm__closed.png` ... `alex__blink.png`.

### Tier 2: more feeling (8 more per character)

`laugh`, `thinking`, `worried`, `serious`, each with `__closed` and `__open`
(for example `alex__worried__open.png`). Laugh: eyes narrowed, wide smile, mouth open for the open one.

### Tier 3: gestures (7 per character, one picture each)

Only the arms and hands change; the head is the one of `calm__closed`, so **one picture per gesture is enough** (the app puts any
face on it). Name: `<character>__gesture-<name>.png`.

| Name | What |
|---|---|
| `gesture-talk` | one hand raised, open palm, explaining |
| `gesture-point` | pointing to the side with one hand |
| `gesture-think` | hand on chin |
| `gesture-open` | both hands open, a small shrug ("who knows?") |
| `gesture-heart` | hand on the chest (sincere, "thank you") |
| `gesture-listen` | arms folded or hands together, listening |
| `gesture-wave` | waving hello (also used for the intro and the goodbye) |

**Counts:** Tier 1 = 14, Tier 2 = 16, Tier 3 = 14, so **44 pictures for the pair** in all (the 14 of Tier 1 are enough to start).

## 3. Prompt templates (for ChatGPT image editing)

First picture (once per character, from your existing sheet): "Use this character exactly (same face, same hair, same outfit).
Waist-up to mid-thigh, facing slightly toward the left, calm friendly face, mouth closed, arms relaxed, transparent background,
1280x1536, photorealistic, soft even lighting."

Every other picture: "Edit the attached picture. Keep the head position, the size, the hair, the clothes, the body, the
lighting and the background exactly identical. Change only <the face: warm smile, mouth open as if speaking / the eyes: closed /
the arms: one hand raised with an open palm>. Same canvas size."

If a picture comes back with the head moved or the face changed, discard it and edit the **reference** again (not the damaged one).

## 4. How to hand them over

Copy the files into `data\library\sprites_inbox` (the importer arrives with Phase 32.1). The app checks that every picture has the
same canvas size, aligns it to `calm__closed` and tells you which file it refused and why. Tier 1 is enough for me to build and show
the first talking video; the rest can follow while you review it.
