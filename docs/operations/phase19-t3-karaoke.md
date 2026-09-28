# Phase 19 Task 19.3 — Word-level karaoke captions

- **Task:** 19.3 (Coder). Design record: `.viepilot/phases/19-remotion/tasks/task-19.3.md`
  (D19.3-a..f, PM-approved 2026-09-28).
- **Run date:** 2026-09-28. **Code HEAD at task start:** Task 19.2 accepted (`20a1d32`, owner
  D34).
- **Scope:** composition change only. `app/services/video_service.py` untouched (confirmed
  below, §5). No `VideoService` wire-up (that's Task 19.7).
- **Methodology note (PM caveat, recorded verbatim as asked):** Edge TTS `WordBoundary`
  values are not guaranteed byte-identical across separate runs of the same input line --
  small millisecond-scale drift is normal. The spot-check timestamps and expected words below
  were taken from the exact same run whose frames were extracted (the render's input props
  are dumped to `<output>.props.json` alongside the video for exactly this reason), not
  compared against a fixed prior baseline. This proves "the correct word is highlighted at
  the correct instant in this rendered MP4," not "timings match a golden file."

## 1. Real data-availability finding (checked before writing any code)

The only real episode with completed audio (`b330d37f-a212-4cf7-a779-7a109098bd6c`, used by
19.1/19.2) has `audio_jobs.word_timestamps_json = NULL` and **zero** `.words.json` sidecar
files anywhere under `data/tts_cache/b330d37f.../` -- confirmed by a read-only query and a
directory listing. It predates Task 19.2's capture code (synthesized/mixed 2026-09-15) and
has not been re-mixed since (re-mixing would need a real-DB write, forbidden after the Task
19.2 incident).

**Resolution:** `scripts/run_remotion_spike.py` now re-synthesizes each line fresh via a real
`tts_service._synthesize_edge_tts()` call (same text, same real speaker config) when
`audio_job["word_timestamps"]` is empty, entirely **in memory** -- the freshly synthesized
audio bytes are discarded, only the real per-word timing is kept and aggregated onto the
line's existing mix-timeline offset (same formula as
`audio_service._aggregate_word_boundaries`). **Nothing is written to `data/app.db` or to
`data/tts_cache/`** -- the real project's cached files were never touched. This cost **30
real Edge TTS network calls** for this episode's 30 lines -- a one-time demo-run cost, not a
production concern (19.7's real wiring will call this exactly once per line at synthesis
time, same as it already does today, just capturing what Edge TTS already returns).

## 2. `@remotion/captions` -- version and a real finding about its API surface

- **Resolved version:** `4.0.529` (exact lockstep with `remotion`/`@remotion/cli`, already
  installed at that version).
- **Real finding:** listing every file in the installed package
  (`node_modules/@remotion/captions/dist/`) shows exactly 5 `.d.ts`/`.js` pairs
  (`caption`, `create-tiktok-style-captions`, `ensure-max-characters-per-line`, `parse-srt`,
  `serialize-srt`) plus an `index` -- **zero `.tsx`/`.jsx` files, zero runtime dependencies,
  no React import anywhere.** This is a pure data/grouping library; it renders nothing. The
  task card's framing ("(i) accept the helper's default visual" vs. "(ii) build custom") was
  based on a misunderstanding inherited from the plan's own wording -- there is no default
  visual to accept in the first place. Rendering is always custom; `createTikTokStyleCaptions`
  is used for what it's actually for: converting a flat per-word list (in
  `Caption`/milliseconds shape) into `TikTokPage`/`TikTokToken` grouping.
- **Used correctly, not bypassed:** called once **per line** (`src/karaoke.ts`,
  `buildKaraokeTokens`), with `combineTokensWithinMilliseconds` set to that line's own
  duration + 1ms -- guaranteeing exactly one `TikTokPage` per line regardless of internal
  word-gap sizes, so the helper's own auto-pagination (designed for a continuous
  whole-episode word stream) can never split or merge across the app's existing per-line SRT
  boundaries.

## 3. Visual

Identical to the 19.1 spike's plain band -- same `fontFamily`/`fontSize: 32`/`fontWeight:
700`/`textShadow`/bottom-10%-centered position (`CAPTION_TEXT_STYLE` in `Episode.tsx`,
byte-identical object to the pre-19.3 style). The only change: the currently active word's
`color` becomes `#FFD54A` (warm yellow) instead of `#FFFFFF`. No font/size/position
regression, confirmed by construction (one conditional style override, nothing else differs).

**Visual quality signal (PM ask, not a gate item):** stepping through the rendered MP4 frame
by frame at the word boundaries (30fps, ~33ms/frame -- real words in this episode span
150–600ms, i.e. 5–18 frames each), the highlight flip lands cleanly on a whole word with no
visible flicker or lag; it reads as crisp, not stuttery.

## 4. Fallback path (D19.3-c)

- **Per-line, at the rendering-code level:** `src/Episode.tsx`'s `CaptionBand` component --
  `if (tokens.length === 0)` (where `tokens = buildKaraokeTokens(line)`) renders the exact,
  unmodified plain-span JSX (`{line.speaker}: {line.text}`, same `CAPTION_TEXT_STYLE`) that
  existed before this task. The karaoke branch is a new `else`, not a replacement of the old
  code.
- **Episode-level:** not a separate code path. The runner builds every line's `words` field
  from the same `audio_jobs.word_timestamps_json`-shaped data; a `NULL` episode (or a project
  never re-mixed since 19.2) naturally produces `words: []` for every line, which hits the
  identical per-line fallback branch above.
- **No fallback screenshot** (PM-approved as sufficient): since this task's re-synthesis
  gives every one of this episode's 30 lines real captured words (0 empty), there is no
  naturally-occurring empty-words line to screenshot here. The fallback branch is a pure
  conditional on data the 19.1 spike already proved renders correctly (that spike's own real
  MP4 output *is* the plain-line-level render) -- 19.3 doesn't change that rendering code at
  all, only conditionally invokes it. `src/karaoke.test.ts`'s
  `"returns an empty array for a line with no captured words"` test exercises this path
  directly and automatically, which is a stronger regression guard than a one-time manual
  screenshot: it fails on every future `npm run test` if the conditional ever breaks, with no
  human needed to notice.

## 5. Re-verification of Task 19.1 invariants (D19.3-f)

- `git log fe06405..HEAD -- app/services/video_service.py` (phase-19-open commit through
  this task's HEAD): **empty.** Confirms the file is genuinely untouched.
- **ffmpeg-fallback comparison, with a real (benign) finding:** re-rendered the same episode
  through `VideoService.generate_video` (fed with data fetched read-only, output to a scratch
  `DATA_DIR`, never touching the real `data/video/b330d37f.../` files) and compared hashes
  against the existing real file. **Hashes did not match** -- investigated rather than
  ignored: `ffprobe` shows the fresh render's duration is `176.04s` (matching the audio's
  measured `176.02s` exactly, ±rounding) while the **existing real file's duration is
  `178.56s`** -- a ~2.5s overshoot. `git log` on that exact file's commit history shows this
  matches **Task 14.10's `-shortest` overshoot bug fix** (`ec26846`, committed
  **2026-09-22**), which replaced `-shortest` with a hard `-t {duration}` cutoff specifically
  because `-shortest` overshot by ~2.5s at real durations (documented in
  `video_service.py`'s own code comment). The real file on disk was rendered **2026-09-15**
  -- a full week **before** that fix shipped. The hash mismatch is fully explained: the
  on-disk file is simply stale relative to an unrelated, already-completed bug fix from
  Task 14.10, not a regression from anything in Phase 19. The fresh render's duration
  matching the audio exactly is confirmation that today's (untouched) `video_service.py` code
  works correctly.
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.

## 6. Verification frames (real data, from one coherent run)

Episode: `b330d37f-a212-4cf7-a779-7a109098bd6c` (30 lines, 176.02s audio -- same episode as
19.1/19.2). Evidence for this exact run lives under `data/tmp/phase19_spike/` (gitignored
scratch, same convention as the 19.1 spike): the rendered
`b330d37f-a212-4cf7-a779-7a109098bd6c.mp4`, the input props actually used
(`b330d37f-a212-4cf7-a779-7a109098bd6c.props.json`), and the 3 extracted frames below.

| # | Timestamp | Line | Expected active word | Frame file | Observed |
|---|---|---|---|---|---|
| 1 | t=1.75s | Line 0 (multi-word), "Hey Maya, are you an early **bird** or a night owl?" | `bird` | `t3_frame1_bird.png` | `bird` highlighted yellow, all else white -- match |
| 2 | t=29.0s | Line 5 (16 words, wraps to 2 lines), "...I **usually** scroll through social media..." | `usually` | `t3_frame2_usually.png` | `usually` highlighted yellow -- match |
| 3 | t=174.9s | Line 29 (last line), "I will! Wish me **luck**!" | `luck` (last word) | `t3_frame3_luck.png` | `luck` highlighted yellow -- match |

All 3/3 correct. Line 5's karaoke band wraps across two lines with no layout regression --
the base style is unchanged, only the active word's color differs, regardless of wrap.

## 7. Render measurement

Two full re-renders of the same episode (each including the 30 real Edge TTS re-synthesis
calls plus the actual Remotion render):

| Run | Wall time |
|---|---|
| 1 | 96.810 s |
| 2 | 94.704 s |

Compared to the 19.1 spike's ~61 s baseline (plain line-level, no re-synthesis, no
`@remotion/captions`): **~1.55–1.59x**, inside the card's ≤~2x threshold. The added time is
dominated by the 30 real network round-trips to Edge TTS (this task's re-synthesis
workaround for missing captured data, not the karaoke rendering itself) -- the actual
`createTikTokStyleCaptions` + per-word-highlight rendering adds negligible per-frame cost, as
expected (text layout, not a pixel operation).

## 8. Test story (D19.3-e)

Chosen: **(i) add Vitest** (`vitest@5.0.2`). Real measured cost:

| Stage | `node_modules` size |
|---|---|
| Before Task 19.3 (19.1/19.2 baseline) | 688 MB |
| After `@remotion/captions` install | 688 MB (no change -- already present transitively via `@remotion/cli`'s own render pipeline; installing it as a direct dependency only promoted/deduped an existing nested copy) |
| After `vitest` install | 725 MB (**+37 MB**: `vitest` 2.9 MB, `vite` 2.4 MB, `@vitest/*` 0.3 MB, `@esbuild/*` (a new platform-specific binary pulled in by `vite`'s own bundler, separate from Remotion's own `esbuild` copy) 12 MB, remaining ~19 MB spread across smaller transitive packages: `tinypool`, `tinyrainbow`, `expect`, `chai`, `loupe`, `pathe`, `magic-string`, `postcss`, etc.) |
| Final (after lockfile resolution) | 727 MB |

`vitest` is a **devDependency only** -- doesn't affect 19.1's packaged-app estimate (already
assumed devDependencies are excluded from shipping). One real test file
(`src/karaoke.test.ts`, 6 tests) exercises `buildKaraokeTokens` (correct per-word ms
conversion, single-page grouping despite internal gaps, empty-array fallback) and
`activeTokenIndex` (correct token at a given time, `-1` in gaps and outside the line's word
span). Revert-and-confirm-failure done: reverted `buildKaraokeTokens` to always return `[]`
-- 3/6 tests failed with real assertion mismatches (not crashes); restored, 6/6 green again.

## 9. Full checks

- `tsc --noEmit` on `video-renderer/src/`: **clean.**
- `npm run test` (vitest): **6/6 passed.**
- Python full suite: **1178/1178 passed** (unchanged from Task 19.2 baseline -- this task
  adds no Python tests). `ruff check .`: **clean.**
- `tests/test_video_studio_browser.py`: **10/10 passed**, unchanged.

## 10. Carry-over conditions (acknowledged, not acted on)

1. **8-min B1 episode:** still does not exist in `data/app.db`. This task rendered the same
   `b330d37f...` (2:56 actual) as 19.1/19.2 measured against -- not invented.
2. **Chrome ~270 MB hard floor:** still 19.7's problem. No `video-renderer/` packaging change
   in this task.
