# Task 20.2f — Spike v4: character-first, Vietnamese students, the r3 watercolor look, one-pass scenes

- **Status:** implemented (Coder, 2026-09-30). Design commit `0fc4459`; see "Implementation
  notes" at the end. **The real run needs the owner's GPU.**
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
- `scripts/image_worker.py`: `prompt_tokens` / `prompt_truncated` in the generate and
  encode responses (finding F3 below; added during implementation).
- **New** `docs/operations/owner-runbook-2026-09-30-r6.md`, this card, and PHASE-STATE.

**Not touched:** `app/`, `tests/`,
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

## Implementation notes (Coder, 2026-09-30)

- **Finding F3: CLIP prompt truncation hurt earlier spikes.**
  - SDXL's CLIP encoders read 77 tokens (75 + BOS/EOS) and **silently drop the rest**.
  - Counted with OpenAI's CLIP BPE (`openai/CLIP` `simple_tokenizer.py` +
    `bpe_simple_vocab_16e6.txt.gz`, fetched from GitHub):

    | Run | Asset prompt tokens | What was dropped |
    |---|---|---|
    | r3 (20.2b) | 72–80 | mostly only "no text, no logo" |
    | r4 (20.2c) | 95–105 | **the view/expression tail**; this explains the six near-identical assets |
    | r5 (20.2e) | 87–99 | **the style and quality tags** at the end of every prompt |

  - The first draft of this spike's prompts ran **81–108**. The prompts were compressed,
    and "no text, no logo" moved to the negative only (base has CFG 6, so the negative
    acts). **Every v4 prompt is now 52–65 tokens.**
  - The worker now reports `prompt_tokens` and `prompt_truncated` per image, so a
    truncation shows up in `L_*.json` instead of being invisible.
- **Verification (cloud, tiny random SDXL, CPU, `--allow-cpu --skip-ip`).**
  - 3/3 phases ok, with the right counts:
    - 8 candidates;
    - 16 sheet images;
    - 8 one-pass `text2img` scenes;
    - 8 1280×720 frames;
    - 3 sheets.
  - Base CFG with the negative prompt applied everywhere.
  - Token fields present on every image. On the tiny test tokenizer the counts are
    meaningless; the real counts are above.

