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

## 5. What the first pack taught us (2026-10-08)

- **Direction:** in the video the **first speaker (Alex) stands on the left and faces right**, the second (Lina) stands on the right and faces left.
  (The first prompt said the opposite; the packs were turned the right way afterwards.)
- **Alignment:** an AI image editor redraws the whole picture, so the pictures of Alex's first pack drifted: the torso moved 20 to 100 px
  between pictures and the hands changed place, which would make the character jump when the face changes. Lina's first pack was
  consistent (torso within 5 px). To make every pack consistent: edit with a **mask** (the face only, or the arms only) and paste the masked
  region back onto the reference with Pillow, so everything outside the mask is identical.
- **Check:** `venv\Scripts\python scripts\check_sprites.py <character>` compares every picture with `<character>__calm__closed.png`
  (canvas, transparent corners, head top within 6 px and head middle within 10 px, torso edges within 8 px, silhouette within 4%) and exits with 1 if any picture fails.
- **Hands:** an expression picture keeps the hands where the reference has them; only a gesture picture changes the arms.
- **Result of the first Alex pack (2026-10-08):** of 22 pictures only `calm__closed` (the reference) and `smile__closed` passed; the other 20
  failed and were deleted. They are redone with `docs/operations/Prompt_Generate_Sprites_Alex_Redo.txt` (masked edits, pasted back onto the
  reference). `check_sprites.py <character> --list-failed` prints the names of the failing pictures.

## 6. Lina's expressions through head crops (2026-10-08)

The image tool refused every edit of Lina's full-figure base picture (its safety filter, for the body). Her expression pictures (tiers 1
and 2) are therefore made from a **crop of the head and neck** only: `scripts/sprite_face_tools.py prepare lina` writes the crop and the
face position, the image tool edits the expression on the crop (`docs/operations/Prompt_Generate_Lina_Faces.txt`), and
`sprite_face_tools.py compose lina` pastes the edited face back into `lina__calm__closed.png` inside a feathered ellipse, keeping the base's
transparency: every picture is aligned with the base by construction. This cannot make the **gestures** (tier 3: they need new arms), so
Lina has none for now and the video uses her base picture where a gesture would be shown.

### 6b. Two ways to make Lina's pictures on ChatGPT web (2026-10-08)

- **Head crops** (face only, always aligned): `scripts/sprite_face_tools.py prepare lina` also writes a square `lina_head_edit_input.png`
  (web tools return squares; `compose` cuts the padding off again). Prompts: `docs/operations/Prompt_ChatGPT_Web_Lina_Faces.txt`.
- **Full figure** (expressions and gestures in one picture, no crop): `docs/operations/Prompt_ChatGPT_Web_Lina_FullBody.txt`. The web
  pictures go to `data/assets_sprites/web_raw/` (flat green `#00B140` background, any size);
  `scripts/sprite_web_import.py lina` keys out the green, finds the face, scales and places the figure on the 1280 x 1536 canvas by the face
  and then by the overlap of the head-zone silhouettes, writes into `sprites_inbox` and runs `check_sprites.py`. Pictures that still fail are
  made again. If the web tool refuses a full-figure edit, use the head crops for the expressions.
