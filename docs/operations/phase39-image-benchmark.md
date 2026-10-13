# Phase 39 — Image model benchmark: RealVisXL vs Qwen-Image (D110–D116)

Run 2026-10-13 on the studio machine (RTX 3060 12 GB, 32 GB RAM), 1344×768, 2 seeds per subject, real subjects from
the storyboards and the scene library (`scripts/benchmarks/image_models/bench_set.json`). Harness:
`scripts/benchmarks/image_models/` (RealVisXL through the app's own image worker and recipes; Qwen in `.venv-qwen`,
diffusers 0.41 + GGUF). Pictures, sheets and `results.jsonl`: `data/tmp/phase39-bench/` (not in git: they include the
owner's characters).

## Engines

| Engine | Licence | How it ran here | Disk |
|---|---|---|---|
| RealVisXL V5.0 (SDXL, current) | open (commercial OK) | app worker, 30 steps, CFG 6 | already installed |
| Qwen-Image-2512 | Apache 2.0 | GGUF Q4_K_S (11.4 GB) streamed from RAM + text encoder 4-bit, Lightning LoRA 8 or 4 steps | ~30 GB |
| Qwen-Image-Edit-2511 (character shots) | Apache 2.0 | GGUF Q4_K_S + 4-bit text encoder + Lightning 8/4 steps, face reference from the library | +13 GB |
| Qwen-Image-2.1-Turbo | **Qwen Research Licence — no commercial use** (evaluation only, D111) | GGUF Q8 (7.1 GB) fully on the GPU, 8 steps | ~25 GB |

## Time and memory (median per picture, model already loaded)

| Engine | Time | VRAM peak | Model load |
|---|---|---|---|
| RealVisXL | **22 s** | 9.9 GB (11.9 GB with the face adapter) | 46 s / 25 s |
| Qwen-Image-2512, 8 steps | 56 s | 7.5 GB | 26 s + 26 s |
| **Qwen-Image-2512, 4 steps** | **30 s** | 7.8 GB | 30 s + 29 s |
| Qwen-Image-Edit-2511, 8 steps | 106 s | 10.1 GB | 51 s |
| **Qwen-Image-Edit-2511, 4 steps** | **56 s** | 10.3 GB | 53 s |
| Qwen-Image-2.1-Turbo | 31 s | 10.9 GB | 31 s + 16 s |

Notes: the 20B Qwen models do not fit the 12 GB card; their transformer streams from RAM block by block, which costs time
(the bottleneck is the GGUF dequantisation, not the PCIe copy: leaf-level streaming was slower, 64 s). The 4-step
Lightning LoRA halves the time with no visible loss (`q8_vs_q4.jpg`, `edit8_vs_4.jpg`). Prompt encoding is ~1 s.

## Quality by task (PM review of the sheets; the owner's blind scoring decides)

| Task | RealVisXL | Qwen-Image-2512 (4 steps) | Qwen-Image-2.1-Turbo (reference only) |
|---|---|---|---|
| **A. Activity illustrations** (a few ordinary people) | varied people (age, gender, ethnicity), natural light; miscounts people (A3: 3 instead of 2); crowd in the background | right number of people and clear actions, candid and sharp; **people repeat the same face** (bearded dark-haired man in most pictures); the two seeds give nearly the same picture | best: varied, right count, natural; not usable commercially |
| **B. Scene plates** (empty places) | natural, photographic, empty | richer and warmer, a little "staged"; empty | clean, modern; empty |
| **C. Thumbnail / topic pictures** (text on a sign) | **misspells** ("Toodday's Menu"), text often missing | **text exact** every time, bold and vivid — clear winner | text exact, cleaner layout |
| **D. Character inserts** (Alex/Lina from the face reference) | posed, looking at the camera, the action and the place mostly lost (no bookshop in D3) | Edit-2511: **does the action in the place** (cooking at the stove, reading among shelves, phone at a bus stop), outfit kept, face close to the reference — clear winner | — |

## Recommendation (to confirm with the owner's blind scores)

| Task | Recommended engine | Why |
|---|---|---|
| Thumbnail / topic pictures | **Qwen-Image-2512, 4 steps** | correct text is decisive for thumbnails; 30 s meets D113 |
| Character inserts | **Qwen-Image-Edit-2511, 4 steps** | much better pictures; 56 s is over D113's ~30 s, but the shots are reused through the Shot Library |
| Activity illustrations | **Qwen-Image-2512, 4 steps with prompts that name varied people** (e.g. "a woman in her thirties and an older man"), else keep RealVisXL | Qwen's counting and actions are better; its face repetition must be fixed by the prompt before it wins |
| Scene plates | **keep RealVisXL** | equal quality, faster, more natural; the plates already exist for 55 places |
| Qwen-Image-2.1-Turbo | do not use | research licence; ask Qwen for a commercial licence only if its quality becomes essential |

Each switch keeps RealVisXL as the automatic fallback (missing model, out of memory, error).

## Blind scoring for the owner

`data/tmp/phase39-bench/blind_{activity,plate,thumbnail,character}.jpg`: each row is one subject, columns A–D are the two
engines × two seeds in a shuffled order; the key is in the matching `.key.json`. Score each row with the best column
(or "equal"); D113's quality condition is met for an engine when it wins most rows.
