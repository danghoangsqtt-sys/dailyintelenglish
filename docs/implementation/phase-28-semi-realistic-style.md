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
| 28.2 | **Character reference sheets:** a turnaround sheet per character (full body front and back, face front, profile, three-quarter, head from above) from the picked faces, with a detailed prompt per view; the woman 160 cm / 50 kg slim hourglass in white, the man 180 cm / 80 kg lean muscular in black | the owner approves the two sheets |
| 28.3 | **Recipes + checks:** replace `STYLE_CEL_ANIME` and the outfit/negative prompts with the chosen look; outfits become single colour (the woman white, the man black), so the library rule "different top and bottom colour" and the colour check are adapted; RealVisXL replaces SDXL base in the worker; keep the prompt budget under 77 tokens | recipe tests green; a smoke on 3 shots keeps the colour and extra-person checks passing |
| 28.4 | **Redo the library:** the two characters (from the 28.2 sheets, locked) and the 55 scene plates | the owner approves the characters and a plate sample |
| 28.5 | **Gate B-20:** one full real episode in the new style | owner PASS |

## 1b. Decisions after the spike (2026-10-06)

- Look: crisp editorial photograph on **RealVisXL V5.0** (openrail++, owner approved the download). The
  Animagine and Ghibli models were removed.
- The woman: long straight black hair, fair skin, all white, no glasses (the brown-haired, round-glasses
  presenter of the logo is superseded). The man: the round 6 face, fair and refined, all black.
- Details and images: `docs/operations/phase28-spike-style.md`.

## 2. Notes

- The logo and the banner show real-looking people: they are used as a **style** reference only, and the
  characters are original (no likeness copying).
- IP-Adapter identity references keep working with semi-realistic faces; a face crop may need a different
  `ip_adapter_scale`.
- Time: a shot is about 90 s on the RTX 3060, so a spike is minutes and a full episode is about 20 minutes.
