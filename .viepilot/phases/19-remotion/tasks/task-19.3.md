# Task 19.3 — Word-level karaoke captions composition

- **Status:** not started (doc-first card, awaiting Coder pickup)
- **Owner:** Coder
- **Priority:** P0 (first user-visible payoff of the Remotion path; consumes Task 19.2)
- **Dependency:** Task 19.2 accepted (`20a1d32`, D34 2026-09-28); real per-word timings now
  captured and persisted (`audio_jobs.word_timestamps_json`, sidecar
  `<line_id>.words.json`)
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.3" (uses
  `@remotion/captions` + `createTikTokStyleCaptions`); Phase 19 invariants 36–40
  (renderer opt-in, local-only, no secret in workspace, licence, thresholds); ENH-013
  scope item 1

## Goal

Extend the 19.1 spike composition (plain line-level subtitle band) into a **word-level
karaoke band** — the active word inside the currently-playing line is highlighted in sync
with the audio. Lines whose captured word list is empty (older projects, omnivoice lines,
Edge TTS returning zero boundaries) fall back to today's plain line-level rendering, exactly
as in the 19.1 spike. Composition change only; no `VideoService` wire-up (that is 19.7).

The task's user-visible payoff: play the rendered MP4 and see the highlighted word tracking
the voice. Any other visual polish (font, colour, band position beyond what libass already
uses) is not this task — it's a future subtitle-style-picker phase.

## Allowed files

- **Modify** `video-renderer/package.json` + `package-lock.json` — add `@remotion/captions`
  as a dependency, pinned to a version compatible with the already-installed
  `remotion@4.0.529` (semver-compatible with the rest of the workspace; do not upgrade the
  whole `remotion/*` line here).
- **Modify** `video-renderer/src/types.ts` — extend the input-props schema (zod) so each
  line carries an optional `words: Array<{text: string; startSec: number; endSec: number}>`
  in mix-absolute time (matching `audio_jobs.word_timestamps_json`'s shape as designed in
  Task 19.2 D19.2-d). Empty array or absent = fall back to line-level rendering. Do **not**
  change any existing field's name or type.
- **Modify** `video-renderer/src/Episode.tsx` — render the active line's caption via
  `@remotion/captions`'s `createTikTokStyleCaptions` (or the closest primitive that gives
  per-word highlight timing), falling back to the current plain `${speaker}: ${text}` render
  when `line.words` is missing or empty. Font/size/colour/band-position must **not regress**
  from the 19.1 spike look — the karaoke is a highlight *on top of* the same visual style,
  not a redesign.
- **Modify** `video-renderer/src/Root.tsx` — only if the composition's `calculateMetadata`
  or `defaultProps` genuinely needs an update for the new schema; otherwise leave it alone.
- **Modify** `scripts/run_remotion_spike.py` — read `audio_jobs.word_timestamps_json` from
  the same read-only-mode DB connection the spike already uses, aggregate into the
  per-line `words` field the new props schema expects. Continue selecting the same episode
  the 19.1 spike used (whichever B1 episode has completed audio) — this task must be
  re-runnable against `b330d37f...` and produce a rendered MP4 with visible per-word
  highlighting. **The DB access remains `mode=ro`** — the incident from Task 19.2
  (see TRACKER.md Known Issues, 2026-09-28) makes this reminder explicit here.
- **New** `docs/operations/phase19-t3-karaoke.md` — a task-scoped report (do not amend
  the 19.1 spike report `phase19-spike-remotion.md`, which stands as immutable historical
  record of the spike). This one covers: measured wall time for the re-render (compare
  against 19.1's ~61 s baseline — any large regression is a design finding), a frame-level
  spot check at ≥3 timestamps confirming the correct word is highlighted at each, and a
  disclosure that omnivoice-fallback lines (if any exist in the chosen episode) rendered
  line-level not word-level (that's the designed behaviour, not a bug).
- `CHANGELOG.md` — one `[Unreleased]` bullet describing the new composition capability, no
  user-visible behaviour change on the app itself yet (still opt-in via the spike runner,
  not wired to `VideoService`).
- `.viepilot/phases/19-remotion/PHASE-STATE.md` — flip 19.3 row to done, append an evidence
  log entry with the re-render wall time and the 3+ spot-check timestamps.

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `docs/implementation/`
(the plan's Amendments come from PM, not this task); the 19.1 spike report
(`docs/operations/phase19-spike-remotion.md`, immutable). `data/app.db` write access is
**forbidden**, restated after the Task 19.2 incident — `mode=ro` connection only, no
`init_db()` invocation, no schema-migration-runner call.

## Design decisions (Coder, doc-first — commit these under `docs(review)` before code)

The Coder writes a design section here answering each of the following, PM approves, then
code lands in a separate commit. Same pattern as 19.1/19.2.

### D19.3-a: `@remotion/captions` API pick + version

- Confirm which specific API from `@remotion/captions` gives per-word highlighted-during-
  window rendering compatible with an already-flattened, timing-annotated word list
  (`createTikTokStyleCaptions` per the plan, but check whether that helper expects a
  specific normalization the spike's flat words array doesn't already provide, e.g. per-word
  in seconds vs. ms, absolute vs. line-relative). Cite the real API signature, not just the
  package README.
- Pin `@remotion/captions` to a version compatible with `remotion@4.0.529`. Record both.

### D19.3-b: Rendering approach

- Two shapes on the table:
  - (i) Use `@remotion/captions`'s recommended TikTok-style helper directly, accepting its
    default visual (which may differ from the spike's plain band).
  - (ii) Use its lower-level per-word primitive plus your own render, keeping the visual
    identical to the spike's plain band with the active word highlighted (bold/colour/scale).
- Recommend (ii) if the helper's default visual would meaningfully diverge from today's
  libass look; recommend (i) only if the visual match is close enough that the tradeoff of
  building custom rendering isn't worth it. Justify from a real look at the helper's own
  output, not just principle. **If (i) means a visible font/size/colour change from the 19.1
  spike output, that is a scope decision, not a fold-in — flag it here for PM approval
  rather than shipping the change.**

### D19.3-c: Fallback path for empty/absent word list

- Confirm at the rendering-code level (not just at the props-type level) that a line with
  `words: []` or `words: undefined` falls back to the exact rendering the 19.1 spike used
  for that line — same speaker: text string, same font/size/colour/position. Cite the
  branch/conditional in `Episode.tsx`.
- Confirm that an *episode* with `audio_jobs.word_timestamps_json = NULL` (every project
  created before 19.2 landed, e.g. `b330d37f...` unless re-mixed since) also renders as pure
  line-level (this is a superset of the per-line fallback — the whole episode's `line.words`
  field arrives as empty from the runner).

### D19.3-d: Verification frames

- Pick ≥3 timestamps for the spot check, at least one inside a line with multiple words,
  and at least one inside the empty-words fallback branch if the chosen episode has any
  such line. Record: timestamp, expected active word, extracted-frame filename, one-sentence
  visual confirmation.
- **Also** re-render the whole `b330d37f...` episode end-to-end and compare wall time to
  19.1's ~61 s baseline — the karaoke composition should not more than ~2× the render time
  (`@remotion/captions` adds per-frame text layout, not a heavy pixel operation). A larger
  regression is a design finding, not a shrug.

### D19.3-e: Test story for the video-renderer workspace

- There is no test framework installed in `video-renderer/` today (spike only had `tsc
  --noEmit` as the type check). Two options:
  - (i) Add a lightweight `vitest` (or similar) dependency and one real unit test on the
    karaoke selection logic (which word is active for a given `currentFrame`/`fps` +
    `line.words`) — small dependency growth, real automated coverage.
  - (ii) Keep verification manual (`tsc --noEmit` + frame-level spot check) — no new
    dependency, but no automated regression guard against future refactors.
- Recommend one, justify against real cost. If (i), the new dep must not pull in a
  meaningfully large sub-tree (measure `du -sh` after install, report). If (ii), the
  frame-level spot check + wall-time compare **is** the regression guard.

### D19.3-f: Re-verify Task 19.1 invariants aren't broken by the composition change

- `app/services/video_service.py` still not touched (confirm via `git log <phase19-open>..HEAD
  -- app/services/video_service.py`).
- The ffmpeg fallback path in the packaged app still produces byte-for-byte-identical output
  (confirm via a real re-render through the existing `VideoService.generate_video` route on
  the same episode, MP4 hash unchanged).
- `test_video_studio_browser.py` still 10/10.

## Design decisions — Coder answers (2026-09-28)

### D19.3-a: `@remotion/captions` API pick + version

Installed and inspected the real package (`node_modules/@remotion/captions/dist/*.d.ts`),
not just its README:

- **Version:** `@remotion/captions@4.0.529` -- npm's `latest` today, and exactly the same
  version number as `remotion`/`@remotion/cli` (this package follows Remotion's own monorepo
  lockstep versioning). `dependencies: {}` in its own `package.json` -- zero runtime
  dependencies, not even React.
- **Real API signatures:**
  ```ts
  type Caption = { text: string; startMs: number; endMs: number; timestampMs: number | null; confidence: number | null; pageBreakAfter?: boolean };
  type TikTokToken = { text: string; fromMs: number; toMs: number; pageBreakAfter?: boolean };
  type TikTokPage = { text: string; startMs: number; tokens: TikTokToken[]; durationMs: number };
  createTikTokStyleCaptions(input: { captions: Caption[]; combineTokensWithinMilliseconds: number; breakOnSilenceAfterMilliseconds?: number }): { pages: TikTokPage[] }
  ```
- **Unit mismatch, confirmed real:** `Caption`/`TikTokToken` are **milliseconds**
  (`startMs`/`endMs`/`fromMs`/`toMs`), but our whole pipeline (D19.2-a onward) is **seconds**
  (`start_sec`/`end_sec`). `types.ts`'s new `words` field stays in seconds (matching
  `audio_jobs.word_timestamps_json`'s shape exactly, per the card) -- the `*1000`/`/1000`
  conversion happens only at the `createTikTokStyleCaptions` call site inside `Episode.tsx`,
  never in the props schema.

### D19.3-b: Rendering approach -- the card's "(i) vs (ii)" framing doesn't match reality

**Real finding, confirmed by listing every file in the installed package:**
`@remotion/captions`'s `dist/` contains exactly 5 `.js`/`.d.ts` pairs (`caption`,
`create-tiktok-style-captions`, `ensure-max-characters-per-line`, `parse-srt`,
`serialize-srt`) plus an `index` -- **zero `.tsx`/`.jsx` files, zero React import anywhere,
zero runtime dependencies.** This is a pure data/grouping library; it renders nothing. There
is no "(i) accept the helper's default visual" option to choose between -- **rendering is
always custom**, regardless of which option is picked. Recommending what the card called
"(ii)" is therefore not a judgment call between two real alternatives, it's the only
alternative that exists; flagging the correction rather than silently picking.

**How `createTikTokStyleCaptions` is still genuinely used, not bypassed:** called **once per
line** (not once for the whole episode) with that line's own `words` array converted to
`Caption`s and a `combineTokensWithinMilliseconds` set to the line's own duration in ms + 1
(`(line.endSec - line.startSec) * 1000 + 1`). Scoping the call to one line's words, with a
combine-threshold larger than the line itself, guarantees exactly one `TikTokPage` per line
regardless of internal word-gap sizes -- matching our existing per-line grouping exactly,
rather than letting the helper's own auto-pagination (designed for a continuous whole-episode
word stream) split or merge across our line boundaries in ways today's SRT-style model
doesn't have. `breakOnSilenceAfterMilliseconds` is left unset (not needed at this scope).

**Visual:** the active token's `<span>` gets one added style vs. today's plain span -- highlight
colour `#FFD54A` (warm yellow, standard karaoke convention) replacing `#FFFFFF` -- every other
style property (`fontFamily`, `fontSize`, `fontWeight`, `textShadow`, band position, layout)
stays byte-identical to the 19.1 spike's plain span. No font/size/colour/position regression,
confirmed by construction (same style object, one conditional colour override).

### D19.3-c: Fallback path

- Per-line: `if (!line.words || line.words.length === 0)` renders the exact, unmodified 19.1
  plain-span JSX (`{line.speaker}: {line.text}`, same style object) -- literally the same
  branch that exists today, untouched; the karaoke branch is a new `else`, not a replacement.
- Episode-level: `audio_jobs.word_timestamps_json = NULL` is not a separate code path --
  the runner script (D19.3-d) builds every line's `words` field from that same column, so a
  `NULL` episode naturally produces `words: []` for every line, hitting the identical
  per-line fallback branch above. No second conditional needed; confirmed by how the runner
  populates props (single code path, not two).

### D19.3-d: Verification frames -- and a real data-availability finding

**Real finding, checked read-only before writing any code:** the only real episode with
completed audio (`b330d37f...`, used by 19.1/19.2) currently has **`word_timestamps_json =
NULL`** in `audio_jobs`, and **zero `.words.json` sidecar files exist** anywhere under
`data/tts_cache/b330d37f.../` (only `.mp3` files) -- confirmed by a read-only query and a
directory listing. This is expected, not a bug: this project's lines were synthesized and
mixed on 2026-09-15, before Task 19.2's capture code existed, and it hasn't been re-mixed
since (re-mixing would need a real DB write to `audio_jobs`, which this task cannot do). So
today, there is genuinely no real per-word data anywhere for this episode.

**Resolution: the runner re-synthesizes each line fresh via a real Edge TTS call, in-memory
only.** For each of the episode's lines (fetched read-only: text, speaker, and the line's
existing mix-timeline offset from `timestamps_json`), the runner calls
`tts_service._synthesize_edge_tts(text, speaker)` directly -- a genuine network call to the
real Edge TTS endpoint, using the exact same text and speaker config the project already has
-- and aggregates the returned `WordBoundary` list onto that line's existing `start_ms` offset
(same formula as `audio_service._aggregate_word_boundaries`, reimplemented in the runner since
it's a small, pure function). **Nothing is written to `data/app.db` or to
`data/tts_cache/b330d37f.../`** -- the freshly synthesized audio bytes are discarded (the
existing cached mix's audio is what actually plays; only the *word timing* from the fresh
synthesis is used), so the real project's cached files are never overwritten. This costs ~30
real Edge TTS calls (one per line) for this specific episode -- a bounded, one-time cost,
and every word timestamp in the resulting render is **real, not fabricated** captured data,
just captured transiently for this task's demo rather than persisted.

- **Frame timestamps** (chosen after the re-synthesis runs and real per-word times are known
  -- recorded with real values in the report, not guessed in advance): one frame inside a
  multi-word line's middle word, one at a line's first word, one at a line's last word. Exact
  values, extracted frames, and expected-vs-observed words go in
  `docs/operations/phase19-t3-karaoke.md`.
- **Empty-words fallback spot check:** since every line gets real re-synthesized words, this
  episode has **no naturally-occurring empty-words line** to screenshot. Per the card's own
  "if the chosen episode has any such line" conditional, none exists here -- the fallback
  branch is instead verified by a real Vitest unit test (D19.3-e) that renders the karaoke
  logic against a hand-crafted `words: []` line directly, which is a stronger regression
  guard than one manual frame would have been anyway.
- **Wall-time comparison:** the full episode is re-rendered end-to-end and its wall time
  compared to 19.1's ~61 s baseline in the report, per the card's ≤~2× threshold.

### D19.3-e: Test story -- (i), with a measured real cost

Chosen: **(i) add Vitest.** Justification against real, measured cost, not principle:
installed `vitest@^5.0.2` (compatible with Node `>=24.0.0`, matching the workspace's own
`engines` pin) and measured `node_modules` before/after: **688 MB → 725 MB, +37 MB** for
vitest plus its 26 transitive packages -- small relative to the workspace's existing ~660 MB
(dominated by the Chrome Headless Shell, unrelated to this dependency), and it's a
**devDependency only**, so it does not affect 19.1's packaged-app estimate (which already
assumed devDependencies like `typescript` are excluded from shipping). One real unit test
exercises: (a) the active-token-selection logic for a given `currentFrame`/`fps` +
`line.words`, and (b) the fallback branch on a line with `words: []`. Revert-and-confirm-
failure done on both before implementation is called complete.

### D19.3-f: Re-verify Task 19.1 invariants

- `git log <phase19-open-sha>..HEAD -- app/services/video_service.py` must stay empty --
  checked at implementation time, reported in the handover.
- Real ffmpeg-fallback comparison: `data/video/b330d37f.../video.mp4` already exists on disk
  (a real prior render, 2,517,473 bytes, dated 2026-09-15) -- this task re-renders the same
  episode through `VideoService.generate_video` (pure function, no DB parameter; fed with
  data fetched read-only) into a **scratch output path** (never overwriting the real
  `data/video/b330d37f.../` files) and compares the fresh render's hash against the existing
  real file's hash, confirming the ffmpeg path is genuinely untouched.
- `tests/test_video_studio_browser.py` re-run, expect 10/10 unchanged.

## PM review — APPROVED (2026-09-28, session a01f96)

All three real findings accepted as-is:
- D19.3-b reframing (no default visual exists; per-line-scoped `createTikTokStyleCaptions` +
  custom render, `#FFFFFF → #FFD54A` for the active word only) confirmed exactly right. If
  the color turns out to visually clash in the real render, that's a fold-in during
  implementation, not a re-approval.
- D19.3-d in-memory re-synthesis approach confirmed the right shape (ranked against re-mixing
  on the real DB [forbidden] and building a fresh scratch-DB episode [larger scope than
  warranted]). **Caveat to record in the report:** Edge TTS `WordBoundary` values aren't
  guaranteed byte-identical across runs of the same line -- the ≥3 spot-check timestamps and
  expected words must come from the same run whose frames are extracted, not a fixed prior
  baseline. The spot-check proves "the correct word lights up at the right instant in this
  render," not "timings match a golden file."
- D19.3-e vitest choice confirmed fine (devDep-only, measured +37MB, packaging estimate
  unchanged). Record which packages the +37MB actually pulls in (one-line `du` breakdown).
- **Fallback verification via vitest instead of a screenshot: approved as sufficient.**
  Reasoning to record in the report: the fallback branch is a pure conditional
  (`words.length === 0` → the unmodified 19.1 line-level path); the 19.1 spike is already the
  visual proof that path renders correctly; 19.3 doesn't change that code, only conditionally
  invokes it; and an automated unit test catches regressions without human intervention,
  unlike a screenshot. No fallback screenshot needed.

Additional asks for the handover (no design change):
- Note the ~30 real Edge TTS network calls the demo runner makes per run (one-time demo cost,
  not a production concern).
- One line on visual quality: does the word-highlight flip look crisp at 30fps or laggy? --
  a spike-adjacent signal useful for 19.7 planning, not a gate item.
- Record the exact resolved `@remotion/captions` version for a future upgrade review.

Proceed to implementation.

## Verification

- Real re-render of `b330d37f...` (or whichever B1 episode with completed audio + captured
  word timings is available at task-execution time) succeeds end-to-end.
- ≥3 frame-level spot checks confirm the correct word is highlighted at each chosen
  timestamp (frames extracted to disk, referenced in the report).
- `tsc --noEmit` clean on `video-renderer/src/`.
- Python full suite still **1178/1178** (this task adds no Python tests). `ruff check .`
  clean. `git log <phase19-open>..HEAD -- app/services/video_service.py` still empty.
- If D19.3-e (i) was chosen: at least one real vitest (or equivalent) unit test on the
  active-word-selection logic, with a revert-and-confirm-failure check on it.

## Evidence (what the Coder's handover message includes)

- Two commits' shas (design + implementation).
- Full-suite line (`N passed, M warnings in Xs`).
- `ruff check .` line.
- `tsc --noEmit` line.
- Re-render wall time (vs. the 19.1 spike's ~61 s).
- The ≥3 frame-level spot check filenames and their expected-vs-observed words.
- The chosen episode's project id, line count, and whether any lines fell back to
  line-level (empty words).
- Whether D19.3-e (i) or (ii) was taken; if (i), the new dependency's install footprint.
- Carry-over conditions from 19.1 acknowledged (still no 8-min episode; Chrome 270 MB
  still 19.7's problem).

## Definition of done

- Two commits, design **before** implementation.
- Composition renders word-level karaoke on real captured lines and line-level fallback on
  empty ones.
- Report on disk (`docs/operations/phase19-t3-karaoke.md`).
- Full suite + ruff + tsc all green.
- `app/services/video_service.py` genuinely untouched (git log range confirms).
- Handover message per the Evidence checklist above.
