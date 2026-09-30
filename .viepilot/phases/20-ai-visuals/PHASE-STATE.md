# Phase 20 State — AI Visual Generation (thumbnails + consistent characters)

## Metadata

- **Phase:** 20
- **Slug:** `20-ai-visuals`
- **Status:** *(Coder update 2026-09-30.)*
  - 20.1 is implemented and awaiting owner-machine verification and PM acceptance.
  - 20.2 is done (owner PASS, SDXL-Lightning).
  - 20.2b (character-library spike): owner-machine run r3 complete, 7/7 phases ok; report
    `docs/operations/phase20-spike-character-library.md`. Owner verdict: SDXL **base** (not
    Lightning), simpler character, **M2** composition (M1 rejected); the background vs
    on-screen-text layout is an open owner question (mockups A/B/C).
  - Both started before the Phase 21 gate on the owner's instruction (see "Owner
    decisions 2026-09-30").
  - PM original: "planning (task 20.1 doc-first card ready; starts after Phase 21 spike
    resolves)".
- **Planned:** 2026-09-29 (owner priority statement: natural voice → thumbnail + character
  images → music from text)
- **Controlling plan:** `docs/implementation/phase-20-ai-visuals.md`
- **Authorization:** owner decision D26 (2026-09-24, ENH-012: local AI thumbnails on the
  RTX 3060, cartoon/3D characters per topic) extended by owner's 2026-09-29 requirement
  that the same character stays recognizable across every image in an episode. Owner chose
  **IP-Adapter** for consistency and **shared VRAM model manager built first**.
- **Ownership of this folder:** PM until the handover commit, Coder after.

## Preflight

- Phase 19 at 7/9 + Gate B-12 PARTIAL (Remotion accepted, 19.9 default flip held).
- Phase 21 TTS in progress (StyleTTS 2 spike after Kokoro STOP).
- Full suite baseline **1205/1205**, ruff clean.
- Existing thumbnail path: 5 Pillow templates + Gemini headline/palette fill
  (Task 1.8a/1.8b). Working, shipped, and stays as the fallback (invariant 47).
- Existing avatar path: `speakers.avatar_image_path` column + upload/serve/delete service
  (Task 1.7c). Currently unused by any real project — **Task 20.4 reuses this rather than
  building a parallel path**, and Task 19.4's speaker chip already has an avatar render
  slot waiting for it.
- Real VRAM budget on the owner's RTX 3060 (12288 MiB total), measured by Coder in Task
  21.1b D21.1b-e with real `nvidia-smi`: **3916 MiB free with Ollama qwen3.5:9b loaded**,
  10286 MiB free at idle. Any image model above ~4 GB cannot coexist with qwen.

## Task status

| Task | Description | Owner | Status |
|---|---|---|---|
| 20.1 | Shared GPU model manager (load / free-VRAM check / unload, used by TTS + images + music) | Coder | **implemented; awaiting owner-machine verification + PM acceptance.** Design `b328fd3`, implementation `6b1e7f7`. 30 new tests, 0 new failures vs the cloud baseline. **Deviations from the PM card are listed for decision** in `tasks/task-20.1.md` Part 3 (R1–R6), notably opposite master-switch semantics (R4) |
| 20.2 | Image model spike + IP-Adapter consistency demo | Coder | **done: owner PASS, SDXL-Lightning** (2026-09-30). Report `docs/operations/phase20-spike-images.md` |
| 20.2b | Spike: character library feasibility (Ghibli-like style preset, 20-asset set, OpenPose actions, anime-seg cut-outs, M1 vs M2) | Coder | **run r3 complete (7/7 ok); owner verdict 2026-09-30: base over Lightning, simplify the character, M2 yes / M1 rejected, background-vs-text layout open.** Card `tasks/task-20.2b.md`; report `docs/operations/phase20-spike-character-library.md` |
| 20.2c | Spike v2: SDXL base + simple character + pose-controlled M2 (silhouette mask) -> 1280x720 video-frame mockups | Coder | **run r4 complete (4/4 ok); owner verdict 2026-09-30: style v2 rejected (wants a modern action-webtoon anime look), character not OK, strict pose, edge halo confirmed, captions/frames accepted.** Card `tasks/task-20.2c.md`; report `docs/operations/phase20-spike-character-v2.md` |
| 20.2e | Spike v3: Animagine XL 4.0 (anime SDXL, Open RAIL++-M), style A action-webtoon vs B bright anime, render-then-cut M2 | Coder | **run r5 complete (4/4 ok); owner verdict 2026-09-30: both anime styles rejected, odd character scale, characters sink into scenes; wants character-first work (Vietnamese, bright colours); the 20.2 r2 one-pass 3D-cartoon result was much better.** Card `tasks/task-20.2e.md`; report `docs/operations/phase20-spike-character-v3.md` |
| 20.2d | Caption style option (outline / box / bottom shade), user-selectable, Remotion path | Coder | **implemented** (design `1642a14`; owner-requested 2026-09-30). Card `tasks/task-20.2d.md`; real Remotion stills `docs/operations/phase20-caption-styles-remotion.png` |
| 20.3 | Thumbnail AI path behind opt-in toggle, Pillow templates as fallback | Coder | provisional |
| 20.4 | Character reference management (reuse `speakers.avatar_image_path` from Task 1.7c) | Coder | provisional |
| 20.5 | In-video character images (populate Task 19.4's existing avatar slot) | Coder | provisional |
| 20.6 | Gate B-14 (owner visual sign-off on thumbnails + character consistency) | PM | provisional |
| 20.7 | Close-out | Coder | provisional |

## Owner decisions 2026-09-30 (cloud session; for the PM's decision log)

- **Sequencing:** *"tôi nghĩ nếu chưa chạy được test thử giọng thì cứ làm các task tiếp
  theo"* ("I think that if the voice test can't be run yet, just go ahead with the next
  tasks"). 20.1 and 20.2 went ahead while 21.1b waits for the owner's GPU.
- **Task 20.1, Ollama takes the lease too** (Coder design D20.1-c): owner answered "có"
  (yes).
- **Task 20.2 Q1:** the channel **is monetized**. The owner wants everything *"miễn phí,
  hợp pháp, nhanh gọn, không dính watermark của bất kỳ hãng nào và không dính đến bản
  quyền"* ("free, legal, quick, no vendor watermark and no copyright entanglement") and no
  Stability AI registration. So **SDXL-Turbo is dropped** (its commercial use requires
  registration plus "Powered by Stability AI").
- **Task 20.2 Q2:** **FLUX.1-schnell is dropped** (owner "okey" to the recommendation).
  It has no commercially usable IP-Adapter (both are FLUX.1-dev non-commercial), needs
  about 18 GB of downloads, its 9.5 GB T5 exceeds the ~9.4 GB of free RAM, and it is
  gated.

## Proposed plan amendments (Coder → PM; the plan file itself is left to the PM)

- **§3 20.2 candidates:**
  - SDXL-Turbo → **SDXL-Lightning** (`openrail++`, 4-step **UNet**, as its README
    recommends for an SDXL base);
  - FLUX.1-schnell removed;
  - "SDXL + a cartoon/3D style LoRA" deferred as an add-on, with a licence check per
    LoRA.
  - The deliverable uses 5 real episodes, not 2–3, matching ENH-012's criterion.
- **§3 20.1:** see Part 3 of the Task 20.1 card (R1–R6).

## Evidence log

- **20.1** (2026-09-30, Coder): design `b328fd3`, implementation `6b1e7f7`, both in the
  cloud session. Evidence is in `tasks/task-20.1.md` Part 2. The owner-machine evidence
  (3-way VRAM probe, eviction, reload, full suite) comes through the owner runbook.
- **20.2** (2026-09-30, Coder): design `d787325` → Amendment A `fe1584c` → implementation
  `518fed8` → lease threshold 8192 (`4c0d1fb`). Evidence is in `tasks/task-20.2.md`.
- **Reconciliation** (2026-09-30, Coder): the PM commit `9b5c8f9` was recovered from the
  owner's unpushed local `main` (through the backup branch `owner-local/backup-20260930`)
  and merged. The cloud session's `20-ai-thumbnails/` folder was folded into this one.
- **Owner-machine run 1** (`owner-runs/20260930` @ `f08d59d`):
  - 1235/1235 passed on the owner's machine;
  - the PM D20.1-a probe settles R1 for `nvidia-smi` (torch can't see Ollama's memory);
  - the 20.2 image run failed on a Coder bug (fp32 UNet materialisation → os error
    1455), which is now fixed and verified;
  - 21.1b's venv step failed (an existing, locked `venv-styletts2`).
  - The retry is `docs/operations/owner-runbook-2026-09-30-r2.md`.
- **Owner-machine run r2** (`owner-runs/20260930-r2` @ `5fd2929`):
  - **20.1 live evidence complete.** The lease evicted qwen (4964 → 11836 MiB free);
    process exit returns VRAM to its baseline to within ±6 MiB; qwen reload takes 12.1 s.
    Report: `docs/operations/phase20-t1-model-manager.md`.
  - **20.2 run complete.** 10/10 backgrounds and 12/12 IP scenes, no OOM, no watermark.
    Base takes 21 s/image and Lightning 2.1 s/image. With the IP-Adapter the peak is 11.1
    GB. Report: `docs/operations/phase20-spike-images.md`.
  - Both are **awaiting the owner's visual verdict and PM acceptance.**
- **Owner verdicts 2026-09-30:**
  - **Phase 21: STOP.** Edge TTS stays.
  - **20.2: PASS, SDXL-Lightning**, plus a new direction: a Character Library + Scene
    Library composed per episode.
  - **Proposed Amendment B** (restructures 20.3+ into library backend / UI / composition
    / in-video, preceded by a 20.2b spike) is in `proposal-amendment-b-asset-library.md`,
    **owner answers recorded in §5 (`3f428ce`); PM approval pending.** The owner said
    "okey làm đi" to the 20.2b spike, which is implemented (card `tasks/task-20.2b.md`,
    runbook r3).
