# PHASE-STATE — Phase 39: Image model benchmark — RealVisXL vs Qwen-Image (D110–D116)

- **Status:** 39.1–39.3 done 2026-10-13 (report `docs/operations/phase39-image-benchmark.md`); waiting for the owner's blind
  scores and choice per task before 39.4. Downloads: ~72 GB + 1.6 GB of 4-step LoRAs (owner approved). Brainstorm:
  `docs/brainstorm/session-2026-10-13-qwen-image.md`.

| Task | Description | Status |
|---|---|---|
| 39.1 | Benchmark harness (separate `.venv-qwen`, diffusers 0.41 + gguf) and prompts per task | done |
| 39.2 | Four system tasks × engines: activity illustration (generic people), scene plate (no people), thumbnail/topic picture, character shot (Alex/Lina: RealVisXL IP-Adapter vs Qwen-Image-Edit-2511) | done |
| 39.3 | Report: time (warm/cold), VRAM, defects; blind sheets for the owner to score; decision per task (D113) | done |
| 39.4 | Apply the winner per task (engine switch with RealVisXL fallback), tests, Gate B-26 | planned |

Engines: RealVisXL V5.0 (baseline), Qwen-Image-2512 GGUF Q4_K_S + Lightning 8-step (Apache 2.0), Qwen-Image-Edit-2511
GGUF Q4_K_S + Lightning (Apache 2.0, character shots), Qwen-Image-2.1-Turbo GGUF Q8 (**evaluation only**, research licence).
