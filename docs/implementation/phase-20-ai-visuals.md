# Phase 20 Implementation Plan — AI Visual Generation (thumbnails + consistent characters)

**Status:** OPEN 2026-09-29 (planning; task 20.1 doc-first ready). **Starts after Phase 21
spike resolves** (Coder is single-session; Phase 21 StyleTTS 2 spike must reach its
PASS/SCOPE-CUT/STOP gate first).
**Authority:** owner priority statement 2026-09-29 — three features requested in order:
natural voice (Phase 21, running), thumbnail + character images (this phase), music from
text (Phase 22, queued). Owner chose **IP-Adapter** for character consistency and
**shared VRAM model manager built first** (both decisions 2026-09-29).
**Supersedes:** ENH-012 / owner decision D26 (2026-09-24) which scoped "AI thumbnails on
the RTX 3060, cartoon or modern 3D characters invented per lesson topic". This plan keeps
that goal and adds owner's newer requirement: the same character stays recognizable across
every image in an episode, not just the thumbnail.

## 1. Goal

Replace the current template-based thumbnail path (5 Pillow templates + Gemini text fill,
Task 1.8) with real AI-generated imagery, and extend it so each speaker has a recognizable
character that persists across the thumbnail and any in-video images.

Two distinct capabilities:

1. **Thumbnail generation** — one AI image per episode, driven by the episode's topic. The
   existing Pillow text-overlay layer stays (it already handles headline/palette well); only
   the background becomes AI-generated instead of a fixed template.
2. **Character consistency** — each speaker (Alex, Maya, …) gets one reference image. Every
   generated image that includes that speaker preserves their appearance via IP-Adapter
   conditioning. Same underlying idea as StyleTTS 2's voice cloning from a reference clip:
   supply one sample, the model imitates its characteristics.

## 2. Invariants (in addition to Phases 13–21)

46. **Local-only.** Image generation runs entirely on the owner's RTX 3060. No cloud image
    API, no per-image cost. Consistent with owner decision D26 ("no paid image generation").
47. **Fallback is always available.** If the image model is missing, OOM, or fails, the
    existing 5-template Pillow path renders the thumbnail exactly as it does today. A
    no-model install behaves like today.
48. **VRAM is shared, never assumed.** Every model load goes through the shared manager
    (Task 20.1). No component assumes it owns the GPU.
49. **Licence.** Whatever base model is chosen must permit commercial use. Verified at the
    spike and re-verified at the gate. Recorded in the spike report.
50. **Reference images are the owner's own.** Character reference images are supplied by
    the owner (upload or pick from generated candidates). The app never fabricates a
    likeness of a real person, and never uses a reference the owner did not provide.

## 3. Tasks

Order: **20.1 (model manager, Coder) → 20.2 (image spike, Coder) → 20.3 (thumbnail AI path,
Coder) → 20.4 (character reference management, Coder) → 20.5 (in-video character images,
Coder) → 20.6 (Gate B-14, PM) → 20.7 (close-out, Coder).**

### 20.1 — Shared GPU model manager (Coder, P0, foundation)

**See:** `.viepilot/phases/20-ai-visuals/tasks/task-20.1.md`.

The problem this solves, in real numbers already measured by Coder in Task 21.1b:

| Model | VRAM | Measured by |
|---|---|---|
| Ollama qwen3.5:9b | 7–8 GB (3916 MiB free when loaded, of 12288) | Task 21.1b D21.1b-e, real `nvidia-smi` |
| StyleTTS 2 | 4–6 GB | Task 21.1b (spike in progress) |
| SDXL + IP-Adapter | 8–9 GB (estimate; 20.2 measures) | — |
| ACE-Step (Phase 22) | 10–11 GB (estimate) | — |

None of these can coexist. The production pipeline is already sequential (script → learning
→ TTS → music → images → video), so each stage can own the GPU briefly and release it. What
is missing is a single component that does the load / check-free-VRAM / unload discipline
once, rather than three phases each inventing their own.

Without it, Phase 20 and Phase 22 would each write a separate VRAM strategy, and the first
real run where two of them overlap would fail in a way that is hard to diagnose.

### 20.2 — Image model spike (Coder, provisional)

Spike-first, same discipline as Phase 19.1 and Phase 21.1/21.1b. Measures on the owner's
real machine, produces real sample images, owner judges.

Candidates to evaluate (spike picks, does not assume):
- **SDXL base + a cartoon/3D style LoRA** — ~6–8 GB, mature IP-Adapter support, large free
  LoRA ecosystem, CreativeML Open RAIL++-M licence (commercial use permitted — verify at
  spike).
- **SDXL-Turbo / SDXL-Lightning** — same family, 1–4 step inference, much faster, slight
  quality trade-off.
- **FLUX.1-schnell** — Apache 2.0, highest quality, but ~11–12 GB on this card. Tight.
  IP-Adapter support is newer and less proven.

Deliverable: real generated images for 2–3 real episode topics, a measured VRAM/time table,
an IP-Adapter consistency demonstration (same reference → 3 different scenes, owner judges
whether the character stays recognizable), and a PASS / SCOPE-CUT / STOP proposal.

### 20.3 — Thumbnail AI path (Coder, provisional)

New AI background generation behind the same opt-in discipline as Phase 19.7's renderer
toggle: request flag → env kill switch → fallback to the existing 5 Pillow templates.
Existing headline/palette editor (Task 1.8b) is untouched — it composites over the new
background exactly as it does over a template PNG today.

### 20.4 — Character reference management (Coder, provisional)

- Per-speaker reference image, stored alongside the existing `speakers.avatar_image_path`
  column (Task 1.7c already built upload/serve/delete — reuse it rather than adding a
  parallel path).
- Owner either uploads a reference or generates candidates and picks one.
- Invariant 50: the app never invents a likeness; the owner supplies or approves it.

### 20.5 — In-video character images (Coder, provisional)

Render the consistent character into the Remotion composition — most likely alongside the
existing speaker chip (Task 19.4 already has an avatar slot that is currently unused because
no project has avatars). This task may be small if 20.4 populates that existing slot.

### 20.6 — Gate B-14: owner visual sign-off (PM)

Real generation on ≥3 real episodes, owner judges thumbnail quality and character
consistency. Same shape as Gate B-12. Report `docs/operations/phase20-gate-b14.md`.

### 20.7 — Close-out (Coder)

Flip the image default on gate PASS, version bump, tag.

## 4. Session partition

As in Phase 16 §6. PM plans, reviews, runs gates. Coder implements. Live channel
`SendMessage`. Git is the record.

## 5. Version

Enters at whatever Phase 21 leaves. Closes one minor bump above it on Gate B-14 PASS.

## 6. Sequencing with Phase 21 and Phase 22

Coder is a single session, so these run one after another:

1. **Phase 21** (running) — StyleTTS 2 spike → gate → either the remaining 21.x tasks or a
   `wontfix` close.
2. **Phase 20.1** (this plan) — model manager. Valuable regardless of how Phase 21 resolves,
   because Phase 20 and 22 both need it.
3. **Phase 20.2 onward** — image work.
4. **Phase 22** — music generation (ACE-Step-1.5 or MusicGen, spike decides). Plan written
   when Phase 20 nears its gate.
5. **Phase 19.9** — the held Remotion default flip, bundled into whichever release ships
   next.

## 7. Amendments

_(None yet.)_
