# Phase 19 Implementation Plan — Animated Learning Videos with Remotion (ENH-013)

**Status:** OPEN 2026-09-28 (planning; task 19.1 doc-first card ready).
**Controlling plan.** PM, 2026-09-28. **Starts after Phase 18 closes** (Phase 18 closed
2026-09-26, `v1.1.0-beta`, tag `die-vp-p18-complete`).
**Authority:** owner decision **D29** (2026-09-24, brainstorm
`docs/brainstorm/session-2026-09-24.md`) and follow-on **D32** (2026-09-28, this document's
planning-shape decisions).
**Evidence baseline:** ENH-013 request card (`.viepilot/requests/ENH-013.md`); Phase 18 close-out
(TRACKER §Current Status, HANDOFF `phases.18`).

## 1. Goal

Replace today's static-background + burned-in line-level subtitles (ffmpeg, "Level 2") with a
Remotion-rendered composition adding **word-level karaoke captions**, an **active-speaker
indicator**, **vocabulary/idiom pop-up cards** timed to the containing line, and
**intro/outro + a chapter/progress bar + a Remotion-rendered thumbnail still**. The ffmpeg
path stays as the tested fallback: any Remotion failure still produces today's video, and
`remotion` is opt-in until Gate B-12 accepts it.

## 2. Invariants (in addition to Phases 13–18)

36. **The Remotion path is opt-in and reversible.** A request-time flag, a settings toggle
    and a `DIE_VIDEO_RENDERER=remotion|ffmpeg` kill switch all resolve to `ffmpeg` when
    ambiguous. A Remotion failure never fails a video — it degrades to the existing ffmpeg
    path (I36-a). The fallback rate is reported (I36-b), same pattern as Phase 18 §I32.
37. **The renderer is local-only.** No episode text, audio or metadata leaves the machine
    from `video-renderer/`. Remotion runs headless Chromium locally against a `file://`
    subprocess call. Verified by static grep in the Node workspace for `http://` / `https://`
    outbound calls and by network capture during the spike render.
38. **No secret in the workspace.** The `video-renderer/` tree contains no `.env`, no key,
    no service URL. `.gitignore` excludes `node_modules/`, `.env*`, build output and any
    absolute path artefacts. Verified by a repo-wide grep for the current
    `DIE_OPENAI_COMPAT_API_KEY` / `DIE_GEMINI_API_KEY` values (never printed).
39. **The licence is re-checked at every phase gate.** Remotion is free for individuals and
    orgs up to 3 employees; the owner is solo. If the org grows, the phase is re-opened and
    the default flipped back to `ffmpeg` until a commercial licence is in place.
40. **Thresholds unchanged.** The media gate (duration ±0.5 s, A/V drift, codec check) still
    passes on Remotion output. This phase changes *who* renders, never *what passes*.

## 3. Tasks

Order: **19.1 (spike) → PM decision (PASS / SCOPE-CUT / STOP) → 19.2–19.6 (composition
build-out, per spike outcome) → 19.7 (wire-up + kill switch + packaging) → 19.8 (Gate B-12,
PM) → 19.9 (close-out / default flip)**. Session partition and messaging as in Phase 16 §6.

### 19.1 — Spike: scaffold + measure render time (Coder, P0)

**See:** `.viepilot/phases/19-remotion/tasks/task-19.1.md` (doc-first card, fully expanded).

**Allowed files (summary; the card is binding):** new `video-renderer/` workspace
(`package.json`, `tsconfig.json`, `.gitignore`, `src/`, `README.md`), new
`scripts/run_remotion_spike.py`, new `docs/operations/phase19-spike-remotion.md`,
`CHANGELOG.md` (one bullet under `[Unreleased]` after the report lands).

**Deliverable:** the spike report on disk, with every "Evidence" item filled in real —
render wall time, install footprint, packaging estimate, A/V correctness. A PASS / SCOPE-CUT
/ STOP proposal in the report. **PM decides the phase's next task card set.**

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `docs/implementation/`.
`data/app.db` is read-only.

### 19.2 — Edge TTS `WordBoundary` capture + per-word timestamps (Coder, provisional)

Opens only if the spike proposal is PASS. Adds:

- `EdgeTTS.synthesize_line()`'s `WordBoundary` events captured into a per-line word list.
- A `word_timestamps` column (JSONB-shaped in SQLite: a JSON string) on the existing per-line
  audio store, added by an additive migration (same pattern as `004_youtube_chapters_measured.sql`).
- `AudioService.mix_project` optionally aggregates per-word times up to the mixed output's
  timeline (same offset math as today's per-line times, applied at word grain).
- Unit tests exercising a real Edge TTS synthesis on one B1 line with a known 5-word count.

### 19.3 — Word-level karaoke captions composition (Coder, provisional)

`@remotion/captions` + `createTikTokStyleCaptions`. Inputs: 19.2's per-word list. Rendered as
a subtitle band matching Step 5's existing subtitle-style choice (today's libass style is the
starting point; a future subtitle-style picker is out of scope here).

### 19.4 — Active-speaker indicator (Coder, provisional)

A speaker chip (name + optional avatar) that highlights when its speaker's line is playing,
matching Step 4's existing speaker-panel colors. Uses the same `speakers` rows the video
already reads.

### 19.5 — Vocabulary/idiom pop-up cards (Coder, provisional)

Timed to the line that contains the item, from the existing Learning pack
(`learning_contents` table). No new learning content is generated by this task — it renders
what already exists. A project with no Learning pack still renders successfully (identical to
today's "no learning pack" export path).

### 19.6 — Intro/outro + chapter/progress bar + Remotion thumbnail still (Coder, provisional)

- A short intro (project title + speaker names) and outro (subscribe/next-episode CTA,
  content owner-approved before this task's card is written).
- A chapter/progress bar overlay drawn from the same measured chapters
  `YouTubePackageService.real_chapters_from_timestamps()` already computes (Task 1.9b).
- A Remotion **still** rendered at a chosen frame — feeds ENH-012/Phase 20 (AI thumbnails)
  by giving the local image model a real headline overlay to composite against.

### 19.7 — Wire-up + toggle + kill switch + packaging + `check_dependencies.py` (Coder, provisional)

- `VideoService.generate_video()` learns `renderer: "ffmpeg"|"remotion"` (default `"ffmpeg"`),
  driven by request flag → settings toggle → `DIE_VIDEO_RENDERER` env kill switch
  (`ffmpeg` when set to anything other than `remotion`).
- Fallback-rate readout on `GET /api/video/health` (or existing health surface), same
  pattern as Phase 18 §18.4's cloud fallback readout.
- `scripts/check_dependencies.py` checks Node runtime, `video-renderer/node_modules/`
  freshness, headless Chromium presence; missing pieces are guidance not crashes.
- PyInstaller build recipe extended to bundle `video-renderer/` (measured against the 19.1
  spike's real packaging-footprint estimate). Startup path verified against the packaged
  `.exe`, not just the dev tree.

### 19.8 — Gate B-12: media gate + owner visual sign-off (PM)

Report: `docs/operations/phase19-gate-b12.md`. Real runs on ≥ 3 real episodes across CEFR
levels the owner selects, with `renderer=remotion`. Owner accepts / declines. PM records A/V
drift, duration, codec, karaoke sync spot checks, and a full-video visual review from the
owner.

### 19.9 — Close-out: flip default to `remotion` (only on Gate B-12 PASS) (Coder)

- If Gate B-12 accepted: `DIE_VIDEO_RENDERER` default flips from `"ffmpeg"` to `"remotion"`,
  same pattern as Task 18.11 (`AI_MODE` default flip after Gate B-11 PASS).
- Version bump: **1.1.0-beta → 1.2.0-beta** (MINOR — new user-visible feature, backward
  compatible via I36's kill switch). CHANGELOG entry closes `[Unreleased]` into
  `## [1.2.0-beta]`.
- Tag `die-vp-p19-complete`.

## 4. Session partition

Same as Phase 16 §6 / Phase 18 §Session partition. Two Claude sessions run in parallel: PM
Claude Opus (this session), Coder Claude Sonnet. Live channel is `SendMessage`. Git is the
single source of truth.

Coder owns `video-renderer/` and Python glue after the handover commit. PM owns the plan,
the review, the gate reports and the version bump.

## 5. Version

Enters at `1.1.0-beta`. Closes at **1.2.0-beta** iff Gate B-12 PASS (MINOR — new feature,
backward-compat kept via kill switch). Any FAIL closes the phase at the accepted subset (a
partial Remotion path still shipped, but default stays `ffmpeg` and version stays
`1.1.0-beta` — same shape as the Phase 18 Amendment C conditional close-out).

## 6. Amendments

### Amendment A — 2026-09-28: Task 19.1 spike PASS (owner D33) + 19.7 shape correction

Task 19.1's real spike report (`docs/operations/phase19-spike-remotion.md`, commit
`4dd325b`) landed with three material findings, all folded here rather than lost:

- **Render time is not the phase blocker.** Measured ~61 s wall time for a 2:56 B1 episode
  (3 real runs, stable within 1 s); linearly extrapolated ~166 s (~2.8 min) for a full 8-min
  episode. Far under ENH-013's "several to 10+ min" feared risk. **Phase 19 proceeds** —
  owner D33 accepts PASS.
- **Real-DB preflight was stale.** The phase's own PHASE-STATE preflight asserted an
  existing 8-min B1 episode with completed audio in `data/app.db`; the spike found this
  false — only one project (`b330d37f...`, "Demo Episode", B1, 2:56) has a completed audio
  job at all. The spike rendered that project and extrapolated. Carry-over condition #1 into
  Task 19.2: **opportunistic 8-min re-confirm** once the owner generates a real 8-min
  episode, non-blocking (frame-driven render — no scaling cliff expected).
- **Packaging weight is heavier than ENH-013's early guess.** ENH-013 predicted "~150–300
  MB". Measured `video-renderer/node_modules/`: **~660 MB total, ~270 MB Chrome Headless
  Shell alone.** Packaged-app estimate: **169 MB → 740–840 MB (4–5× increase)**, of which
  ~270 MB (the Chrome binary) is a hard floor — Chrome Headless Shell *is* the render
  engine, not a trimmable dependency.

**19.7 shape correction:** Task 19.7's card, when it is written, **must** plan explicitly
for one of:

1. **Ship the ~270 MB Chrome binary bundled**, accepting the 740–840 MB packaged size.
2. **Download Chrome Headless Shell on first use** post-install (Remotion's own CLI supports
   this pattern), keeping the base installer near today's 169 MB and adding the ~270 MB on
   first render, once. Requires a real network-connected first render; must degrade to the
   ffmpeg fallback (I36) if that first-run download fails.
3. **Drop Remotion entirely** if the packaging cost is not acceptable to the owner at 19.7
   review time — the ffmpeg fallback remains default, and the phase closes with the
   composition work Remotion did in 19.2–19.6 available only in the dev tree.

The choice is deferred to 19.7's design commit (with real numbers from a probe of option
#2's real first-run download behaviour) — not decided here. What is decided here: **19.7 may
not treat ~270 MB as an optimization target.**

19.2's card is written and on disk (`.viepilot/phases/19-remotion/tasks/task-19.2.md`);
19.3–19.6 remain provisional pending 19.2 close.
