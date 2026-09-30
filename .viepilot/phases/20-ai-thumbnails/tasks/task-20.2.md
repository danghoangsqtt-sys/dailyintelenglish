# Task 20.2 — Spike: pick the local image model (SDXL / SDXL-Turbo / FLUX.1-schnell) + IP-Adapter trial

- **Status:** design committed (Coder, doc-first). **Awaiting PM/owner approval, plus 2 owner
  answers (Q1, Q2 below), before any download or code.** The spike run itself needs the
  owner's RTX 3060. The design pass ran in a cloud container with no GPU, where huggingface.co
  downloads are blocked; the Hugging Face connector was used for metadata and file sizes.
- **Owner:** Coder
- **Priority:** P0 for Phase 20. Its PASS gates 20.3–20.5.
- **Dependency:** Task 20.1 (GPU model manager, `6b1e7f7`). The spike takes its GPU through a
  real lease and produces the measured threshold that 20.1 deliberately left unset (D20.1-e).
- **Card source:** the owner's Phase 20 summary (2026-09-30): "Spike chọn model ảnh: SDXL /
  SDXL-Turbo / FLUX.1-schnell + thử IP-Adapter". ENH-012's acceptance criteria also apply:
  - the choice is made by a measured spike (VRAM fit on 12 GB, time per image, licence,
    quality);
  - there is a feature flag with the template fallback;
  - no weights are bundled in the .exe;
  - VRAM contention with qwen is handled;
  - the owner compares generated and template thumbnails on 5 real episodes.

## Goal

Measure, on the owner's machine, which candidate makes usable per-episode thumbnail
backgrounds (D26: cartoon or modern 3D characters invented per lesson topic). Test whether
IP-Adapter keeps one character consistent across images; that is the foundation for 20.4
and 20.5. Then hand the owner real images to judge, with the same spike-first discipline
as 19.1, 21.1 and 21.1b.

## Findings from the design investigation (2026-09-30, real sources)

Everything here was read live from the Hugging Face Hub (repo metadata, `LICENSE`/`README`
front-matter, exact file sizes) or produced by a real install. Nothing is from memory.

### F1. Licences: one of the plan's combinations is not commercially usable

| Component | Licence (read from the repo) | Commercial use |
|---|---|---|
| `stabilityai/stable-diffusion-xl-base-1.0` | `openrail++` | Yes, subject to the OpenRAIL use restrictions |
| `stabilityai/sdxl-turbo` | Stability AI Community License (read from `LICENSE.md`, updated 2024-07-05) | Only if annual revenue < US$1M. You **must register** at stability.ai/community-license and display **"Powered by Stability AI"** |
| `black-forest-labs/FLUX.1-schnell` | `apache-2.0` | Yes. The repo is **gated**: the owner's HF account must accept the terms and the download needs an HF token |
| `city96/FLUX.1-schnell-gguf` (quantized) | `apache-2.0` | Yes |
| `h94/IP-Adapter` (SDXL adapters) | `apache-2.0` | Yes |
| `XLabs-AI/flux-ip-adapter` | `flux-1-dev-non-commercial-license` | **No**. It was also trained for FLUX.1-**dev**, not schnell |
| `InstantX/FLUX.1-dev-IP-Adapter` | `flux-1-dev-non-commercial-license` | **No**. Also FLUX.1-dev |
| `madebyollin/sdxl-vae-fp16-fix` | `mit` | Yes |

**Consequence:** "FLUX.1-schnell + IP-Adapter" has **no commercially usable IP-Adapter**.
Both FLUX adapters on the Hub are non-commercial and target a different model. **The only
licence-clean path to a consistent character is SDXL + `h94/IP-Adapter`.** FLUX.1-schnell
can still compete on background quality, but not on character consistency.

### F2. Sizes and fit on the 12 GB RTX 3060 (exact file sizes from the Hub)

| Candidate | Weights on disk (download) | Fits in VRAM as-is? |
|---|---|---|
| SDXL base, fp16 variant | UNet 5,135,149,760 + text encoder 246,144,152 + text encoder 2 1,389,382,176 + VAE ≈ 0.17 GB → **≈ 6.9 GB** | Yes, about 7 GB of weights plus activations |
| SDXL-Turbo, fp16 | `sd_xl_turbo_1.0_fp16.safetensors` 6,938,081,905 → **≈ 6.9 GB** | Yes (same architecture as SDXL) |
| FLUX.1-schnell, bf16 | transformer 9,962,580,296 + 9,949,328,904 + 3,870,584,832 = **23.78 GB**; T5-XXL text encoder 4,994,582,224 + 4,530,066,360 = **9.52 GB**; CLIP 0.25 GB; VAE 0.17 GB → **≈ 33.7 GB** | **No.** The transformer alone is 2× the card |
| FLUX.1-schnell GGUF (transformer only) | Q4_K_S 6,783,943,712 · Q5_K_S 8,263,222,304 · Q6_K 9,834,955,808 · Q8_0 12,687,821,728 | Q4/Q5/Q6 yes; Q8 no. The **9.5 GB T5 must still run separately**: encode the prompt, free it, then load the transformer |
| IP-Adapter (SDXL) | `ip-adapter-plus-face_sdxl_vit-h.safetensors` 847,517,512 + ViT-H image encoder 2,528,373,448 (**≈ 3.4 GB**). The bigG encoder for `ip-adapter_sdxl` is 3,689,912,664 | Adds to SDXL's ~7 GB. The spike measures whether SDXL + adapter + 1344×768 activations stays under 12 GB |

**RAM finding (from the owner's own Task Manager screenshot, 2026-09-30):** 22.3 of 31.7 GB
RAM was in use, so about **9.4 GB free**. The FLUX route stages a 9.5 GB T5 (bf16) through
system RAM when offloading, which would push the machine into paging. The spike must record
peak RAM for FLUX, not just VRAM. SDXL does not have this problem.

### F3. Python 3.14 works this time, but the model should still run in a separate process

A real (not `--dry-run`) install into a **fresh Python 3.14.7 venv**, the owner's exact
interpreter from the 21.1 report, **succeeded**: `torch==2.14.0`, `diffusers==0.40.0`,
`transformers==5.17.0`, `accelerate==1.15.0`, `sentencepiece==0.2.2`, `gguf==0.19.0`,
`tokenizers==0.23.2`. The imports were checked for real: `StableDiffusionXLPipeline`,
`FluxPipeline`, `FluxTransformer2DModel`, `GGUFQuantizationConfig`,
`CLIPVisionModelWithProjection`, `T5EncoderModel`. Both pipelines expose
`load_ip_adapter`. `diffusers` requires `torch>=2.6`. Unlike Kokoro (21.1) and StyleTTS 2
(21.1b), **nothing forces Python 3.11 here.**

It still belongs in its own venv and subprocess, not in the FastAPI process:
- **torch is not in `requirements.txt`.** The torch in the owner's main venv (2.11.0+cu128)
  is an unrecorded leftover from the abandoned OmniVoice path (21.1 report §1), so nothing
  may depend on it.
- **Packaging:** the image venv measured **5.5 GB** here (Linux CUDA torch). Putting it in
  the main app would bloat the PyInstaller .exe (Task 12.2). ENH-012 already rules out
  bundled weights.
- **VRAM release:** a worker process that exits returns 100% of its CUDA memory, including
  the CUDA context and allocator cache that `del` + `empty_cache()` leave behind. Task 20.1
  is built on consumers releasing the card completely.
- **Crash isolation:** a CUDA OOM or driver fault kills the worker, not the app.

`transformers` 5.x logged that `CLIPImageProcessor` falls back to its PIL implementation
without `torchvision`. That is harmless for IP-Adapter's image encoder input; noted so
nobody chases the warning.

### F4. Output sizes the spike must hit

The current thumbnails are **1280×720** (16:9) and **720×1280** (9:16)
(`app/core/constants.py:24-27`).
- SDXL is trained on aspect buckets. The nearest are **1344×768 / 768×1344**, which are then
  resized/cropped to the exact size.
- FLUX takes multiples of 16, so 1280×720 and 720×1280 work natively.

## Design decisions (Coder, doc-first)

### D20.2-a: Isolation: a new `venv-image/` on Python 3.14, plus a subprocess worker

Mirrors `venv-kokoro/` and `venv-styletts2/`. Only the interpreter differs (3.14 is proven
to work, F3).
- `scripts/image_worker.py` uses the same line-delimited JSON protocol, stdout isolation,
  handshake and `load`/`unload` commands as `styletts2_worker.py`.
- `requirements-image.txt` pins the versions from F3.
- torch comes from the cu128 index first, the same guard as 21.1b, because plain PyPI gives
  Windows a CPU-only torch.

### D20.2-b: The candidate matrix (the 3 models the owner named, with F1/F2 applied)

| # | Candidate | Role in the spike |
|---|---|---|
| A | **SDXL base 1.0** fp16 + `sdxl-vae-fp16-fix` | Main candidate: the only one with a licence-clean IP-Adapter |
| B | **SDXL-Turbo** fp16 | Speed comparison (1–4 steps). **Only if the owner accepts its licence (Q1)** |
| C | **FLUX.1-schnell** GGUF Q5_K_S transformer + T5 run separately | Background-quality comparison only (no IP-Adapter, F1). **Only if the owner accepts the gated terms (Q2)** |

Q5_K_S is the proposed middle point: 8.26 GB leaves room for activations. Q4_K_S is the
fallback if Q5 does not fit, and the spike records which one ran.

ENH-012/D26's earlier candidates (Z-Image-Turbo, Qwen-Image GGUF, SDXL + a cartoon/3D LoRA)
are **not** in this matrix, because the owner's 2026-09-30 list narrowed it to the three
above. A style LoRA on SDXL is a cheap later add-on if A's style is close but not right.
Each LoRA needs its own licence check.

### D20.2-c: Test inputs: 5 real episodes, same discipline as before

- The runner reads 5 real projects `mode=ro` (topic, CEFR level, speakers), matching
  ENH-012's "5 real episodes".
- Each gets one 16:9 background from each candidate that is run.
- The prompt is one fixed style template stated in the report (D26: a cartoon or modern 3D
  character per topic, no text in the image, leave room for the headline). The production
  prompt file under `prompts/` belongs to 20.3.
- The existing template thumbnail for each episode is rendered alongside, so the owner
  compares against what ships today.
- Fixed seeds, so a re-run reproduces the same images.

### D20.2-d: IP-Adapter consistency trial (SDXL only, F1)

1. With candidate A, generate one character sheet image (fixed seed) as the reference. No
   project uses `speakers.avatar_image_path` yet, so there is no real reference to reuse.
2. Generate 3 different scenes with `ip-adapter-plus-face_sdxl_vit-h` at 2 strengths (0.5
   and 0.8), giving 6 images.
3. The owner judges one question: "is this the same character?"
4. Record the VRAM added by the adapter.

That VRAM figure determines whether 20.4/20.5 can run in one lease with the base model.

### D20.2-e: GPU sharing and the measured threshold

- The runner takes a **real Task 20.1 lease** (`get_gpu_manager().lease("image", min_free_mb=...)`)
  for each candidate. It uses a provisional `min_free_mb` equal to the weight size from F2
  plus 2 GB, and says so in the report.
- It runs twice, as 21.1b does: once with Ollama idle, and once right after the app's own
  qwen call, so the lease has to evict for real. That second run also covers 20.1's owed
  eviction evidence.
- The report proposes `DIE_GPU_MIN_FREE_MB_IMAGE` = **measured peak VRAM + a stated
  margin**, which 20.3 adds to config.

### D20.2-f: Measurements, per candidate

- Model load time.
- Per-image wall time at the target size (mean of 5, first one reported separately as the
  cold one).
- Peak VRAM (`torch.cuda.max_memory_allocated` in the worker, and `nvidia-smi` from the
  runner).
- Peak RAM (worker RSS).
- Disk footprint (weights and venv).
- Licence.
- For B/C, the steps used (Turbo 1–4, schnell 4).

### D20.2-g: What the owner receives

`data/tmp/phase20_image_spike/`:
- a contact sheet per episode (template | A | B | C, side by side);
- the 6-image IP-Adapter sheet;
- `docs/operations/phase20-spike-images.md`, containing all the numbers.

### D20.2-h: Decision proposal (after the real run, not pre-decided)

- **PASS:** name one model, and IP-Adapter goes ahead for 20.4/20.5.
- **SCOPE-CUT:** backgrounds only, with no character consistency.
- **STOP:** keep the templates, and Phase 20 shrinks to the 20.1 foundation.

## Questions for the owner (answer before any download)

- **Q1: Is the YouTube channel monetized, or will it be?**
  - If yes, candidate B (SDXL-Turbo) requires registering with Stability AI and showing
    "Powered by Stability AI".
  - It does not change A or C.
  - Any FLUX.1-dev component is out either way (F1).
  - Answering "drop B" also saves a 6.9 GB download.
- **Q2: Keep FLUX.1-schnell (candidate C)?**
  - If yes, the owner accepts its gated terms on their Hugging Face account and creates a
    read token for the download on their machine.
  - It costs about 18 GB of downloads (Q5 transformer + T5 + CLIP/VAE), and RAM is tight
    (F2).
  - It can only ever do backgrounds, not consistent characters (F1).

## Proposed allowed files (for PM approval)

- **New:**
  - `scripts/image_worker.py`;
  - `scripts/spike_images.py`;
  - `requirements-image.txt`;
  - `docs/operations/phase20-spike-images.md` (after the run).
- `.gitignore`: add `venv-image/`. Weights go to `models/image/` via `HF_HOME`, which the
  existing `models/*` rule already covers.
- `CHANGELOG.md`: one bullet after the report.
- **Not touched:** `app/`, `frontend/`, `tests/`, `video-renderer/`, the other `venv-*`,
  and 21.1/21.1b artefacts. `data/app.db` is read-only (`mode=ro`).

## Risks

| Risk | Mitigation |
|---|---|
| SDXL + IP-Adapter + 1344×768 exceeds 12 GB | Measured. Fallbacks, in order: VAE tiling, attention slicing, and running the image encoder first and freeing it. The report says which were needed |
| FLUX T5 staging exhausts RAM (~9.4 GB free observed) | Measure peak RSS. If it pages, report that as a result instead of hiding it; C can be dropped |
| 18–30 GB of downloads | Only the candidates the owner keeps (Q1/Q2). Sizes are known upfront (F2) |
| Licence drift | Licences were read on 2026-09-30 and are re-checked at the gate (the same idea as Phase 19's invariant on re-checking licences) |

## Verification / Definition of done

- The design is approved and Q1/Q2 are answered.
- Every kept candidate produces 5 real episode backgrounds. The IP-Adapter sheet exists.
  There is no OOM, or any OOM is reported with the mitigation that fixed it.
- The report has every D20.2-f number from the real run, plus the proposed
  `DIE_GPU_MIN_FREE_MB_IMAGE`.
- The owner judges the contact sheets, and the decision is recorded.
- No disallowed file is touched. The full suite is unchanged, since this task adds no tests
  and touches no `app/`.
