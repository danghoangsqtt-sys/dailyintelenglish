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

## Result (2026-10-06), awaiting owner approval

- `docs/operations/phase28-characters/{woman,man}_sheet_2000.png` (full size `*_sheet.png`), the six
  panels per character, and `prompts.md` (detailed description, generation prompt, negative per view).
- **Changes from the plan:**
  - an OpenPose ControlNet (skeletons from `geometry.py`) was added, because the face IP-Adapter alone
    gave random poses and a grey shirt on the man;
  - the "head from above" panel was dropped (the model drew the face instead: two tries) and replaced
    by a **smile** panel, which is also the talking-video expression;
  - a true 90-degree profile needed the skeleton to hide one eye and one ear, and a weaker face
    reference (0.2).
- **Known flaws, shown honestly to the owner:**
  - the man's full-front panel is mid-stride and his lower foot is cropped at the edge;
  - the woman's back view is cut at the ankles;
  - his front and back panels have different backgrounds (grey and light).
  The face holds across all six panels for both characters; outfits are single colour.
- Height and weight (160 cm / 50 kg, 180 cm / 80 kg) cannot be measured in a picture: they are in
  `prompts.md` and shown by the figure only (the man is clearly muscular and lean).

## Owner feedback on the sheets (2026-10-06), fix round

The owner sent 5 clothed reference photos of well-proportioned people and said both body proportions
are wrong:

- **Woman:** the hips and buttocks are too big, the bust too small. References: a fuller bust, a narrow
  waist, slim hips, a fitted short-sleeve white blouse tucked in.
- **Man:** the shoulders are too high and the muscles are not clear. References: a broad chest, defined
  biceps and shoulders, a fitted shirt that shows the muscle, a V-shaped torso.

**Cause found in `app/services/visuals/geometry.py`:** the skeleton puts the shoulders only 0.1 head
below the neck (a shrug), the hips at 3.0 and the knees/ankles too short, and my wide-leg trousers
widened the hips.

**Fix (script only, not the app):**

- Full-body skeleton: shoulders about 0.95 below the nose; hips at 3.3 with a narrower hip width for
  the woman; knees 4.9, ankles 6.5 (a 7.4-head figure); the man's shoulder width kept broad.
- Prompts: the woman "full bust, slim waist, narrow hips, fitted white blouse tucked in, slim straight
  white trousers" (clothed and buttoned, no open collar); the man "muscular broad chest, defined
  biceps, V-taper torso, fitted short-sleeve black shirt". The negative adds "wide hips, flared
  trousers, rolled sleeves, hunched shoulders".
- Only the 2 full-body panels per character are redone (3 seeds), then the sheets are recomposed.
- Real photos are not model inputs; the words describe proportion only.

### Fix round 2 (2026-10-06)

Man: shoulders natural and muscle clear (seed 21), but one back view was shirtless (rejected, "bare back"
added to the negative). Woman: the blouse was still loose and the bust not fuller, and the shoes were cut
off for both. Changes: "tight short-sleeve white blouse tucked in"; the figure is drawn smaller in the frame
(nose 0.05, head unit 0.115) so the shoes fit; both characters' full-body panels redone at 3 seeds.

### Fix round 3 (2026-10-06)

The woman is good (fitted short-sleeve blouse, narrow hips, shoes in frame). The man's head top was cut
off and one front view was a torn crop top: his full-body framing is now nose 0.085 / unit 0.105, and
"crop top, torn clothes" are in his negative. Only his two full-body panels are redone.

### Result after the fixes (2026-10-06), awaiting owner approval

Sheets recomposed (`docs/operations/phase28-characters/*_sheet_2000.png`, `prompts.md` regenerated).
- **Man:** shoulders natural, biceps and chest clearly muscular, head and shoes in the frame, front and
  back backgrounds match.
- **Woman:** fitted short-sleeve blouse tucked in, narrow hips, slim straight trousers, shoes in frame.
- **Not fully achieved, stated to the owner:** the bust reads only moderately full (the model still
  draws a modest bust under a fitted blouse); her head top is a little tight in the back view.

## Owner feedback on the fixed sheets (2026-10-06), fix round 4

- **Woman:** the bust is far too small for the channel's direction. She must have a clearly fuller
  bust, in the same fitted, buttoned white blouse.
- **Man:** the shoulders are still a little high and the neck is short. The owner wants the look of a
  Korean man: a long neck, sloped broad shoulders, a slim waist.

**Plan (script only):**

- Man skeleton: a longer neck (the neck joint 0.85 below the nose, was 0.65), shoulders lower
  (1.25, was 0.95) and a little less wide; elbows, wrists, hips, knees and ankles shifted to keep a
  figure of about 7.6 heads. Prompt: "long neck, sloped broad shoulders, slim waist, lean muscular".
- Woman prompt: "curvy hourglass figure, large bust, slim waist, blouse fitted across the chest" (clothed,
  buttoned, no open collar); the negative adds "small bust, flat chest". The prompt budget stays at
  77 tokens, so lower-value words are traded out.
- Redo the 2 full-body panels per character at 3 seeds, look at them, then the man's close-ups if
  the neck still reads short.

### Result of fix round 4 (2026-10-06), awaiting owner approval

- **Man:** a long neck, sloped shoulders, a slim V-taper with defined arms: the Korean-idol proportion the
  owner described (front seed 21, back seed 42).
- **Woman:** the bust is only slightly fuller (seeds 21 and 42). Rewording the prompt (figure words first,
  synonyms) did not change it much: with this model and a text prompt the bust under a fitted blouse
  stays modest. Options for the owner: accept it, or use a body-shape control (an extra download
  and a hand-drawn torso map) or a different checkpoint.

## Owner decision (2026-10-06): body map approved, the current look kept as the fallback

The owner agreed to option 1 (draw a body map and add the control model it needs) and to option 2
(add a body-shape model), and to **keep the current sheets as the approved fallback**.

- **Option 1, now:** `xinsir/controlnet-depth-sdxl-1.0` (Apache-2.0, commercial use allowed), loaded
  next to the OpenPose control (diffusers multi-ControlNet). The script draws a **depth map of the
  torso** (grey-scale: a rounded chest with two raised bust forms, a narrow waist, narrow hips, and a long
  neck/sloped shoulders for the man) that is used only for the full-body and the face panels that show the
  chest. A fuller bust then comes from the shading the control produces, not from a prompt word.
- **Option 2, after:** a licence check first (commercial use) for any body-shape LoRA; nothing is
  downloaded until the licence is read.
- Clothed, buttoned blouse; the depth map is a smooth torso shape, not a nude body.
- Acceptance: the owner approves the bust size on the woman's sheet. The previous sheets stay in git
  history (commit "Task 28.2 sheets after round 4").

### Body map result and a speed fix (2026-10-06)

- The first image with the depth control confirmed the method: a visibly fuller bust, a narrow waist and
  narrow hips, in the same fitted buttoned blouse.
- **Problem found:** OpenPose and depth ControlNets together overflowed the 12 GB card: 1173 s for one
  image (about 20 times slower). **Fix:** one ControlNet at a time. The depth map already holds the
  silhouette, so the woman's full-front panel uses the depth control alone (scale 0.9) and the other
  panels keep the skeleton. Her frame is lowered (nose 0.07) so the head is not cut.

### Depth alone failed (2026-10-06)

The depth ControlNet alone (the silhouette without the skeleton) broke the figure in 3 of 4 images
(a floating torso, wrong limbs): rejected, not shown to the owner as a candidate. OpenPose + depth
together is the only variant that worked (the first image), at about 20 minutes an image because the two
controls plus the UNet overflow the 12 GB card. The script is back to "both"; two seeds are run in the
background (seeds 7 and 21). Option 2 (a body-shape LoRA) is not pursued: see the answer to the owner.

### Result of the body map (2026-10-06), awaiting owner approval

Pose + depth, seeds 7 and 21 (about 1000 s each): both show a visibly fuller bust, a narrow waist and
narrow hips, with the head and shoes in frame; seed 21 is on the woman's sheet (full front). The other five
woman panels are unchanged. The depth map is used only for the full-front panel: in the close-ups the chest
is out of frame, and in the back view it is not needed.

## Owner decision (2026-10-06): Minh approved; Lan's bust bigger

- **Minh (man): APPROVED** (long neck, sloped shoulders, lean muscular, the current sheet). Locked.
- **Lan (woman):** the bust must be a big size, larger than the body-map result. Plan: the bust forms of the
  depth map grow (the size factor 1.0 -> 1.4, a little further apart); the prompt keeps "large full bust".
  She stays in the fitted, buttoned white blouse and keeps natural proportions (a narrow waist and hips),
  with no open collar. Only her full-front panel is redone (pose + depth, seeds 7 and 21, about 17
  minutes each).
