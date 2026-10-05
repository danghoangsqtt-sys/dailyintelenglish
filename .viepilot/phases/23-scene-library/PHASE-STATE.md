# PHASE-STATE — Phase 23: Scene Library v2

- **Status:** open 2026-10-05 (owner: "tôi đang không có thời gian test hãy tiếp tục Phase 23";
  Gate B-14 deferred, Phase 20 stays open until the owner's visual sign-off).
- **Plan:** `docs/implementation/phase-23-24-scenes-and-storyboard.md` §3.

| Task | Description | Owner | Status |
|---|---|---|---|
| 23.1 | Spike: same-place consistency (a text only / b scene IP reference / c plate + character inpaint) | Claude | **done 2026-10-05** (`f62e4cd`): bg-sim a 0.815/0.757, b 0.83–0.87, c 0.86–0.89 but pasted-on; **owner picked b ~0.4** |
| 23.2 | Scene model v2 + plate IP reference in shots | Claude | **done 2026-10-05** (`8401d3f` card, `88a55dc` code): migration 009, plates in L0, scene IP 0.4; VAE tiling fixes a pre-existing L2 VRAM spill (2395 s -> 967 s, peak 11.4 GB); bg-sim Cafe 0.791->0.853, Classroom 0.757->0.813; full suite 1290 passed |
| 23.3 | Built-in pack: 16 places | Claude | **done 2026-10-05** (`2219685` card + code commit): real-tokenizer budget fixed (single suffix), people-free plates, 16 plates in the owner's library; sheet `docs/operations/phase23-t3-builtin-plates.png` |
| 23.4 | Scene Library UI v2 | Claude | **done 2026-10-05** (`ded4eb6` card): category/time fields, filter chips, used-in count, duplicate, stale-plate warning, cache-busted plate URL; full suite 1294 passed |
| 23.5 | Gate B-15 (owner) | Owner | planned |
