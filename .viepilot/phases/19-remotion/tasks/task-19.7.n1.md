# Task 19.7.n1 — Step 5 "Enhanced" toggle tooltip clarity (nit)

- **Status:** not started (doc-first card, awaiting Coder pickup — small nit, ~30-60 min)
- **Owner:** Coder
- **Priority:** P2 (nit; owner feedback from Gate B-12 live test 2026-09-29 —
  "nội dung ghi chú của nút không rõ ràng, ví dụ có hay không có karaoke script")
- **Dependency:** none
- **Controlling context:** owner Gate B-12 feedback; existing Step 5 toggle in
  `frontend/pages/step5_video.html` + `frontend/static/js/step5_video.js`

## Goal

Owner's real feedback: the "Enhanced (Remotion, opt-in)" pill doesn't tell the user
what "Enhanced" actually adds. Owner expected the label to say what features they get
(karaoke? subtitle style? something else?). This is a copy fix, not a feature change.

## Allowed files

- **Modify** `frontend/pages/step5_video.html` — toggle button label + tooltip text
- **Modify** `frontend/static/js/step5_video.js` — if the tooltip text is dynamically
  built from a JS constant (recommend keep the source-of-truth in one place)
- **Modify** `.viepilot/phases/19-remotion/PHASE-STATE.md` — one evidence log line
- `CHANGELOG.md` — one bullet under `[Unreleased]`

**Not allowed:** any backend file. No `app/`. No new dependencies. Pure copy fix.

## Design decisions (Coder, doc-first — 1-paragraph commit under `docs(review)` OK given
scope)

### D19.7n1-a: Exact tooltip copy

Recommend (PM draft — Coder polishes):

> **"Enhanced (Remotion): word-by-word karaoke highlight, speaker name chip, vocabulary
> pop-up cards, intro title + outro CTA, chapter progress bar. Higher-quality YouTube
> output. Slower render than Standard (about 3× wall time)."**

Key: audience is the creator (owner) picking the button, not a developer. Say what
features they GET, not the technology. "About 3× wall time" sets honest expectation
(Gate B-12 data: 62s Remotion vs 7s ffmpeg on B1 2:56).

If the tooltip length feels too long for the actual UI: split into a short label + a
detailed tooltip on hover. Recommend keeping full text on hover; button label stays
"Enhanced (Remotion, opt-in)".

Also: when the button is disabled (Remotion not available), tooltip should say:
> **"Enhanced rendering requires Node.js and Chrome Headless Shell. Not installed on
> this machine — see `scripts/check_dependencies.py`. Standard (ffmpeg) rendering still
> works."**

### D19.7n1-b: Vietnamese fallback?

Phase 4.3 UI localization was dropped 2026-09-16 (owner explicit decision — UI stays
English). Keep tooltip English. Do NOT add Vietnamese translation.

## Verification

- Real browser check: hover the button, tooltip appears with new text.
- Disabled state: same check with `DIE_VIDEO_RENDERER=ffmpeg` env — different tooltip
  text appears, button click does nothing.
- No test change needed; existing browser tests don't assert tooltip content.
- Full suite still 1205/1205; ruff clean.

## Evidence (handover)

- Two shas (design commit is optional given scope — one commit total is fine if the
  design paragraph is inside the commit message).
- Screenshot of hover state showing new tooltip text.
- Screenshot of disabled state showing different tooltip text.

## Definition of done

- New tooltip text visible on hover in owner's browser.
- No app/backend files touched.
- Owner satisfied that button purpose is now clear.
