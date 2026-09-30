# Task 20.2b — Spike: character library feasibility (style, identity, actions, cut-outs, M1 vs M2)

- **Status:** design + implementation (Coder, 2026-09-30). The owner approved the scope
  ("okey làm đi" — "okay, go ahead") after Amendment B §5. **The real run needs the owner's
  GPU.** It goes through the runbook `docs/operations/owner-runbook-2026-09-30-r3.md`.
- **Owner:** Coder
- **Depends on:** 20.1 (the GPU lease) and 20.2 (SDXL-Lightning chosen, image worker).
- **Controlling detail:** `../proposal-amendment-b-asset-library.md` §5.4 (the spike scope
  the owner approved).

## Goal

Answer, with real images the owner judges, four questions:

1. **The channel style.** Can a Ghibli-like look be reached with *descriptive* prompts
   only, never naming Ghibli or Miyazaki, on Lightning vs base?
2. **Identity.** Does one character stay the same person across 3 face views × 5
   expressions + full body × 5 expressions, and across 4 **OpenPose-controlled actions**?
3. **Cut-outs.** How clean are `skytnt/anime-seg` background removals on those assets?
4. **Composition.** In the owner's eye, compare three versions of the same scene:
   - an **M1 naive paste**;
   - an **M1 integrated composite** (stage spot, contact shadow, colour match,
     feathering);
   - an **M2 inpaint render**.

## Design decisions

- **D20.2b-a: pipeline in five worker lifetimes.** Each runs under its own Task 20.1 lease,
  and each worker exits, freeing all of its VRAM.

  | Phase | Worker | Produces |
  |---|---|---|
  | P1 | Lightning (and base, for the style comparison) | style sheet: 2 scenes "no people" + portrait candidates |
  | P2 | Lightning + IP-Adapter plus-face (with image encoder) | 20 base assets; **encodes** the action prompts + reference image to an embeddings file |
  | P3 | Lightning **+ ControlNet OpenPose**, **without** text/image encoders (IP projection layers only) | 4 action assets from the saved embeddings |
  | P4 | no GPU needed | `anime-seg` cut-outs (ONNX via onnxruntime) |
  | P6 | base **inpaint** + IP-Adapter | M2: the character rendered into each scene |

  P5 (M1 composites) is Pillow in the runner.
- **D20.2b-b: why P2/P3 split encode from render (measured constraints, not preference).**
  - SDXL (~9.1 GB) + IP-Adapter (+2.0 GB) + ControlNet (~2.5 GB fp16,
    `diffusion_pytorch_model.safetensors` = 2,502,139,104 B) ≈ 13.6 GB, more than the
    12 GB card.
  - diffusers CPU offload would keep ~11 GB of weights in RAM. The owner's machine showed
    only **8.5 GB free virtual memory** (r2 preflight) and has already hit os error 1455
    once.
  - So: encode the prompts and the IP image embeddings first (P2), drop every encoder
    (the process exits), and render with UNet + ControlNet + IP projection layers + VAE
    only.
  - Verified in diffusers 0.40.0 source:
    - `text_encoder`, `text_encoder_2` and `image_encoder` are `_optional_components` of
      `StableDiffusionXLControlNetPipeline`;
    - `__call__` derives `text_encoder_projection_dim` from `pooled_prompt_embeds` when
      `text_encoder_2 is None` (line 1395);
    - `load_ip_adapter(image_encoder_folder=None)` loads the projection layers only
      (`loaders/ip_adapter.py:200-229`).
- **D20.2b-c: models (licences read from the Hub 2026-09-30).**
  - `xinsir/controlnet-openpose-sdxl-1.0`: Apache-2.0.
  - `skytnt/anime-seg` `isnetis.onnx` (176,069,933 B): Apache-2.0. It runs with
    `onnxruntime==1.30.0`, verified to install and import on Python 3.14; no remote code
    runs.
  - **BiRefNet is not used.** Its loader needs `trust_remote_code=True` (executing
    downloaded code), and anime-seg suits the 2D style. It is revisited only if the
    anime-seg cut-outs fail.
  - `briaai/RMBG-2.0` is excluded (gated, "other" licence).
- **D20.2b-d: OpenPose control images are drawn, not detected.**
  - Standard 18-keypoint OpenPose rendering (COCO keypoint order, the usual limb colours).
  - 4 hand-defined poses: waving, pointing, thinking (hand to chin), cheering. They are
    drawn by the runner with Pillow, so no pose-detector model is needed.
- **D20.2b-e: style preset and prompt rules.**
  - The Amendment B §5.1 preset is prepended to every prompt.
  - Never "Ghibli" or "Miyazaki", and never a brand, franchise character or living artist.
  - "no text, no logo" stays in the positive prompt, because Lightning at CFG 0 ignores
    the negative prompt (20.2 finding).
  - Scenes say "no people".
- **D20.2b-f: the character.** One invented character (a young woman English teacher),
  with a canonical description reused verbatim in every prompt. The runner uses portrait
  candidate #1 as the reference; in the real library the owner picks. Invariant 50: the
  character is invented, and no real person is drawn.

## Allowed files

- `scripts/image_worker.py`: new `pipeline` (controlnet / inpaint), `encoders=false`,
  IP-layers-only loading, `encode`, embeds-based generate, `remove_background`.
- **New** `scripts/spike_character_library.py` (the runner).
- `requirements-image.txt`: `+ onnxruntime==1.30.0`.
- **New** `docs/operations/owner-runbook-2026-09-30-r3.md`, this card, and PHASE-STATE.

**Not touched:** `app/`, `tests/`, `frontend/`, `video-renderer/`, other venvs, and
`data/app.db` (this spike needs no DB at all).

## Verification here (cloud, no GPU, no Hub)

Tested against tiny random-weight SDXL components (UNet, ControlNet built from the UNet,
VAE, text encoders):
- text2img, the encode→embeds→ControlNet-render path, and inpaint;
- `remove_background` against a tiny exported ONNX model with the same I/O shape;
- the runner end to end with `--allow-cpu --skip-ip`;
- unit checks of the pose drawing and the M1 compositor.

The IP-Adapter paths cannot run here (no weights). They are exercised only on the owner's
machine.
