# Task 28.2: Character reference sheets (a turnaround sheet + detailed prompts per view)

## Owner request (2026-10-06)

Make the picture set for the woman and the man to go in the character profile, like the sample sheet
the owner sent (full body front, full body back, face front, face profile, face three-quarter, head from
above) with a **detailed prompt for each view**: the face from each angle and the body.

- **Man:** the round 6 `N3_soft` face (seed 42). Muscular but lean, slim-fit, **180 cm, 80 kg**. All
  black outfit (shirt, trousers, shoes).
- **Woman:** the round 4 face (E1, seed 21), very long straight black hair. A slender hourglass figure,
  **160 cm, 50 kg**. All white outfit (blouse, trousers, shoes).
- **Scope decisions:**
  - Both are fully clothed. The woman's figure is drawn as a slim hourglass in modest clothes; the very
    large bust and the swimwear of the owner's references are NOT reproduced, because the sheets go into
    the profile of an English-learning channel.
  - The man's physique is drawn from the clothed, slim-fit description (the reference photo is shirtless).
  - The faces are the generated faces of the two picks, carried to every angle by the face IP-Adapter
    (`ip-adapter-plus-face_sdxl_vit-h`, already in the cache). No real person's photo is a face reference.

## Paths

- `scripts/character_sheet_realvis.py` (new; the generator, run in `venv-image` outside the app)
- `docs/operations/phase28-characters/` (new: `woman_sheet.png`, `man_sheet.png`, the panels, `prompts.md`)

## File-Level Plan

1. `character_sheet_realvis.py` loads RealVisXL (the round 4 loader), the fp16-fix VAE and the face
   IP-Adapter. The reference face is cropped from the picked round 4 / round 6 image.
2. **Six panels per character** (the sample's layout: two tall panels on the left, a 2 x 2 block on the
   right): `full_front`, `full_back`, `face_front`, `face_profile`, `face_three_quarter`, `head_top`.
   - Face panels: face IP-Adapter scale about 0.6 so the identity holds across angles.
   - `full_*` panels: scale about 0.5, because the face is small; the body words carry the figure.
   - `full_back` and `head_top` have no visible face: IP-Adapter off, hair and outfit by text.
3. **Prompts:** each panel has a generation prompt of at most 77 CLIP tokens (counted with the real
   tokenizer, `--tokens-only`) and a negative against nudity, swimwear, cleavage, extra people and
   other outfit colours. The **long, detailed** description of the face from that angle and of the body
   goes to `prompts.md`, which is what the owner asked for as the detailed prompt.
4. Compose the panels into one sheet per character (PIL), label each panel.
5. Judge by eye: the same person in every panel, the outfit single colour, the figure and height
   described, the hands without artefacts, no nudity.

## Verification

- All prompts within 77 tokens (script check).
- 12 panels (2 x 6) are made, then looked at one by one; failed panels are redone with another seed.
- The owner approves the two sheets or says what to change.

## Next in Phase 28 (renumbered)

28.3 Recipes + re-tuned colour / extra-person checks (single-colour outfits, RealVisXL in the worker);
28.4 Redo the library (the two characters from the sheets, the 55 scene plates); 28.5 Gate B-20.
