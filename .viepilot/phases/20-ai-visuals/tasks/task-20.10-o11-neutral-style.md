# Task 20.10 — O11: neutral style wording, no franchise LoRA (doc-first card)

**Authority:** owner E1 (D41, 2026-10-05): O11 stands — no franchise, artist or studio names in
prompts and no franchise LoRAs. Task 20.9 put "Studio Ghibli style" in `STYLE_CEL_ANIME` and
added optional support for ntc-ai's "Studio Ghibli style" LoRA (off by default).

## Change

1. `recipes.STYLE_CEL_ANIME` → `"hand-drawn 1990s anime film still, clean ink outlines, flat cel
   shading, lush painted background, warm sunlight, vivid colors"` (no proper names).
2. Remove `style_lora` from `scripts/image_worker.py` + `engine.py`, `VISUALS_STYLE_LORA_WEIGHT`
   from config and the `peft` note in `requirements-image.txt`. `scripts/spike_style_ghibli.py`
   keeps its LoRA variant only as historical evidence code and is renamed in its docstring as a
   spike (not shipped).
3. Re-measure CLIP tokens (worst built-in case must stay ≤ 77).

## Verification (GPU, owner's machine)

A/B at the 20.9 seeds (11, 23), SDXL base, 30 steps, CFG 6, items lan_portrait /
minh_portrait / duo_cafe / duo_path: **named** prefix vs **neutral** prefix → side-by-side sheet
`docs/operations/phase20-t10-neutral-style-ab.png`.

**Accept:** the neutral column keeps outlines, flat cel shading, round simple faces and painted
sunlit backgrounds (owner judges); visual tests + ruff green.
