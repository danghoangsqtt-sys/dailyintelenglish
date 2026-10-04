# Task 20.11 — Duo fixes: third person in duo_close, top-colour drift (doc-first card)

**Evidence:** r9 (refine on/off) and the 20.9 smoke both show `Cafe_duo_close` with a third
person — a second, back-turned copy of the left character (yellow top) in the gap between the
two skeletons — and the male top drifting to yellow/cream in duo shots (r9: 10 colour
mismatches per run).

## Hypotheses

- **H1 (identity spill):** the IP-Adapter masks are image *halves*
  (`geometry.half_masks`). The empty middle of `duo_close` lies inside the left half, so the
  left face identity is applied to empty space and the model paints that character again.
  → Use person **silhouette masks** (`geometry.refine_mask(person, size, half)`, already used
  by the refine pass) as the IP masks in the L2 render.
- **H2 (wording):** "two … people talking face to face" + no count guard. → Add a count
  phrase ("only two people") and negative "three people, group, back view" (within 77 tokens).
- **H3 (colour drift):** the refine prompt reads character → style → garments, and the
  duo prompt names the left person's colour first, which bleeds. → Refine prompt leads with
  the garment colour (`"<top colour> <top item>"` first after the style), refine strength
  0.55 → 0.65.

## Method (GPU, owner's machine)

Harness `scripts/spike_duo_fixes.py` reuses the real pipeline helpers with the real locked
Lan + Minh faces, scenes Cafe + Classroom, `duo_close` + `duo_wide`, seeds 1 and 2:
variant **A** today's pipeline, **B** = H1, **C** = H1 + H2 + H3. Contact sheet
`docs/operations/phase20-t11-duo-fixes.png`; count per image: extra persons, top-colour
mismatches (Lan yellow, Minh light blue).

## Accept

The chosen variant has 0 extra persons on the 4 `duo_close` images and fewer colour mismatches
than A; then it is wired into `pipelines._generate_set` (+ unit tests on the mask choice and
prompt token budget), visual tests + ruff green.
