# Task 24.5 — Shots and video timeline from the approved storyboard (doc-first card)

## Objective

Once the owner approves a storyboard (24.4), "Generate shots" makes the pictures the beats need,
and the Enhanced (Remotion) video shows them as the lines are spoken. Pictures follow places and
actions (owner E4). With no approved storyboard, today's per-scene shot set and timeline rule stay
exactly as they are (backward compatible).

Two sub-tasks with separate commits: **24.5a** shots from beats, **24.5b** timeline from beats.

## Paths

- `app/db/migrations/011_beat_shots.sql` (new)
- `app/services/visuals/project_visuals_service.py` (`prepare_storyboard_shots`, `assign_beat_shots`)
- `app/services/visuals/pipelines.py` (beat prompts/poses for people shots, insert shots)
- `app/services/visuals/storyboard_service.py` (`approved_beats`, `materialize_new_places`)
- `app/services/video_renderer_remotion.py` (beat timeline when a storyboard is approved)
- `tests/test_storyboard_shots.py` (new)

## File-Level Plan

### 24.5a — shots from beats

- **011_beat_shots.sql:** `project_shots` gains:
  - `action TEXT NOT NULL DEFAULT ''`;
  - `expression TEXT NOT NULL DEFAULT 'calm'`;
  - `subject TEXT` (an insert's picture);
  - `beat_position INTEGER` (NULL for a place's framing set).

  Inserts use `kind = 'insert'` and `scene_id = ''` (the column is NOT NULL; there is no place).
- **storyboard_service:**
  - `approved_beats(db, project_id)` → beats, only if the storyboard is approved.
  - `materialize_new_places(db, project_id)`: each beat `new_place` (scene kind) becomes a user
    library scene with these properties:
    - name: Title-cased, made unique;
    - category: other;
    - staging: standing;
    - a new seed.

    The beats then point at it, so the place gets a plate (23.2) and is reusable.
- **project_visuals_service.prepare_storyboard_shots(db, project_id):** requires an approved
  storyboard and a cast, then materializes places. Per place, in order of first appearance:
  - its **framing set**: singles per cast member + duo close + duo wide when cast ≥ 2, carrying
    the first beat's action and expression;
  - **one action shot** per later beat in that place with a different action: a duo wide when two
    people are on screen, else a single of the one on screen;
  - per insert, **one insert shot** (`subject` = `new_place` or `action`).

  The count equals `estimate_images` (asserted).
- **pipelines:**
  - people shots with an action or a non-calm expression use `recipes.beat_*_prompt` and
    `geometry.beat_people` (category from the action); legacy rows (no action, calm) keep today's
    prompts and poses exactly;
  - insert shots render in L0 text2img (no IP, no ControlNet) from
    `style + subject + "wide view, detailed"`, with `PLATE_NEGATIVE` when no person is on screen;
    final = raw.
  - The `project_shots` job uses `prepare_storyboard_shots` when an approved storyboard exists,
    else `prepare_shots`.

### 24.5b — timeline from beats

- **assign_beat_shots(lines, beats, shots):** per beat:
  - an insert shows its insert shot;
  - a scene beat's first line shows the beat's action shot (else the place's duo wide);
  - every 4th line shows the duo close;
  - the other lines show the speaking person's single.

  Fallbacks: single → duo close → duo wide → any shot of the place → None (midnight).
- **video_renderer_remotion:** uses `assign_beat_shots` when the project has an approved storyboard
  and complete shots; else today's `assign_line_shots`.

## Best practices

Additive migration; one place for "which pictures does this storyboard need" (`prepare_*` asserts
equality with `estimate_images`); legacy path untouched (tests prove the old shot set and
timeline are byte-identical); GPU-free tests with the fake engine.

## Verification

`tests/test_storyboard_shots.py`:
- approved-only;
- new place → library scene with a plate;
- shot specs (framing set, action shots, inserts) equal the estimate;
- the pipeline sends beat prompts and poses only for beat rows;
- insert rows go through text2img without IP;
- the legacy project keeps its old 4-shot set;
- beat timeline (insert lines, first-line action shot, speaker singles, fallbacks);
- Remotion props use the beat timeline only when approved.

Real GPU smoke on the owner's machine for one approved storyboard. Full suite green; ruff clean.

## 24.5a result (2026-10-05) — PASS

- Delivered as planned, plus:
  - `POST …/visuals/shots` accepts a project with no chosen scenes when its storyboard is approved
    (draft + no scenes → 422 "…or approve a storyboard…");
  - shot views carry `scene_name` ("Inserts" for inserts);
  - Step 5 groups shots by their own place and shows the action and expression.
- Tests: `tests/test_storyboard_shots.py`, 3 passed:
  - specs order/kinds/positions;
  - draft keeps the legacy path;
  - approved → 10 shots;
  - new place → library scene "Quiet tea house" with a plate, and its beat re-pointed;
  - the insert goes through text2img with the people-free negative and no IP keys;
  - beat prompts carry "warm smile, drinking coffee";
  - an insert can be regenerated.
- Full suite: the first run had live-server start timeouts under load (each passed when run alone).
  The rerun gave **1363 passed**.

## 24.5b result (2026-10-05) — PASS; Task 24.5 closed

- `assign_beat_shots`:
  - insert → its illustration;
  - a beat with its own action shot opens on it and alternates it with the speaker's single;
  - otherwise the beat opens wide, shows the duo close on every 4th line and the speaker's single
    in between;
  - fallbacks as before.
- `storyboard_timeline_ready` keeps the per-scene rule until every storyboard place has a complete
  shot. Remotion props use the beat timeline when it is ready.
- The `insert` shot kind was added to the Remotion schema; the vocab card stays top-right on
  inserts (vitest).
- **Real end-to-end smoke** on a copy of the owner DB ("Trial Run 8min", 33 lines, Lan + Minh;
  sheet `docs/operations/phase24-t5-storyboard-smoke.png`):
  - Gemini proposed in 4.8 s (path ai, trimmed 1 step, 12/12 images): office → crowded subway at
    rush hour (insert) → office → empty boutique coffee bar (insert) → office → person working
    alone at home (insert) → cafe.
  - Approve → 12/12 shots complete in 1031 s on the RTX 3060.
  - The inserts illustrate exactly what the lines describe; all four cafe shots show coffee cups
    (drink pose).
  - Weak: the "looking at a city skyline chart" action shot shows no chart; Lan's top drifts
    (navy over-jacket, blue vest) in 2 shots.
- Tests:
  - `tests/test_storyboard_shots.py`: +2 (beat timeline with fallbacks/readiness, Remotion props
    from a generated storyboard);
  - vitest 39 passed; tsc clean;
  - full suite **1365 passed**.
