# PHASE-STATE — Phase 24: Story-driven visuals (storyboard)

- **Status:** open 2026-10-05 (`/vp-auto` "thực hiện bước tiếp theo"; Phases 20 and 23 wait only
  on owner Gates B-14 / B-15).
- **Plan:** `docs/implementation/phase-23-24-scenes-and-storyboard.md` §4 (owner E3: AI proposes,
  owner reviews; E4: few images by story beats, default cap 12).

| Task | Description | Owner | Status |
|---|---|---|---|
| 24.1 | Beat schema + migration + validated storyboard API (GET/PUT) + image estimate | Claude | **done 2026-10-05**: migration 010, models, service, GET/PUT API, estimate + cap; 9 tests; full suite 1305 passed |
| 24.2 | AI storyboard via the gateway (validated, repaired, deterministic fallback) | Claude | **done 2026-10-05**: POST …/storyboard/propose; normalization + fit_to_cap from real Gemini runs (5/5 AI after fixes); 9 tests |
| 24.3 | Recipes v3: action + expression slots, pose library | Claude | **done 2026-10-05**: 8 action poses, beat prompts with expression + budget guard; GPU sheet 7/9 actions read clearly (think/work weak, expressions subtle); 45 tests |
| 24.4 | Step 5 storyboard review/edit UI | Claude | **done 2026-10-05**: Storyboard section on Step 5 (propose, edit place/people/action/expression, split/merge, live cost, save/approve); Playwright flow test |
| 24.5 | Generation + timeline from beats (24.5a shots, 24.5b timeline) | Claude | **done 2026-10-05**: shots + timeline from the approved storyboard; real smoke 12/12 shots in 1031 s (AI 4.8 s, 3 content inserts); full suite 1365 passed |
| 24.6 | Remotion polish (crossfade, pan/zoom, inserts) | Claude | planned |
| 24.7 | Gate B-16 (owner) | Owner | planned |
