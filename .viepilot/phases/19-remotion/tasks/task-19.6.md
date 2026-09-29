# Task 19.6 — Intro + outro + chapter/progress bar + Remotion thumbnail still

- **Status:** not started (doc-first card, awaiting Coder pickup after 19.5)
- **Owner:** Coder
- **Priority:** P0 (Phase 19's biggest composition task, 4 sub-features; last user-visible
  visual before 19.7 wire-up)
- **Dependency:** Task 19.5 accepted (`4548653`)
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.6"; Phase 19
  invariants 36-40; existing `app/services/youtube_service.py::real_chapters_from_timestamps`
  (Task 1.9b) that already groups `timestamps_json` into chapter buckets
- **Owner-signed content decisions (2026-09-29):**
  - Outro text: `"Thanks for watching · Subscribe for more · See you next episode!"`
  - Still frame timestamp: 50% of episode duration (middle)

## Goal

Add 4 composition features that turn the current bare karaoke+chip+vocab composition into
an episode that actually looks like a shipped YouTube video:

1. **Intro (~2-3 s):** project title + speaker names + CEFR/topic tags, fades in over a
   subdued background.
2. **Outro (~5 s):** the owner-approved CTA text above, fades in after the last spoken line.
3. **Chapter/progress bar overlay:** thin horizontal bar showing playback position + chapter
   dividers, drawn from `youtube_service.real_chapters_from_timestamps()`'s existing output.
4. **Remotion thumbnail still:** single PNG frame extracted at 50% of episode duration
   (owner decision), feeds ENH-012/Phase 20 AI thumbnails.

**Big design choice up front (D19.6-a below):** whether intro/outro extend the video's
total length (Option B, natural) or overlay onto the first/last few seconds of audio
(Option A, simpler). Recommend Option B — this task should decide once, not defer.

## Allowed files

- **Modify** `video-renderer/src/types.ts` — extend the input-props schema with `title:
  string`, `topic: string`, `cefrLevel: string`, `chapters: Array<{title: string;
  startSec: number}>`, `introSec: number`, `outroSec: number`, `outroText: string`. All
  additions optional so old runner invocations don't break; sensible defaults in the schema
  (introSec 2.5, outroSec 5.0, outroText the exact owner-approved string).
- **Modify** `video-renderer/src/Root.tsx` — the composition's `calculateMetadata` needs to
  extend `durationInFrames` by `(introSec + outroSec) * fps` so the video total covers all
  three sections.
- **Modify** `video-renderer/src/Episode.tsx`:
  - New `<Intro>` component rendered inside a `<Sequence from={0}
    durationInFrames={introFrames}>`.
  - Existing `<CaptionBand>`, `<SpeakerChips>`, `<VocabCard>` wrapped in a `<Sequence
    from={introFrames}>` so they play during the audio window.
  - New `<Outro>` inside `<Sequence from={introFrames + audioFrames}
    durationInFrames={outroFrames}>`.
  - New `<ChapterProgressBar>` overlay throughout the audio window (not intro/outro),
    positioned to not collide with the caption band (bottom) or speaker chip (top-left) or
    vocab card (top-right). Recommend thin bar at very-top or very-bottom edge.
  - Audio component `<Audio src={staticFile(audioUrl)} startFrom={0}>` inside the audio
    window's `<Sequence>` so audio plays during the middle section only, silent during
    intro/outro.
- **New** `video-renderer/src/chapters.ts` — pure helper `computeProgressForFrame(
  currentFrame, fps, audioDurationSec, chapters) -> {overallPct, currentChapter, ...}`.
  Unit-testable.
- **New** `video-renderer/src/chapters.test.ts` — vitest for `computeProgressForFrame`.
- **New** `video-renderer/src/StillFrame.tsx` — a separate Remotion composition that
  renders exactly the single frame at 50% audio duration (audio window offset already
  accounted for). Uses the same `<CaptionBand>`, `<SpeakerChips>`, `<VocabCard>` shared
  with Episode so the still visually matches the video at that timestamp.
- **Modify** `video-renderer/src/Root.tsx` — register `StillFrame` as a second composition
  (`registerRoot` supports multiple).
- **Modify** `scripts/run_remotion_spike.py`:
  - Compute `chapters` using existing Python `youtube_service.real_chapters_from_timestamps`
    (import + call, read-only) — do not re-implement the grouping logic in Python or JS.
  - Pass `title`, `topic`, `cefrLevel`, `chapters`, `introSec`, `outroSec`, `outroText` in
    the props JSON.
  - After the main video render, invoke `npx remotion still` (or Remotion's equivalent CLI)
    on the `StillFrame` composition, saving to `data/tmp/phase19_spike/<project_id>.png`.
- **New** `docs/operations/phase19-t6-intro-outro.md` — task-scoped report (do NOT amend
  the spike report, t3-karaoke, t4-speaker, t5-vocab reports — all immutable).
- `CHANGELOG.md` — one `[Unreleased]` bullet.
- `.viepilot/phases/19-remotion/PHASE-STATE.md` — flip 19.6 to done, evidence log entry.

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `docs/implementation/`;
prior reports (all immutable). `data/app.db` is `mode=ro` from Coder side, always
(standing constraint post-19.2 incident).

## Design decisions (Coder, doc-first — commit under `docs(review)` before code)

### D19.6-a: Intro/outro time-slice — extend vs overlay

- **Recommend Option B (extend):** total video = intro + audio + outro. Audio silent
  during intro/outro; the composition's `<Sequence>` wraps drive when each section plays.
  Video looks like real TV: title slide → episode → CTA. Requires
  `calculateMetadata` to compute total frames = `(introSec + audioSec + outroSec) * fps`.
- Option A (overlay): total video = audio duration; intro/outro fade in over the first
  3s and last 5s of spoken content. Simpler but competes for viewer attention.
- Reject any option that modifies the source audio itself (padding, etc.) — audio is
  AudioService's product, not this composition's territory.

### D19.6-b: Intro visual

- Content: `{projectTitle}` (large), `{speaker1Name} & {speaker2Name}` (medium),
  `[{cefrLevel}] {topic}` (small). Fade in over ~0.5s, hold, fade out into first line.
- Background: solid `#0E0F15` (same as spike composition), plus optional subtle color
  band drawn from the speaker palette (`#F59E0B` amber / `#58A6FF` blue from 19.4).
- If a project has 3+ speakers, comma-separate; if 1 speaker (solo), show just their name.
- Font: same family as caption band (already in `CAPTION_TEXT_STYLE`).

### D19.6-c: Outro visual

- Content: fixed `"Thanks for watching · Subscribe for more · See you next episode!"`
  (owner-approved, exact string). Displayed centered, medium size.
- Fade in from black, hold ~4s, fade out ~1s.
- Same background as intro.
- If a future project needs a different outro string, `outroText` prop accepts an
  override — do NOT hardcode this string in `Episode.tsx`; keep it in props with the
  owner-approved string as the schema default.

### D19.6-d: Chapter/progress bar

- Position: recommend top edge (opposite the bottom-anchored caption band), thin (~4-6px
  tall), full-width. Justify against collision with speaker chips (top-left) — the bar
  spans full width but stays above the chips vertically, not overlapping.
- Visual: base bar in `rgba(255,255,255,0.15)`, played portion in
  `rgba(255,255,255,0.85)`, chapter dividers as small tick marks at each chapter's
  `startSec`. Optional (Coder decides): small chapter title text hovering above the tick
  when the current chapter is within ~1s of a boundary.
- Compute via `computeProgressForFrame` — pure function, no state.
- Shown during audio window only, hidden during intro/outro (chapters are about audio
  content, meaningless during title/CTA slides).

### D19.6-e: Chapters data source

- Import `youtube_service.real_chapters_from_timestamps` in `run_remotion_spike.py`
  (read-only — same pattern as reading `learning_contents` in 19.5). Pass the result as
  `chapters` prop. **Do NOT re-implement the grouping in JS** — one source of truth for
  chapter computation.
- If the project has no `audio_jobs.timestamps_json` (shouldn't happen for a completed
  project, but handle it): `chapters = []`, chapter bar renders as a plain progress bar
  with no tick marks. Not an error.

### D19.6-f: Remotion still frame

- Add `StillFrame` composition to `Root.tsx`. Same input props as `Episode` (so the still
  can reference the same speaker chips + vocab card + karaoke state at that instant).
- Render at 50% of audio duration (owner decision), computed inside `StillFrame`'s own
  `calculateMetadata` from the passed `audioSec`.
- Runner invokes `npx remotion still` after the main video render, saving PNG to
  `data/tmp/phase19_spike/<project_id>.png`. Same folder convention as the main MP4.
- Wall-time cost: negligible (single frame render).

### D19.6-g: Wall-time budget

- Expect the render wall time to increase by roughly the intro (~2.5s) + outro (~5s)
  worth of frames (25% of the audio window). At 61s baseline (from 19.5) with audio 176s,
  intro/outro add ~2.5 + 5 = 7.5s of extra render at same fps — roughly +8-10% wall time.
- Report both before/after wall-time numbers to prove nothing regressed unexpectedly.
- Still render adds ~1-2s more.

### D19.6-h: Re-verify 19.1/19.3/19.4/19.5 invariants

- `app/services/video_service.py` still untouched (`git log <phase19-open>..HEAD --` empty).
- Python full suite still **1189/1189** (this task adds no Python tests; runner change is
  code, not test — verify existing tests still pass).
- vitest 21/21 (from 19.5) still green, plus new chapter tests.
- One combined frame proves karaoke + chip + vocab card + progress bar all render
  simultaneously during audio window; one intro frame; one outro frame; one still PNG.

## Design decisions — Coder answers (2026-09-29)

Investigated real code/APIs before answering (no code written yet). All 8 of the card's own
D19.6-a..h points above are **confirmed as the plan**, with two real corrections/findings
below that change *how* two of them get implemented.

### Confirmed as-is

- **D19.6-a (extend, Option B):** confirmed by reading the installed Remotion source
  (`video-renderer/node_modules/remotion/dist/cjs/Sequence.js:379`,
  `const content = frameInParent - from < -boundaryTolerance`) — a `<Sequence from={N}>`
  genuinely remaps `useCurrentFrame()` for its children to `frameInParent - from`, i.e. frame
  0 *inside* the Sequence is already the Sequence's own start. **Practical consequence:**
  wrapping the existing `<CaptionBand>`/`<SpeakerChips>`/`<VocabCard>` tree in
  `<Sequence from={introFrames}>` requires zero changes to their internal
  `currentTimeSec = frame / fps` math — it already lines up with `line.startSec`/`endSec`
  (both audio-relative) with no manual offset subtraction anywhere in `Episode.tsx`. This was
  the one real risk in Option B (that every existing time-based component would need an
  `introSec` correction term threaded through); it isn't needed. `<Audio startFrom={0}>` goes
  inside the same audio-window Sequence.
- **D19.6-b, D19.6-c (intro/outro visuals), D19.6-d (progress bar position/collision):**
  confirmed against the real `SPEAKER_COLORS`/`CAPTION_TEXT_STYLE` constants already in
  `Episode.tsx` and 19.4's top-left chip placement — no changes to the card's plan.
- **D19.6-g (wall-time budget):** no objection; will report real before/after numbers same as
  every prior task, investigated (not shrugged off) if the delta is outside the card's ~8-15%
  expectation, per the standing discipline since 19.4.

### D19.6-e — real finding: `real_chapters_from_timestamps` returns text, not structured data

Read `app/services/youtube_service.py:85-105` directly. Its real signature and return
contract:
```python
def real_chapters_from_timestamps(timestamps: list[dict]) -> str:
    """... Returns: Plain-text "MM:SS Label" lines, or "" if there are no timestamps."""
```
It returns a **single newline-joined string** (`"00:00 Introduction\n00:20 Label\n..."`), not
an `Array<{title, startSec}>`. Called it for real (read-only) against the pinned episode's
actual `timestamps_json` (`b330d37f...`, 30 lines) and got a real 8-line block:
```
00:00 Introduction
00:20 Well, the first thing I do…
00:45 I drink a big glass of…
01:09 Just ten minutes of fresh air…
01:33 If you put your alarm clock…
01:56 If you don't eat anything, you…
02:20 Exactly. Small changes can help you…
02:47 Anytime! Let me know if you…
```
The card's proposed `types.ts` schema (`chapters: Array<{title: string; startSec: number}>`)
needs structured data, so `run_remotion_spike.py` needs one small **format-conversion** step
between this string and the props JSON — not a re-implementation of the grouping heuristic.
Plan: a `_parse_chapters_text(text: str) -> list[dict]` helper in the runner that splits on
`"\n"`, and per non-empty line splits on the first space into `"MM:SS"` and the rest as
`title`, converting `"MM:SS"` to `startSec = minutes * 60 + seconds`. This only re-parses the
function's own output format back into structured fields it was given in the first place
(`cue["start_sec"]`, rounded, and `cue["text"]`, truncated via `_chapter_label`) — it does not
decide which lines become chapters or how labels are built (`YOUTUBE_CHAPTER_MIN_LINES`,
`_chapter_label`'s 6-word truncation) — that stays 100% inside `real_chapters_from_timestamps`
per D19.6-e's single-source-of-truth rule. Flagging this now because the card's "Pass the
result as `chapters` prop" line reads as if the function's return value were already
structured; it isn't, so this parsing step is a necessary (small) addition to the runner's
"Allowed files" scope, not a scope creep.

### D19.6-f — real finding: `remotion still`'s frame selection is a CLI flag, not `calculateMetadata`

Ran `npx remotion still --help` for real. Confirmed usage:
`remotion still <serve-url|entry-point>? [<composition-id>] [<output-location>]`, and,
critically, a real `--frame <value>` override flag exists alongside `--props`. This means the
50%-of-audio-duration frame selection (owner decision) is more naturally a **runner-side
computation passed via `--frame`**, not something `StillFrame`'s own `calculateMetadata` can
express — `calculateMetadata` controls the composition's `durationInFrames`/`fps`/dimensions,
not which single frame `remotion still` captures. Corrected plan (small refinement to the
card's D19.6-f wording, same "flag card inaccuracies, don't silently reinterpret" discipline
as every prior task):
- `StillFrame.tsx`'s `calculateMetadata` computes `durationInFrames` the same way `Episode`'s
  audio-window section does (from `audioSec * fps`) so the composition is valid across the
  full audio length — it does **not** need to encode "50%" anywhere.
- The runner computes `midpointFrame = round(0.5 * audio_job["duration_seconds"] * RENDER_FPS)`
  and invokes `npx remotion still src/index.ts StillFrame <output.png> --props=<file>
  --frame=<midpointFrame>` — mirroring the existing `_run_render` invocation shape exactly
  (`shutil.which("npx.cmd")`, temp props file, `cwd=VIDEO_RENDERER_DIR`).
- `StillFrame` reuses `<CaptionBand>`/`<SpeakerChips>`/`<VocabCard>` directly (no Sequence
  wrapping needed — it's a single flat composition covering just the audio window, no
  intro/outro slices to time-slice between).

### D19.6-h — re-verify plan

Will re-run the exact same invariant checks as every prior task before handover: `git log
fe06405..HEAD -- app/services/video_service.py` empty, full Python suite (currently
1189/1189) unchanged, `tests/test_video_studio_browser.py` unchanged, vitest 21/21 (19.5
baseline) plus new `chapters.test.ts` cases, `tsc --noEmit` clean, `ruff check .` clean.

## Verification

- Real re-render of `b330d37f...` (pinned per 19.5) succeeds end-to-end.
- ≥4 frame spot checks: intro title visible, outro CTA visible at correct timestamp,
  chapter bar progresses across the audio, combined-features frame confirms no regression.
- Still PNG exists at `data/tmp/phase19_spike/b330d37f-a212-4cf7-a779-7a109098bd6c.png`.
- vitest passes; revert-and-confirm-failure on `computeProgressForFrame`.
- `tsc --noEmit` clean; Python full suite 1189/1189; ruff clean.
- `git log fe06405..HEAD -- app/services/video_service.py` still empty.
- Report on disk with wall-time before/after + real screenshots.

## Evidence (Coder handover)

- Two shas (design + implementation).
- Full-suite + ruff + tsc + vitest lines.
- Re-render wall time vs. 19.5's 60-61s baseline (accept +8-15% for the extra frames).
- 4 frame filenames + expected-vs-observed content.
- Still PNG filename + dimensions.
- Chapters count computed for demo episode + which service function was called.
- Any wall-time surprise investigated, not shrugged off (same discipline as 19.4/19.5).
- Carry-overs still open (8-min episode; Chrome ~270MB stays 19.7's problem).

## Definition of done

- Two commits, design before implementation.
- Composition now includes intro, outro, chapter bar, and produces a still PNG.
- Report on disk.
- All checks green. `app/services/video_service.py` genuinely untouched.
- Handover per Evidence checklist.
