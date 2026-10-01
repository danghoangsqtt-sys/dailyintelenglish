# Task 20.2h — Spike v6: two-person conversation shots, close-up framing, clean solid-colour outfits

- **Status:** implemented (Coder, 2026-10-01). Design commit `65ea14a`; see "Implementation
  notes" at the end. **The real run needs the owner's GPU.**
  It goes through the runbook `docs/operations/owner-runbook-2026-10-01-r8.md`.
- **Owner:** Coder
- **Authorization:** the owner's 20.2g verdict, 2026-10-01 (verbatim in
  `docs/operations/phase20-spike-character-v5.md`), which also asks for the
  conversation shots the earlier spikes did not cover.

## Owner requirements (20.2g verdict)

1. **Male: candidate 1** — neat short hair, "not long, effeminate hair".
2. **Hand repair: much improved, very good quality.** Keep the pass.
3. **Close-up framing is preferred over the wide r7 framing.**
4. **New: two-person conversation images**, in three forms:
   - close-up conversation;
   - wide conversation in a setting: school;
   - wide conversation in a setting: café.
5. **Male outfit: neat, slim-fit**, not a bulky hoodie.
6. **The female is good as is.**
7. **Outfit rule for both:** **exactly 1 top + 1 bottom, each one solid colour, no
   pattern, no multi-colour.** Colours must not get "confused".

## Design decisions

- **D20.2h-a: characters and references.**
  - **Female:** unchanged, except the outfit wording becomes explicitly solid ("plain
    yellow sweater, plain blue jeans").
  - **Male:**
    - "handsome young Vietnamese man student, short neat black hair, brown eyes, friendly
      smile, plain light blue slim-fit shirt, plain black slim trousers";
    - the face comes from **the owner's pick: r7 candidate 1**
      (`r3_bright_male_student_candidate_1.png`, the neat-haired one).
  - **Reference cards** (P1):
    - per style × character, one head-and-shoulders portrait on a plain light background
      in the new solid outfit;
    - the face is IP-guided (scale 0.6) from the r7 candidate 1 the owner liked; the
      female uses each style's own r7 candidate 1.
    - These cards become the identity references for every shot. Falls back to a no-IP
      portrait (fixed seed) if an r7 file is missing.
- **D20.2h-b: outfit lock.** The negative adds "pattern, stripes, plaid, print,
  multicolored clothes, layered clothes" to 20.2g's clothing list.
- **D20.2h-c: two people in one picture — masked multi-face IP-Adapter.**
  - One IP-Adapter (plus-face), **two reference faces**. Diffusers' IP-Adapter masking
    confines each face to its half of the frame (`ip_adapter_masks`; left = female,
    right = male).
  - **OpenPose draws both skeletons** in one control image, facing each other: nose
    offset toward the partner, far ear hidden.
  - **The text prompt places them:** "…a woman … on the left, a man … on the right…".
  - Through the encode→render split: the encode takes `ip_adapter_images` [female,
    male]; the render takes `ip_adapter_masks`.
  - **Verified in the cloud** on a tiny SDXL with a fake plus-adapter: swapping the two
    masks changes the output, in both the direct and the embeds+ControlNet paths.
- **D20.2h-d: shot list per style** (both styles kept: the owner called both pretty);
  2 seeds each, so 20 renders.

  | Shot | Framing | Pose geometry (head height / nose y / centres) |
  |---|---|---|
  | female single close-up, café | chest-up | 0.30 / 0.36 / x 0.32, one hand gesturing |
  | male single close-up, classroom | chest-up | 0.30 / 0.36 / x 0.32, one hand gesturing |
  | **duo close-up**, café | chest-up, facing each other | 0.24 / 0.38 / x 0.30 + 0.70 |
  | **duo wide**, school classroom | standing, knees in frame | 0.13 / 0.30 / x 0.33 + 0.67 |
  | **duo wide**, café, seated at a table | waist-up behind the table, hands on it | 0.15 / 0.32 / x 0.33 + 0.67 |

- **D20.2h-e: hand repair (kept).** It runs for every in-frame wrist of every person
  (crop 2.2 head-units, 768², strength 0.5).
- **D20.2h-f: frames.**
  - Single shots: the speaker chip + vocab card as before.
  - **Duo shots carry no vocab card in the mockup.** The card's top-right slot covers the
    right-hand person's head in a two-shot. That is a layout decision for the real
    in-video task: move the card, or show it only on single shots. It is noted here, not
    solved.
- **D20.2h-g: run shape.**

  | Phase | Worker | Produces |
  |---|---|---|
  | P1 | base text2img + IP (with encoder) | 4 reference cards; encode 2 single prompts + 3 duo prompts per style |
  | P2 | base ControlNet text2img, no encoders, IP layers | 20 renders |
  | P3 | base inpaint | hand repair |
  | P4 | Pillow | 20 frames, 3 sheets |

  The estimate is ~25 minutes; no download.

## Allowed files

- `scripts/image_worker.py`: `ip_adapter_images` (several faces, one adapter) on
  generate/encode; `ip_adapter_masks` on generate.
- **New** `scripts/spike_character_v6.py`.
- **New** `docs/operations/owner-runbook-2026-10-01-r8.md`, this card, and PHASE-STATE.

**Not touched:** `app/`, `tests/`, `frontend/`, `video-renderer/`, requirements, and the DB.

## Verification here (cloud, no GPU, no Hub)

- A tiny SDXL plus a **fake IP-Adapter plus** (random weights in the real key layout,
  with a tiny CLIP vision encoder), built for this task, so the IP code paths finally
  run in the cloud.
- The runner end to end with `--allow-cpu` (IP on, through the fake adapter).
- Pure checks: the pose geometry for all 5 shot types, the masks, the hand boxes for
  both people, and CLIP token counts ≤ 75.

## Owner questions the run answers

1. Do the conversation shots (close-up, school, café) look natural, with **two different
   people** who keep their identities?
2. Is the close-up framing right now?
3. Is the male now neat and slim-fit, with short hair?
4. Are the outfits single solid colours, 1 top + 1 bottom, with no colour confusion?

## Implementation notes (Coder, 2026-10-01)

- **Worker** (`scripts/image_worker.py`).
  - `ip_adapter_images` (several faces for the one loaded adapter, diffusers' `[[a, b]]`
    form) on `encode` and direct `generate`.
  - `ip_adapter_masks` on `generate`: `IPAdapterMaskProcessor` → `[1, n_faces, h, w]` in
    `cross_attention_kwargs`.
  - `encode` reports `ip_faces`.
- **Prompts** were compressed after counting with OpenAI's CLIP BPE.
  - The first duo wording reached 82 tokens.
  - Now every prompt is ≤ 72 and the negative is 66.
- **A fake IP-Adapter plus** (scratch `build_fake_ip.py`, not committed). It is built in
  the real key layout:
  - `image_proj.latents`, `proj_in`/`proj_out`, `norm_out`;
  - 4 Resampler layers;
  - `ip_adapter.{1,3,…}.to_k_ip/to_v_ip` for the tiny UNet's 12 cross-attention
    processors;
  - a tiny `CLIPVisionModelWithProjection`.
  - **This is the first time the IP code paths ran in the cloud.**
- **Verification (cloud, CPU).**
  - **Masking works:** swapping the two masks changes the output, in the direct path
    (mean |Δ| 24.7) and the embeds + ControlNet path (6.3). Masked differs from unmasked
    (4.1).
  - **The runner end to end with IP on**, all 4 phases ok:
    - 4 cards, covering both found-r7 and missing-r7 (the scale-0 fallback);
    - 10 CFG encodes with IP, with `ip_faces` 2 for duos and 1 for singles;
    - 20 ControlNet renders from embeds, with IP layers only and no encoders;
    - 44 hand repairs;
    - 20 frames;
    - 3 sheets.
  - **Pose checks:**
    - every head top is below the chip row;
    - in duos, each person stays inside their IP-mask half and the far ear is hidden
      (they face each other);
    - the masks are disjoint and cover the frame;
    - hand crops: 1 per single, 1 for the duo close-up, 4 for each wide duo.

