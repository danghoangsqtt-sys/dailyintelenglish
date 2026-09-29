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
