# Task 19.4 — Active-speaker indicator (name chip + optional avatar highlight)

- **Status:** not started (doc-first card, awaiting Coder pickup)
- **Owner:** Coder
- **Priority:** P0 (second user-visible payoff of the Remotion path; complements 19.3's
  karaoke by adding "who is talking")
- **Dependency:** Task 19.3 accepted (`c48037d`, PM task-level 2026-09-28 — no owner
  decision needed, clean delivery, no incident, no gate crossed)
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.4" ("A speaker
  chip (name + optional avatar) that highlights when its speaker's line is playing, matching
  Step 4's existing speaker-panel colors. Uses the same `speakers` rows the video already
  reads."); Phase 19 invariants 36–40; ENH-013 scope item 2

## Goal

Show viewers which speaker is talking right now. Persistent chip(s) rendered on screen — one
per project speaker — with the currently-active chip visually highlighted (color/scale/glow)
while its speaker's line plays. If a speaker has an uploaded avatar (`speakers.avatar_image_path`
non-null), the chip renders the avatar image + name; otherwise it renders the name only. Same
"opportunistic when data present, degrades gracefully when absent" pattern as 19.3's karaoke.

No `VideoService` wire-up (that's 19.7). Same demo runner as 19.1–19.3 — the same
`b330d37f...` 2:56 B1 episode gets re-rendered end-to-end and spot-checked.

## Real data preflight (already verified read-only from PM side)

- Demo project's speakers (`b330d37f...`): **Alex** (male, american) and **Maya** (female,
  american), **both with `avatar_image_path = NULL`.** This task's demo therefore exercises
  the name-only chip path, not the avatar path. Avatar rendering must still be designed and
  implemented (opportunistically active on any project that has avatars uploaded via
  `/step5`'s avatar UI, Task 1.7c) — its correctness is verified via vitest, not the demo
  render.
- Speaker schema column is `avatar_image_path` (verified via `PRAGMA table_info(speakers)`),
  not `avatar_path` — the design must use the real column name.

## Allowed files

- **Modify** `video-renderer/src/types.ts` — extend the input-props schema (zod) with a new
  top-level `speakers: Array<{id: string; name: string; gender: string; avatar_url?:
  string}>`. Every line's existing `speaker` (name string) stays for backward-compat with
  the 19.1 spike composition; a new `line.speaker_id` field carries the real DB id so the
  chip can match line → speaker unambiguously (a project could have two "Alex"es across
  speaker rows — never name-match, always id-match).
- **Modify** `video-renderer/src/Episode.tsx` — add a `<SpeakerChips>` component rendered as
  a persistent overlay (position TBD in D19.4-a) alongside the existing `<CaptionBand>`.
  Each chip shows the speaker's name (and avatar image if `avatar_url` present); the chip
  matching the current active line is visually distinguished.
- **New** `video-renderer/src/speakers.ts` — pure helper
  `activeSpeakerId(currentTimeSec: number, lines: Line[]) -> string | null`. Returns the
  `speaker_id` of the line whose `startSec <= currentTimeSec < endSec`, or `null` in gaps
  (between lines, before line 0, after last line). Keep it a standalone helper, not
  inlined into `Episode.tsx`, so vitest can exercise it in isolation.
- **New** `video-renderer/src/speakers.test.ts` — vitest for `activeSpeakerId`. Coverage
  targets: correct id inside a line, `null` in a gap between lines, `null` before line 0,
  `null` after last line, correct id at exact boundary (spec the tie-breaking rule
  explicitly — recommend "startSec inclusive, endSec exclusive", same as SRT convention).
  Revert-and-confirm-failure required (same discipline as 19.3's `karaoke.test.ts`).
- **Modify** `scripts/run_remotion_spike.py` — read the project's `speakers` rows
  (`mode=ro` DB connection, same as existing pattern), add each line's `speaker_id` and the
  project-level `speakers` array to the props. For any speaker with a non-null
  `avatar_image_path`, copy the file into `video-renderer/public/avatars/` and set
  `avatar_url` to `avatars/<filename>` (Remotion's `staticFile()` will resolve it, same
  pattern as the audio file in 19.1). Skip the copy silently for `NULL` avatars. **Never
  write to the real `data/avatars/` directory** — the copy is a one-way read-from-real-DB,
  write-to-video-renderer-scratch operation.
- **New** `docs/operations/phase19-t4-speaker.md` — task-scoped report (do not amend the
  spike report or the t3 report). Covers: chip design decisions, render wall time (compare
  to 19.3's ~95 s baseline — chip rendering should add negligible cost), ≥3 frame-level spot
  checks at speaker changes, avatar-path status for the demo episode (both NULL, so name-only
  chip path exercised in the render; avatar path exercised in vitest), and the visual
  quality signal (does the chip switch cleanly on a speaker change, or does it look laggy?).
- `CHANGELOG.md` — one `[Unreleased]` bullet, no user-visible behaviour change on the app
  itself yet (still opt-in via spike runner).
- `.viepilot/phases/19-remotion/PHASE-STATE.md` — flip 19.4 row to done, append an evidence
  log entry with the wall time, avatar-status, and the 3+ spot-check timestamps.

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `docs/implementation/`; the
19.1 spike report, the 19.3 t3 report (both immutable). `data/app.db` and `data/avatars/`
are **`mode=ro` from Coder side, always** — restated after the Task 19.2 incident.

## Design decisions (Coder, doc-first — commit these under `docs(review)` before code)

The Coder writes a design section here answering each of the following, PM approves, then
code lands in a separate commit. Same pattern as 19.1–19.3.

### D19.4-a: Chip design + on-screen position

- Where do the chips live on screen? Options: top corners, top-left row, side stripes,
  bottom-adjacent-to-caption. Pick one, justify against: (a) not covering the karaoke band
  (the primary reading target from 19.3), (b) not looking like an accidental app-chrome
  overlay, (c) visible enough that the highlight is legible at a glance.
- What does the "active" state look like? Options: background-color shift, scale-up
  (`transform: scale(1.15)`), glow/shadow, a colored border. Pick one or a subtle
  combination; keep it obvious but not distracting. Reference: Step 4's speaker-panel
  colors (`frontend/pages/step4_tts.html` / `frontend/static/js/step4_tts.js` /
  `frontend/static/css/step4_tts.css` — grep for the palette actually used there, cite the
  colors you pick).
- If the project has more than 2 speakers, do all chips stay on screen persistently, or is
  there a fade-out for non-active ones? Recommend all-persistent (viewer continuity: "these
  are the two people in this episode") for the demo's 2-speaker case; document how the
  layout scales to 3–5 speakers even if the demo won't exercise it (D19.4-c handles the
  bounded-multi-speaker case).

### D19.4-b: Avatar rendering (opportunistic)

- When `avatar_url` is present, how does the chip lay out? Recommend circular avatar image
  (48–64 px) + name label to the right, matching the pattern most video/podcast apps use.
  Justify pixel dimensions against the chosen chip position (must not compete with the
  caption band for real estate).
- When `avatar_url` is absent (the demo case for both Alex and Maya), what does the chip
  render? Recommend name-only chip; optionally an initials circle in place of the avatar,
  matching Step 4's own placeholder pattern if one exists (check
  `frontend/static/js/step4_tts.js` — if Step 4 uses initials-in-a-colored-circle for
  missing avatars, mirror that; if it just shows name, mirror that too).
- Confirm the runner **copies** (never symlinks, never absolute-paths) avatar files into
  `video-renderer/public/avatars/` with a scratch prefix so the copy is disposable and can
  be cleaned up (or is naturally gitignored — check `video-renderer/.gitignore`).

### D19.4-c: Multi-speaker layout scaling

- The demo has 2 speakers. But `speakers` is 1–6 per this project's `ScriptConfig`. Sketch
  how the chip strip lays out at 3, 4, 5, 6 speakers (horizontal? two-row grid?). One
  paragraph. Not built here — only 2-speaker is verified in this task's render — but if the
  layout would break at 3+, this task's design must at least fail cleanly (e.g. wrap
  horizontally, don't overflow the screen), not silently look wrong.

### D19.4-d: `activeSpeakerId` semantics

- Confirm the tie-breaking rule at line boundaries — recommend `startSec` inclusive,
  `endSec` exclusive (matches SRT and matches how 19.3's karaoke selects the active word).
- Confirm behaviour in gaps between lines (300 ms same-speaker / 500 ms different-speaker
  padding from Task 1.6b): return `null`, chip highlight goes back to neutral for the gap
  duration. Justify: brief gap-off states are visual honesty (matches audio silence),
  keeping the last-active chip highlighted through a gap would look laggy.

### D19.4-e: Verification frames + wall-time comparison

- Pick ≥3 timestamps to spot-check at speaker changes (in this 2-speaker episode, that
  means Alex→Maya and Maya→Alex transitions plus at least one same-speaker line to prove
  the chip stays highlighted). Record: timestamp, expected active speaker id/name, extracted
  frame filename.
- Wall time vs. 19.3's ~95 s baseline (which was ~1.55× 19.1's ~61 s, dominated by the 30
  re-synth calls). This task doesn't add network calls; chip rendering should add negligible
  per-frame cost, so wall time should stay within ~±10 % of 19.3's number. A larger increase
  is a design finding.

### D19.4-f: Re-verify 19.1/19.3 invariants aren't broken

- `app/services/video_service.py` still untouched (`git log <phase19-open>..HEAD --` check).
- Python full suite still **1178/1178** unchanged, ruff clean (this task adds no Python
  tests).
- 19.3's karaoke still renders correctly — the chip is an *addition* alongside
  `<CaptionBand>`, not a modification of it. Include one frame in the report that shows
  both the karaoke band and the speaker chip rendering simultaneously (one frame, one
  timestamp — covers both features at once).

## Design decisions — Coder answers (2026-09-28)

**Card correction:** `frontend/static/css/step4_tts.css` (cited in D19.4-a) does not exist --
Step 4's styles are inline in `frontend/pages/step4_tts.html`, and the actual per-speaker
color variables live in the shared `frontend/static/css/style.css`.

### D19.4-a: Chip design + on-screen position

- **Real palette found, not guessed:** `frontend/static/css/style.css` defines
  `--speaker-a`/`--speaker-b` custom properties, already used app-wide (`.timeline-clip`,
  and a `speakerIndex % 2 === 0 ? "speaker-a" : ""` class pattern repeated identically in
  `step2_script.js:267`, `step4_tts.js:293`, `step5_video.js:124`) -- i.e. the app already
  has an established **alternate-by-index, two-color** convention for any number of
  speakers, not a unique color per speaker. Two theme variants exist:
  light (`--speaker-a: #9a4a00`, `--speaker-b: #0757a8`) and dark
  (`--speaker-a: #f59e0b`, `--speaker-b: #58a6ff`). **Chosen: the dark-theme pair**
  (`#F59E0B` amber / `#58A6FF` blue) -- the composition's background is the fixed near-black
  `#0E0F15` (19.1's `MIDNIGHT_BACKGROUND`), and the light-theme hex values were contrast-
  calibrated for a white surface; using them against a near-black background would read
  muddy. The dark-theme pair is the app's own calibration for exactly this kind of surface.
- **Position:** top-left, horizontal row, `top: 5%, left: 5%`. Justified against the three
  criteria: (a) doesn't compete with `<CaptionBand>` (bottom 10%) -- opposite corner,
  spatially separated; (b) reads as a caption-adjacent UI element, not floating app chrome,
  because it's small and corner-anchored like a real broadcast "lower/upper third" convention
  viewers already recognize; (c) legible at a glance -- top-left is the first place Western
  -language viewers' eyes land (F-pattern reading), so the "who's talking" cue is seen before
  the caption text itself, which is the right priority order for this feature's purpose.
- **Active state:** the active speaker's chip gets its `--speaker-a`/`--speaker-b` color as a
  solid background (text switches to `#0E0F15`, the same near-black as the base background,
  for contrast against the now-bright chip) plus `transform: scale(1.08)`. Inactive chips
  stay a neutral dark surface (`rgba(255,255,255,0.08)`) with white text at reduced opacity
  (`0.6`) -- present but visually receded, not gone. Combination (color fill + subtle scale),
  not a single cue alone, so the change reads clearly even to someone glancing mid-scene.
- **Persistence:** all speaker chips stay on screen for the whole episode (not just the
  demo's 2 speakers) -- confirmed as the right call for continuity ("these are the people in
  this episode"), matching the card's own recommendation. No fade-out for inactive chips
  (fading would remove the "who else is in this scene" context the chips exist to provide).

### D19.4-b: Avatar rendering

- **Real finding, not a guess:** `frontend/static/js/step5_video.js:239-242` (Task 1.7c's own
  avatar upload UI) shows the app's actual placeholder for a missing avatar is a **plain text
  box reading "No image"** -- there is no initials-in-a-colored-circle pattern anywhere in
  this codebase to mirror. The card's speculative "if Step 4 uses initials-in-a-circle, mirror
  that" doesn't apply; the real, simpler precedent is: no avatar → no image element at all,
  just text. This directly informs the chip's absent-avatar design below.
- **When `avatar_url` present:** circular avatar, `56px` diameter (`border-radius: 50%`,
  `object-fit: cover`) to the left of the name label. 56px chosen against the chosen position
  (top-left, ~5% margins on a 1280×720 canvas) -- large enough to read a face at video
  resolution, small enough that even 6 stacked/wrapped chips (D19.4-c) stay well clear of the
  caption band's bottom 10%.
- **When `avatar_url` absent (the demo case, both speakers):** **name-only chip, no circle, no
  initials** -- matching the real app's own "just text, no fake-avatar substitute" precedent
  found above, not inventing a fancier pattern the app doesn't actually use anywhere.
- **Avatar file handling confirmed:** the runner **copies** (never symlinks, never passes an
  absolute path) any non-null `avatar_image_path` file into
  `video-renderer/public/avatars/<speaker_id><ext>` before render, exactly the same pattern
  already used for the mixed audio file (D19.1-d addendum) -- copy-into-`public/`-then-
  `staticFile()`, because Remotion has no other way to read a real filesystem asset.
  `video-renderer/.gitignore`'s existing `public/` blanket-ignore already covers this new
  subfolder -- confirmed by reading the `.gitignore` (single `public/` line, not scoped to
  `spike-audio/`), no additional gitignore edit needed.

### D19.4-c: Multi-speaker layout scaling

One paragraph, as asked: the chip row uses CSS flexbox (`display: flex, flexWrap: wrap, gap:
8px`) inside a fixed-width container anchored top-left. At 2 speakers (the demo) it's one
short row. At 3–4, still one row (each chip is compact -- name-only chips are ~120-160px
wide at 32px font, avatar chips ~180-220px; four avatar chips fit within a 1280px-wide canvas
with margin to spare). At 5–6, `flexWrap: wrap` lets the row become two rows rather than
overflowing off-screen or shrinking chips illegibly -- this is the "fail cleanly, don't
silently look wrong" requirement: wrapping is a real, visible, correct degradation, not a
silent bug. Colors continue the app's existing alternate-by-index convention (`speaker_index
% 2`) rather than needing N unique colors -- consistent with the real app's own 2-color
convention at any speaker count. Not built/rendered in this task beyond the demo's 2 speakers
(per the card), but the layout mechanism (flexbox wrap, index-parity coloring) requires no
different code path at higher counts -- it degrades by CSS alone, not a conditional.

### D19.4-d: `activeSpeakerId` semantics

- **Tie rule: `startSec` inclusive, `endSec` exclusive** -- identical convention to 19.3's
  `activeTokenIndex` (`karaoke.ts`) and to the existing SRT export format, so a viewer never
  sees two different Phase-19 systems disagree about which instant a boundary belongs to.
- **Gaps return `null`:** between-line silence (300ms/500ms padding, Task 1.6b), before line
  0, and after the last line all produce `null` -- confirmed as correct, not a compromise:
  the padding exists precisely because no one is speaking during it, so "no speaker
  highlighted" is the honest visual state, matching the actual audio. Keeping the previous
  speaker highlighted through a silence gap would visually claim someone is still talking
  when the audio says otherwise -- worse than a brief neutral flicker.

### D19.4-e: Verification frames + wall-time comparison

Frames chosen after the render (same run-coherence discipline as 19.3 -- timestamps come from
this task's own render, not guessed in advance): at least one Alex→Maya transition, one
Maya→Alex transition, and one frame mid-line (proving the chip *stays* highlighted for a
whole line, not just at its boundary instant) -- plus one frame that captures both the
karaoke band and the speaker chip simultaneously (D19.4-f). Wall time compared to 19.3's
~95s/~97s: expected to land within ~±10%, since this task adds no network calls and chip
rendering is a handful of `<div>`s, not a per-frame-expensive operation.

### D19.4-f: Re-verify 19.1/19.3 invariants

- `git log fe06405..HEAD -- app/services/video_service.py` checked at implementation time,
  reported in the handover -- expect empty (untouched).
- Python full suite 1178/1178 unchanged (no Python files touched by this task), `ruff check
  .` clean.
- 19.3's karaoke band is additive-only: `<SpeakerChips>` is a new sibling element inside
  `<AbsoluteFill>`, not a change to `<CaptionBand>`'s own JSX or styles. One spot-check frame
  shows both features rendering together in the same frame as direct proof.

## Verification

- Real re-render of `b330d37f...` succeeds end-to-end.
- ≥3 frame-level spot checks confirm the correct speaker chip is highlighted at each chosen
  timestamp.
- vitest `speakers.test.ts` passes; revert-and-confirm-failure done on it.
- `tsc --noEmit` clean on `video-renderer/src/`; Python full suite 1178/1178; ruff clean.
- `git log fe06405..HEAD -- app/services/video_service.py` still empty.
- Report on disk with wall-time comparison to 19.3.

## Evidence (what the Coder's handover message includes)

- Two commits' shas (design + implementation).
- Full-suite line + ruff line + tsc line + vitest line.
- Re-render wall time (vs. 19.3's ~95 s).
- ≥3 frame filenames + expected-vs-observed speaker names.
- Chip position/style decisions cited from Step 4's real palette.
- Avatar-path status for the demo (both `NULL` per the preflight above, so name-only chip
  exercised in the render; avatar path exercised in vitest — record which vitest cases
  cover it).
- Visual quality signal: does the chip switch look crisp at 30 fps, or does it look laggy?
- Carry-over conditions (still no 8-min episode; Chrome ~270 MB still 19.7's problem).

## Definition of done

- Two commits, design **before** implementation.
- Composition renders the active-speaker chip; falls back to name-only when avatar absent.
- Report on disk (`docs/operations/phase19-t4-speaker.md`).
- Full suite + ruff + tsc + vitest all green.
- `app/services/video_service.py` genuinely untouched.
- Handover message per Evidence checklist.
