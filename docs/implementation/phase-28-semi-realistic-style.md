# Phase 28 — Semi-realistic picture style like the channel banner (ENH-019)

**Status:** planned 2026-10-06 from `docs/brainstorm/session-2026-10-06.md` (D58, D59).
**Supersedes** the cel-anime style of Phase 20.9 (owner, 2026-10-06: "phong cách vẽ vẫn còn rất xấu").

## 0. Goal

Illustrations of episodes (characters, scene plates, shots, inserts) look like the banner:
semi-realistic, soft natural light, warm beige/brown tones, believable faces, glasses on the presenter.

## 1. Plan

| Task | What | Accept when |
|---|---|---|
| 28.1 | **Spike (GPU):** the same 3 prompts (the presenter, a male student, a cafe scene) on SDXL base 1.0 with semi-realistic recipes (photographic wording, soft light, shallow depth, no cartoon terms, a bigger negative prompt). If base is not enough, list 2–3 commercially licensed fine-tunes for the owner to approve a download | the owner picks a look from side-by-side images |
| 28.2 | **Recipes + checks:** replace `STYLE_CEL_ANIME` and the outfit/negative prompts with the chosen look; re-tune the colour check and the extra-person check on the new look; keep the prompt budget under 77 tokens | recipe tests green; a smoke on 3 shots keeps the colour and extra-person checks passing |
| 28.3 | **Redo the library:** the presenter (glasses, brown wavy hair) and a male character, locked; redo the 55 scene plates in the new look | the owner approves the characters and a plate sample |
| 28.4 | **Gate B-20:** one full real episode in the new style | owner PASS |

## 2. Notes

- The logo and the banner show real-looking people: they are used as a **style** reference only, and the
  characters are original (no likeness copying).
- IP-Adapter identity references keep working with semi-realistic faces; a face crop may need a different
  `ip_adapter_scale`.
- Time: a shot is about 90 s on the RTX 3060, so a spike is minutes and a full episode is about 20 minutes.
