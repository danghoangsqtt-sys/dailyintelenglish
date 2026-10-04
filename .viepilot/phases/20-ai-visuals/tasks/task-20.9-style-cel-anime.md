# Task 20.9 — Style switch: r3 watercolor → cel-anime (owner references, 2026-10-04)

**Trigger:** owner, 2026-10-04 (`/vp-audit`): the generated images are "still very poor,
not the cartoon style I want". Three reference images were attached (summarised below).
**Supersedes:** spec O2 (`r3_watercolor` channel style), Phase 20 feature spec §2.

## 1. Reference analysis (what the owner wants)

| Aspect | References (all three) | r9 output (`owner-runs/20261001-r9`) |
|---|---|---|
| Rendering | 1990s hand-drawn cel anime film still: clean dark ink outlines, flat 2-tone cel shading, light film grain | soft watercolor wash, almost no outlines, airbrushed gradients |
| Colour | saturated natural colours: leaf greens, sky blue, white cumulus, warm sunlight, earthy browns/creams | pastel, washed out, overexposed whites, low contrast |
| Face | soft round/oval face, small simple nose (one line), medium eyes with dark iris + one highlight, rosy cheeks, natural open smile | long-chin semi-realistic webtoon face, heavy eye makeup, glossy skin |
| Hair | dark hair in solid shapes with a few strands, wind movement | fine strand-rendered, glossy |
| Outfit | simple natural fabrics (linen shirt, cotton dress, knit), folds in a few lines | plain sweater/shirt — fine, but colours drift (10 mismatches/run) |
| Background | lush painted gouache scenery: rolling hills, trees with clustered foliage, wildflowers, blue sky with cumulus, cottages | blurry watercolor interiors, blown-out windows |

**Root cause:** the style prefix literally asked for "soft watercolor background, gentle
pastel palette" and the negative did not exclude watercolor/pastel/semi-realism. The model
(SDXL base 1.0) can do the reference look; it was being steered away from it.

## 2. Measured comparison (RTX 3060, same seeds 11 and 23, 30 steps, CFG 6)

Evidence (deleted 2026-10-04 at the owner's request; reproducible with the script): `owner-runs/style-ghibli-20261004/compare_s11.png`, `compare_s23.png`, `log.json`
(script `scripts/spike_style_ghibli.py`). Columns: old | sdxl | lora | anim.

| Variant | Result |
|---|---|
| old: SDXL base + r3 watercolor | reproduces the complaint (washed out, webtoon faces) |
| **sdxl: SDXL base + new cel-anime recipe** | **matches the references**: outlines, cel shading, round simple faces, hills/clouds/wildflowers. ~25 s/image, no new dependency |
| lora: + ntc-ai "Studio Ghibli style" slider LoRA (MIT) @ 2.0 | almost identical composition, older/duller colours; needs `peft` |
| anim: Animagine XL 4.0 tag prompt | 1990s shōjo anime (big eyes) — not the reference look; best outfit-colour adherence |

Prompt-only text-to-image swaps outfit colours between two people (SDXL attribute bleed).
The production shot pipeline already counters this with masked per-person IP-Adapter faces,
two-skeleton OpenPose and the per-person refine; the real smoke checks it (§4).

## 3. Change

- `recipes.py`: `STYLE_R3_WATERCOLOR` → `STYLE_CEL_ANIME`; `NEGATIVE` now leads with
  watercolor / pastel / washed out / faded / overexposed / photorealistic / realistic face /
  glossy skin, then the outfit lock. All recipe prompts stay ≤ 77 CLIP tokens (measured with
  the real tokenizer: worst built-in case 76; negative 71).
- API `/api/visuals/options` `style_id`: `cel_anime`.
- Worker + engine: optional style LoRA (`VISUALS_STYLE_LORA_WEIGHT`, default **0 = off**).
  `peft` is listed as optional in `requirements-image.txt` (0.21.2; 0.17.x breaks on
  transformers 5).
- Built-in scene texts unchanged: richer places pushed duo prompts to 83–87 tokens, so the
  place (prompt tail) would be truncated; the style prefix already supplies the scenery look.

## 4. Real pipeline smoke (2026-10-04, owner's RTX 3060)

`scripts/smoke_ai_visuals.py --duo-refine on --seed 20261001` (same seed as r9) → exit 0,
8/8 shots, 3 Remotion stills, 638 s for the shots, no prompt truncated. Contact sheet:
`owner-runs/style-ghibli-20261004/smoke_refine_on/*/contact_shots.png` (deleted 2026-10-04 at the owner's request).
- All 8 shots are cel-anime with outlines, flat shading, painted sunlit backgrounds;
  the faces carry through IP-Adapter consistently.
- Still open (carried over from r9, not caused by the style change): `Cafe_duo_close` has a
  third person, and the male top drifts to yellow/cream in the duo shots.
- Visual tests: 76/76 passed; ruff clean.

## 5. Owner action

Characters created before this change keep their watercolor face references, and the
IP-Adapter copies that look into every shot. **Unlock each character and regenerate its
candidates + sheet**, then re-run Step 5 shots. Owner visual verdict on the real smoke
(`owner-runs/style-ghibli-20261004/smoke_refine_on/`) is Gate B-14's style input.
