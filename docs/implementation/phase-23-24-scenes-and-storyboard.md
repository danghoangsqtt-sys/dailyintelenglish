# Plan — Character flow close-out, Scene Library v2 (Phase 23), Story-driven visuals (Phase 24)

**Status:** plan, written by PM (Claude) 2026-10-05 after `/vp-audit`; owner answers recorded in §0.
**Supersedes:** spec §1 "out of scope: the script LLM choosing scenes or expressions per line"
(`docs/implementation/phase-20-ai-visuals-feature-spec.md`), which this plan brings in scope.
**Execution order (owner, 2026-10-05):** Phase 20 close-out → Phase 23 → Phase 24 → Phase 22 (music).
Phase numbers stay stable; 22 was reserved for music before this plan existed.

## 0. Owner decisions (2026-10-05)

| # | Decision |
|---|---|
| E1 | **O11 stands.** Remove "Studio Ghibli style" from the recipes and the franchise-named style LoRA support; keep the look with neutral words, verified by an A/B GPU run (Task 20.10). |
| E2 | Order: characters → scenes → story → music. |
| E3 | The storyboard is **AI-proposed, owner-reviewed**: Step 5 shows the beats for editing before any GPU time is spent. |
| E4 | **Few images, chosen by story beats, not by duration.** Owner: "a conversation doesn't need that many images". Images change when the *place or action* changes; framing changes (wide → duo close → single of the speaker) give the motion in between. Default cap 12 images per episode (setting). |

## 1. Where we are (audit 2026-10-04)

- Character Library: built (20.3–20.5), cel-anime recipes (20.9), Lan + Minh regenerated and locked.
- Scene Library: a name + one-line `place` + `staging` (standing/seated) + optional preview;
  6 built-ins. Shots are generic ("talking with a hand gesture") and
  `assign_line_shots()` cycles 4 shots per scene by a fixed rule, blind to the script.
- Open quality issues: `duo_close` sometimes has a third person; the male top drifts to
  yellow/cream in duo shots (r9 and 20.9 smoke).

## 2. Phase 20 close-out (character flow stable)

| Task | What | Accept when |
|---|---|---|
| 20.10 | **O11 neutral style.** Replace the style prefix with neutral words (e.g. "hand-drawn 1990s anime film still, clean ink outlines, flat cel shading, lush painted background, warm sunlight, vivid colors"); remove `style_lora` from worker/engine/config and the `peft` note. A/B on GPU at the 20.9 seeds (with name vs without). | owner judges the neutral look equal or acceptable; tests green |
| 20.11 | **Duo fixes.** (a) third person in `duo_close`: test "two people only" wording + `1 man and 1 woman` count words + negative "three people, group"; check the two-skeleton pose image for a stray limb set; (b) top-colour drift: per-person refine prompt leads with the garment colour, refine strength 0.55 → 0.65 A/B. Measured on the r9 seed set (count of extra persons, colour mismatches). | extra persons 0/2 duo_close at both seeds; colour mismatches clearly below r9's 10 |
| 20.12 | **Gate B-14** on one real episode in the owner's library with Lan + Minh (Step 5 cast + 2 scenes + shots + Enhanced render). | owner visual PASS → tag `die-vp-p20-complete` |

## 3. Phase 23 — Scene Library v2

Goal: places that look like the references (painted, sunlit, detailed) and are reusable,
recognisable settings across many episodes.

| Task | What |
|---|---|
| 23.1 | **Spike: scene consistency.** Can several shots in one scene look like the *same* place? Compare at fixed seeds: (a) text only (today), (b) scene preview as a second, low-weight IP-Adapter image (general `ip-adapter_sdxl_vit-h`, measure VRAM against the 12 GB card with the face adapter + ControlNet), (c) preview as a background plate + character inpaint (the 20.2b "M2" path the owner accepted). Report + owner pick. |
| 23.2 | **Scene model v2** (additive migration): `category` (home, school, work, city, nature, travel, food), `time_of_day` (morning/day/sunset/night), `indoor`, `prompt_place` (token-capped), `seed`, preview in the cel-anime style; whatever 23.1 needs (plate path / reference weight). |
| 23.3 | **Built-in pack ≈ 16 places** matching common lesson topics: living room, home desk, kitchen, bedroom, café, restaurant, market, classroom, library, campus, office, meeting room, city street, bus/subway, park, countryside path. Upgrade rule as in the reverted 20.9 attempt: only rows the user has not edited; every place text measured ≤ the token budget of the longest recipe. |
| 23.4 | **Scene Library UI:** grid of previews by category, create/edit/duplicate, regenerate preview, "used in N projects". |
| 23.5 | Gate B-15: owner reviews the 16 previews + one consistency sheet per 23.1's pick. |

## 4. Phase 24 — Story-driven visuals (storyboard)

Goal: pictures follow the script, so a lesson reads as a small story.

**Beat model** (what the AI proposes, the owner edits):

```
beat = { line_from, line_to,             # contiguous script lines it covers
         kind: "scene" | "insert",        # scene = dialogue in a place; insert = illustration
         scene_id | new_place,            # library scene, or a proposed new place (added on accept)
         speakers: [speaker_index...],    # who is on screen (0, 1 or 2)
         action: str (<= 8 words),        # "ordering coffee", "pointing at a map"
         expression: one of calm|smile|laugh|surprised|thinking|worried|serious }
```

- A `scene` beat reuses that scene's framing set (wide / duo close / singles); the timeline
  picks the framing per line (speaker single while one person talks; duo close on turn
  exchanges; wide at the beat start). Only one new image per `(scene, action)` pair.
- An `insert` beat is one illustration of what is described (with or without the characters),
  shown for its lines; capped at 3 per episode by default.
- Budget: generation refuses above the cap (setting, default 12) and the review UI shows
  the count and the estimated GPU minutes before the owner presses Generate.

| Task | What |
|---|---|
| 24.1 | Storyboard schema + migration (`project_beats`), Pydantic model, validation (ranges contiguous and complete, speakers in cast, action/expression limits, cap). |
| 24.2 | **AI storyboard** through the existing AI gateway (cloud-first chain + local fallback): strict JSON prompt with the project's scene list + cast, schema validation, one repair attempt, **deterministic fallback** = today's rule turned into beats (so a failed AI call never blocks the video). |
| 24.3 | **Recipes v3:** action + expression slots inside the 77-token budget (measured table like 20.9); a small **pose library** mapped from action categories (talk, point, hold cup/phone, write, walk, sit at desk, wave) built on the existing OpenPose geometry; expression words tested per character. Spike-style GPU sheet before wiring. |
| 24.4 | Step 5 **storyboard review**: beat list with the script lines it covers, editable scene/action/expression/speakers, merge/split beats, image count + GPU-minute estimate, Generate. |
| 24.5 | Generation from beats (dedupe identical shots, reuse a scene's framing set, regenerate one beat) + timeline from beats replacing `assign_line_shots()` (the rule stays as the fallback). |
| 24.6 | Remotion polish: crossfade on beat change, per-shot pan/zoom direction (still subtle, O8), inserts full-bleed with the speaker chip kept. |
| 24.7 | Gate B-16: two real episodes (one dialogue, one interview), owner sign-off: "the pictures follow what is said". |

## 5. Risks

- **Same-place consistency** is the hardest part; 23.1 decides it before any UI is built.
- **Action fidelity:** SDXL + pose can do common gestures; held objects (cup, phone) are
  error-prone, hence the hand repair pass stays and actions are a short list first.
- **Token budget:** every new slot competes with the 77 tokens; each recipe change re-runs
  the measured table (the place text sits last and is cut first).
- **AI JSON reliability:** validated + repaired + deterministic fallback (Phase 13–17 lessons).

## 6. Working model

PM (Claude Opus) writes each task card doc-first and commits it before implementation
(audit lesson); implementation by the Coder session or Claude per task; GPU evidence runs
on the owner's machine; owner gates B-14, B-15, B-16.
