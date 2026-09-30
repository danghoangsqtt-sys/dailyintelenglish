# Task 20.2f — Spike v4: character-first, Vietnamese students, the r3 watercolor look, one-pass scenes

- **Status:** design (Coder, doc-first, 2026-09-30). **The real run needs the owner's GPU.**
  It goes through the runbook `docs/operations/owner-runbook-2026-09-30-r6.md`.
- **Owner:** Coder
- **Authorization:** the owner's 20.2e verdict and three answers, 2026-09-30.
  - *"cần tập trung vào xây dựng nhân vật, thiên hướng người Việt Nam màu sắc tươi sáng…"*
    ("focus on building the characters, Vietnamese-leaning, bright colours").
  - The "much better" first result is **the r3 watercolor run (20.2b)**, not r2.
  - Method: **one-pass generation** (character + scene in the same pass).
  - Roster: **a female student (~20) and a male student (~20), Vietnamese.**

## Why

The owner judged four spikes. What survived:

| Kept | Rejected |
|---|---|
| r3 (20.2b) look: *"hand-painted 2D anime illustration, soft watercolor background, warm natural sunlight, gentle pastel palette, cozy whimsical atmosphere, clean line art"*, and on r3 **base looked prettier with more soul than Lightning** | r4 cel-animation v2; r5 anime (Animagine) A and B |
| Captions / frame layout (20.2d, r4) | Inpainting a character into a pre-made scene (M2): odd scale, the character sinks into the scene (r4/r5) |
| Strict pose was preferred **over loose**, but only within M2 | M1 collage |

## Design decisions

- **D20.2f-a: model — SDXL base 1.0** (30 steps, CFG 6), as on r3's preferred base
  column. No new download: everything is cached.
- **D20.2f-b: two style variants of the r3 preset.** The owner asked for bright colours
  and the r3 preset says "pastel", so both are rendered:
  - `r3_watercolor`: the exact r3 preset (the anchor the owner liked);
  - `r3_bright`: the same preset, with "gentle pastel palette, cozy whimsical
    atmosphere" → "bright cheerful colors, vivid clean colors, cheerful atmosphere".
- **D20.2f-c: the characters** (invented; Vietnamese; bright, simple outfits; no
  accessories that drift):
  - **female student:** "a young Vietnamese woman university student, about 20 years
    old, long straight black hair, warm brown eyes, wearing a bright yellow sweater and
    blue jeans";
  - **male student:** "a young Vietnamese man university student, about 20 years old,
    short neat black hair, warm brown eyes, wearing a bright teal hoodie over a white
    t-shirt and dark jeans".
- **D20.2f-d: character-first order**, the owner's priority.
  - **P1:** per style × character, 2 head-and-shoulders candidates on a plain light
    background (the IP reference pool).
  - **P2 (IP-Adapter plus-face, scale 0.45, reference = candidate 1):** the character
    sheet, 4 images:
    - a full body front, standing;
    - 3 portraits (neutral, happy, surprised), each on its own seed.
- **D20.2f-e: one-pass scenes** (the owner's method choice; how r2 worked).
  - In the same P2 worker, per style × character: **2 scenes** generated as one picture
    (text2img + IP).
  - Medium-shot wording fixes the scale ("medium shot, upper body and waist visible").
  - The character is placed left of centre ("standing on the left side of the picture"),
    which keeps the vocab-card corner clear.
  - Scenes:
    - **female:** "waving hello in a bright university library"; "reading a book at a
      cozy Vietnamese street café with plants";
    - **male:** "pointing at a whiteboard in a sunny classroom"; "talking with open hands
      at a cozy Vietnamese street café with plants".
  - **No inpaint, no ControlNet, no cut-out:** nothing is pasted, so nothing can sink or
    haloe.
- **D20.2f-f: frames.** Each scene becomes a 1280×720 frame with the approved outline
  captions (the 20.2c `frame_mockup`). The female scenes use speaker "Linh", the male
  scenes "Minh".
- **D20.2f-g: known limit, stated up front.** One picture holds **one** IP-identified
  character. Two IP-identified characters in one frame is a separate, harder problem;
  dialogue shots show the active speaker.

## Allowed files

- **New** `scripts/spike_character_v4.py` (reuses the 20.2b/20.2c helpers).
- **New** `docs/operations/owner-runbook-2026-09-30-r6.md`, this card, and PHASE-STATE.

**Not touched:** `scripts/image_worker.py` (no change needed), `app/`, `tests/`,
`frontend/`, `video-renderer/`, requirements, and the DB.

## Verification here (cloud, no GPU, no Hub)

- The runner end to end on the tiny random SDXL with `--allow-cpu --skip-ip`, covering:
  - counts;
  - both styles;
  - both characters;
  - frames;
  - sheets.
- The IP-Adapter paths run only on the owner's machine.

## Owner questions the run answers

1. `r3_watercolor` or `r3_bright`?
2. Is each student clearly drawn and recognisably Vietnamese? Pick candidate 1 or 2 per
   character.
3. Does each character stay the same person across the sheet and the scenes?
4. Scale and presence in the scenes — natural now, and not sinking?
