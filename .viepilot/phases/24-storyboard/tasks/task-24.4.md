# Task 24.4 — Step 5 storyboard review and edit (doc-first card)

## Objective

Owner E3: the AI proposes, the owner reviews. The Step 5 page gains a **Storyboard** section where
the owner can:

- ask the AI for a proposal (24.2);
- see each beat with its script lines;
- edit the place, the people on screen, the action and the expression, and split or merge beats;
- see the image and GPU cost update live;
- save a draft, or approve.

Approval is what 24.5 will generate from.

## Paths

- `frontend/static/js/storyboard.js` (new, self-contained IIFE, like `characters.js`)
- `frontend/pages/step5_video.html` (section markup, styles, script tag)
- `frontend/static/js/api.js` (`getStoryboard`, `saveStoryboard`, `proposeStoryboard`)
- `tests/test_storyboard_browser.py` (new, Playwright, fake engine + fake AI router)

## File-Level Plan

- **api.js:** three calls: `GET`/`PUT /api/projects/{id}/storyboard` and `POST …/propose`.
- **step5_video.html:** a `<section id="storyboard-section">` after "Characters & scenes":
  - title and hint;
  - buttons `#storyboard-propose`, `#storyboard-save`, `#storyboard-approve`;
  - `#storyboard-summary` (beats, images/cap, GPU minutes, status/source, proposal path/reason);
  - `#storyboard-warnings`;
  - `#storyboard-beats`.

  Compact styles; `<script src="/static/js/storyboard.js">` after `step5_video.js`.
- **storyboard.js:**
  - **Loading:** reads `project_id` from the URL, then loads the project (speaker names), script
    lines, project visuals (cast), the scene library and the storyboard in parallel.
  - **Beat card** (`article.storyboard-beat[data-index]`):
    - header "Beat k · lines a–b";
    - a `<details>` with the lines as "speaker: text";
    - Kind select (scene / insert);
    - Place select: `<optgroup>` per scene category, plus "New place…", which reveals a text input
      (also used for an insert's subject);
    - speaker checkboxes (cast only, at most 2);
    - Action input (maxlength 40);
    - Expression select (the 7 values);
    - buttons "Split at line…" (a select of the beat's inner lines) and "Merge with next".
  - **Live summary:** `estimateImages(beats, castSize)` mirrors the server's `estimate_images`
    and turns the cap overrun red. "Unsaved changes" appears after an edit.
  - **Buttons:** Propose shows "Proposing…" and disables itself; Save sends `PUT` with
    status draft; Approve sends `PUT` with status approved. A 422 message is shown verbatim in
    `#storyboard-error`.
  - **Empty state:** with no script lines the section explains that a script is needed.
    "Propose with AI" is the primary action when there are no beats.

## Best practices

No inline handlers; DOM built with `createElement` and `textContent` (no HTML injection from
script text); all server calls go through `Api`; the server stays authoritative and the client
estimate is only a preview; buttons are disabled while a request is in flight; labels are tied to
their inputs for accessibility.

## Verification

`tests/test_storyboard_browser.py`:
- propose (fake AI router) → 3 beats render;
- editing the action and expression, then saving, persists across a reload;
- merging beats 1 and 2 updates the line range and the estimate;
- an invalid new place shows the server message;
- approving sets the status to approved.

Existing Step 5 browser tests stay green. Full suite green; ruff clean.

## Result (2026-10-05) — PASS

- Delivered as planned: `storyboard.js` (self-contained, DOM built with createElement/textContent),
  a Storyboard section on Step 5, and Api calls.
- Live check on the owner's library: on a project with finished audio the section loads in its
  empty state, with Propose enabled and Save/Approve disabled. On a project without audio, Step 5
  hides its whole workspace, including this section, the same as the shots. Moving the storyboard
  earlier (it needs only the script) is a follow-up for 24.5's UI.
- Test: `tests/test_storyboard_browser.py`, run against the fake AI router and the fake engine.
  - Propose → 3 beats at 9/12 images.
  - Edit an action and an expression → "unsaved changes".
  - Merge → lines 1–4 at 8/12.
  - Save, reload → edits persisted, "draft (owner)".
  - Invalid new place → the server's `new_place` message is shown.
  - Approve → "approved".
