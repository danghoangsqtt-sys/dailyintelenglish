# Task 20.2 — Spike: pick the local image model (SDXL / SDXL-Turbo / FLUX.1-schnell) + IP-Adapter trial

- **Status:** implementation (worker + runner) landed 2026-09-30 and was validated off-machine.
  Owner confirmed Q2 (drop FLUX). **Pending: the real run on the owner's RTX 3060** (see
  "Owner-machine run"), then the report and the owner's decision.
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

## Owner decisions and Amendment A (2026-09-30)

**Q1, owner's answer (verbatim):** *"có bật kiếm tiền, tôi không muốn đăng ký với stability
AI vì tôi muốn mọi thứ miễn phí, hợp pháp, nhanh gọn, không dính watermark của bất kỳ hãng
nào và không dính đến bản quyền"*. In English: the channel **is monetized**, and the owner
does **not** want to register with Stability AI. Everything must be free, legal and quick,
with no vendor watermark and no copyright entanglement.

This gives four hard constraints for the whole of Phase 20: free, commercial-safe with no
registration, no watermark of any vendor, and no licence strings on the output. Checked
against the real sources:

- **Candidate B (SDXL-Turbo) is dropped.** Commercial use of it requires registering with
  Stability AI and displaying "Powered by Stability AI" (F1).
- **Candidate A (SDXL base 1.0) meets all four constraints.** Read from its `LICENSE.md`
  (CreativeML Open RAIL++-M, 2023-07-26):
  - no fee;
  - no registration;
  - *"Licensor claims no rights in the Output You generate"*;
  - notice and attribution duties apply only when **redistributing the model weights**.
    That does not happen here: each install downloads the weights to the owner's own
    machine, and none are bundled in the .exe (ENH-012).
  - The Attachment A use-restrictions (unlawful use, harming minors, defamation, and so on)
    do not touch English-lesson thumbnails.
- **Watermark, verified in the source.** `diffusers==0.40.0`
  `pipelines/stable_diffusion_xl/pipeline_stable_diffusion_xl.py:276` defaults
  `add_watermarker` to `is_invisible_watermark_available()`. It applies an *invisible*
  (not visible) watermark **only if the optional `invisible-watermark` package is
  installed**. The worker passes `add_watermarker=False` explicitly, and
  `requirements-image.txt` never includes that package. The result is no watermark of any
  kind, and the spike report re-checks this from the worker's pipeline object.
- **The replacement for B's "fast" role is `ByteDance/SDXL-Lightning`**:
  - licence `openrail++`, the same terms as SDXL base, so free with no registration;
  - a 4- or 8-step distillation of SDXL base;
  - shipped as a **393,854,592-byte LoRA** loaded on top of A's own weights, so "fast mode"
    costs +394 MB instead of a second 6.9 GB model;
  - same architecture, so `h94/IP-Adapter` stays usable.
  - The spike measures its speed and quality against A at full steps.
  - `latent-consistency/lcm-lora-sdxl` (also `openrail++`) is the fallback if Lightning
    disappoints. `ByteDance/Hyper-SD` is not considered because its repo declares no
    licence.

**Q2 (keep FLUX.1-schnell?): Coder recommends DROPPING it.** Awaiting the owner's
confirmation. Reasons, all from F1/F2:
1. It **cannot do the phase's main goal** (a consistent character across thumbnails and
   video): every FLUX IP-Adapter is FLUX.1-dev non-commercial.
2. **Weight:** about 18 GB of downloads even quantized, against about 11 GB for the whole
   amended SDXL set.
3. **The owner's RAM is tight:** about 9.4 GB free, while FLUX needs a separate 9.5 GB T5
   text encoder.
4. It is **gated**: it needs an HF token and the owner accepting terms on their account.
   That is not "nhanh gọn" (quick and simple).

Its licence (Apache-2.0) would have been fine. If SDXL's *backgrounds* fail the owner's
eye at Gate B-14, FLUX can come back as a background-only plan B with its own card.

**Amended candidate matrix:**

| # | Candidate | Download | Role |
|---|---|---|---|
| A | SDXL base 1.0 fp16 + `sdxl-vae-fp16-fix` (MIT), full steps | ≈ 7.2 GB | Quality reference, and the base for everything below |
| A-fast | A + SDXL-Lightning **4-step UNet** (corrected from "LoRA": see the implementation pass) | +5.14 GB | Speed option |
| IP | `ip-adapter-plus-face_sdxl_vit-h` + ViT-H encoder, on A and on A-fast | +3.4 GB | Consistent-character trial (D20.2-d) |

The total download is **about 15.6 GB** (corrected from about 11 GB: see the implementation pass), against about 35 GB in the original matrix. The
IP-Adapter sheet runs on both A and A-fast, because a speed LoRA can weaken the adapter's
effect, and that is exactly what the owner needs to see before 20.4.

**Honest limit on "no copyright entanglement".** The model licences above are clean. What
this spike cannot promise is anything about *what a prompt asks for*. A prompt naming a
real brand, a known cartoon character or a living artist's style could produce something
infringing, whatever the licence. So:
- the style template (D20.2-c) and 20.3's production prompt file will **never name a
  brand, a franchise character, or a living artist**;
- they will describe generic "original cartoon / modern 3D character" styles only;
- a negative prompt excludes text, logos and watermarks, so the image carries no
  third-party marks.

This is a design rule, not legal advice.

**Q2, owner confirmed 2026-09-30 ("okey"): FLUX.1-schnell is dropped.**

## Implementation pass (2026-09-30, Coder, cloud session: no GPU, huggingface.co blocked)

### Correction to Amendment A: Lightning is used as its UNet, not the LoRA

SDXL-Lightning's own README (read in full via the HF connector) says: *"Use LoRA only if you
are using non-SDXL base models. Otherwise use our UNet checkpoint for better quality."*
Our base *is* SDXL. So the worker loads `sdxl_lightning_4step_unet.safetensors`
(5,135,149,736 B), not the 394 MB LoRA. It also follows the README's two requirements:
the "trailing" scheduler, and exactly N steps at CFG 0. This also removes a dependency: the
diffusers LoRA path requires `peft>=0.17.0` (`diffusers/utils/constants.py`
`MIN_PEFT_VERSION`), and the UNet path does not.

Download totals, from exact Hub sizes:
- **Spike:** base 6,770,676,088 + VAE fix 334,643,238 + Lightning UNet 5,135,149,736 +
  IP-Adapter 3,375,890,960 = **15.6 GB**.
- **Production after the decision:** whichever UNet wins, plus the shared text encoders,
  VAE and IP-Adapter ≈ **10.5 GB**. The losing UNet is never shipped. The worker's
  Lightning mode already skips the base UNet weights.

### Real finding: with Lightning, the negative prompt does nothing

Lightning runs at CFG 0, and diffusers only uses `negative_prompt` when
`guidance_scale > 1`. So the "no text / logo / watermark" rule **must also live in the
positive prompt**. The runner does this, and the worker reports `negative_prompt_applied`
per image, so the report shows it rather than assuming it.

### Files

- `scripts/image_worker.py`:
  - handshake that refuses a CPU-only torch build;
  - `load` with base or lightning mode, exact fp16 `allow_patterns` so the base repo's
    10+ GB flax/onnx/openvino copies are never fetched, `add_watermarker=False`, and an
    optional `vae_tiling`;
  - `load_ip_adapter` (plus-face ViT-H; the encoder comes from the repo root's
    `models/image_encoder`, per `loaders/ip_adapter.py:203-206`);
  - `generate` (CPU-seeded generator; Lightning forced to 4 steps and CFG 0; "cover" fit to
    1280×720; peak VRAM and RSS reported);
  - `stats` and `unload`.
- `scripts/spike_images.py`:
  - reads 5 episodes `mode=ro`, taking today's thumbnail through the app's own
    `_resolve_content_sync`;
  - optional `--warm-qwen`, which makes a real local qwen call with the app's
    `num_ctx=16384` and later times the reload;
  - takes a **real Task 20.1 lease** per candidate (provisional 8192 MiB; lowered from
    9216 because the owner's screenshot shows only ~9.2 GB free at idle);
  - one worker lifetime per candidate;
  - writes contact sheets and the IP-Adapter sheet, and prints the JSON report.
- `requirements-image.txt` (Python 3.14; torch from cu128 first; no invisible-watermark,
  no peft, no FLUX dependencies) and `.gitignore` (`venv-image/`).

### Validation done here

The real SDXL weights cannot be fetched from this container, so a tiny SDXL pipeline with
random weights was built with the **real architecture** instead: a UNet with `text_time`
added embeddings, two CLIP text encoders, a VAE and a tokenizer. The real code paths were
run against it.

| Check | Result |
|---|---|
| Worker protocol: stats, generate before load, bad mode, load, 2 same-seed generates, IP without adapter, double load, unload | 11/11 lines valid JSON; every error returned cleanly, and the worker kept running |
| Same seed twice | **identical pixels** |
| Cover fit | 120×68 exactly as requested |
| Lightning mode | all **428/428** UNet tensors equal the Lightning file; scheduler `timestep_spacing = trailing`; a request for 30 steps / CFG 7 was forced to **4 / 0**; `negative_prompt_applied: false` |
| Watermark | `watermark_active: false`; the pipeline's `watermark` attribute is `None` |
| Lightning steps other than 2/4/8 | rejected |
| Runner end-to-end (scratch DB built with the app's real migrations, 2 episodes, tiny pipeline, both modes, `--warm-qwen` with no Ollama) | exit 0. The episode with a real template thumbnail comes first; the Ollama error is recorded as data; both workers exit 0; contact sheets are written with the right layout |
| Runner with no GPU (lease path) | the lease refuses `no_nvidia_gpu`, recorded as data; exit 0 |
| IP-Adapter trial sequencing (stub worker, since real adapter weights are not reachable) | reference generated **before** the adapter loads, then `load_ip_adapter`, then 6 scenes (3 prompts × 0.5/0.8), each carrying the reference; the sheet renders |
| `pip install -r requirements-image.txt` into a **fresh** Python 3.14.7 venv (torch first) | exit 0; diffusers 0.40.0 / transformers 5.17.0; `invisible-watermark` and `peft` both absent; SDXL imports |
| `ruff check` on both scripts | clean |

**Not validated here (needs the owner's machine):**
- real weights, image quality, and the real IP-Adapter load;
- VRAM and RAM peaks and timings;
- the qwen eviction.

### Owner-machine run

Close the app first (the lease is process-local, D20.1-g), then:

```
git pull
py -3.14 -m venv venv-image
venv-image\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cu128
venv-image\Scripts\pip install -r requirements-image.txt
venv-image\Scripts\python -c "import torch; print(torch.version.cuda, torch.cuda.is_available())"
venv\Scripts\python scripts\spike_images.py --run-label idle > idle.json
venv\Scripts\python scripts\spike_images.py --run-label warm_qwen --warm-qwen --skip-ip > warm_qwen.json
```

- The torch check must print a CUDA version and `True`.
- The first run downloads about 15.6 GB.
- The second run makes qwen resident with the app's own settings first. Its first lease
  therefore has to evict qwen, which also produces Task 20.1's owed numbers.
- If a run reports an OOM, re-run it with `--vae-tiling`.
- Outputs go to `data\tmp\phase20_image_spike\run_*\`. The owner looks at
  `sheet_ep1..5.png` (today's template | base | lightning) and `sheet_ip_adapter.png`.

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

## Owner-machine run 1 (`owner-runs/20260930` @ `f08d59d`): failed, root-caused, fixed

- **Environment:** `venv-image` was created on Python 3.14.7. From the cu128 index, pip
  resolved **torch `2.11.0+cu128`** (CUDA 12.8, `cuda.is_available() == True`), not the
  2.14 that plain PyPI gave the cloud install.
- **The `idle` run failed at `lightning load`:** `OSError: The paging file is too small
  for this operation to complete. (os error 1455)`. The `base` candidate had already
  run, but the runner raised out of `_main`, so `C_idle.json` was **empty** and base's
  numbers were lost.
- **Root cause (a Coder bug):** in Lightning mode the worker ran
  `UNet2DConditionModel.from_config(...).to(device, dtype)`. That instantiates the whole
  2.57B-param UNet with random **fp32** weights in CPU RAM (≈10.3 GB, the size of the
  fp32 UNet file) before any conversion. On a machine with ~9 GB of RAM free, that
  exhausts the Windows commit limit. Base mode was fine because `from_pretrained` loads
  with `low_cpu_mem_usage`.
  - **Fix:** create the UNet under `accelerate.init_empty_weights()` (meta device), then
    `load_state_dict(..., assign=True)` straight from the safetensors file on the target
    device.
  - **Measured here** on a 0.9B-param UNet with the real SDXL channel widths: peak RSS
    **4186 MB → 745 MB**.
  - On the tiny pipeline: all 428 tensors are equal to the file, and the output is
    **pixel-identical** to the pre-fix Lightning image for the same prompt and seed.
- **Runner fix:** a `SpikeError` inside one candidate is now recorded as that
  candidate's `"error"`, and the run continues. Tested: with a missing Lightning file,
  base keeps its images, Lightning records its error, the JSON is printed, and the sheets
  are built.
- **Retry:** `docs/operations/owner-runbook-2026-09-30-r2.md` (runs `idle2` and
  `warm_qwen2`; A and the C1b probe are not repeated).
