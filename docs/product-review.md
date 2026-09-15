# Product Review Report

Status as of 2026-09-15 (Day 6 of a 21-day target). Assembled from `.viepilot/ROADMAP.md`
and `.viepilot/TRACKER.md` — every status below matches those files exactly; see them for
full evidence and decision rationale rather than duplicating it here.

## Feature checklist

### Phase 1 — Full Feature Build (✅ Complete, 2026-09-13, Day 3 of 21)

| # | Feature | Status |
|---|---------|--------|
| 1.1 | Project Setup & Infrastructure | ✅ Done |
| 1.2 | Dashboard & Project Management | ✅ Done |
| 1.3 | Step 1 — Script Config Wizard | ✅ Done |
| 1.4 | Step 2 — AI Script Generation | ✅ Done |
| 1.5 | Step 3 — Learning Content | ✅ Done |
| 1.6 | Step 4 — TTS Audio Studio | ✅ Done (Edge TTS only — see "Won't do" below) |
| 1.7 | Step 5 — Video Studio (background + subtitles, 16:9 + 9:16) | ✅ Done — LivePortrait avatar lip-sync inference itself not started (see "Deferred" below) |
| 1.8 | Step 6 — Thumbnail Generator | ✅ Done |
| 1.9 | Step 7 — YouTube Package (titles/description/tags/chapters/`.zip` export) | ✅ Done |
| 1.10 | Music Library | ✅ Done |

**Won't do:** Real OmniVoice GPU voice-cloning integration. Investigated fully (model
downloaded, GPU-load verified) but decided against 2026-09-13 — OmniVoice's real API is
zero-shot voice *cloning* from a reference sample, not the text-described "voice design"
originally planned, and raises consent/rights questions without a clear benefit over the
already-working Edge TTS. See `docs/tts-setup.md`.

### Phase 2 — Testing & Polish (✅ Complete at buildable scope, 2026-09-15, Day 6 of 21)

| # | Feature | Status |
|---|---------|--------|
| 2.1 | Quality Testing (CEFR accuracy, multi-accent TTS, audio quality, video) | ✅ Done — 18/18 real CEFR samples (14 PASS/4 BORDERLINE/0 FLAG), 20/20 real TTS syntheses, real LUFS/sync measurement |
| 2.2 | Bug Fixes & Performance | ✅ Done (buildable scope) — 1 real fix shipped, 1 already-done, 1 moot, 1 deferred (see below) |
| 2.3 | UX Polish (7 items: progress indicator, breadcrumbs, shortcuts, error toasts, empty states, responsive layout, auto-save indicator) | ✅ Done, all 7/7 |
| 2.4 | UI Redesign Slice 1 (light Dashboard + CapCut-style Script workspace) | ✅ Done |
| 2.5 | Fix Task 2.1c's 3 findings (LUFS drift, 9:16 video, Scottish/British disclosure) | ✅ Done |
| 2.6 | Fix 3 findings from a post-Task-2.5 audit pass | ✅ Done |

### Phase 3 — Review & Documentation (🔄 In Progress, opened 2026-09-15)

| # | Feature | Status |
|---|---------|--------|
| 3.1 | Documentation (README, prompt guide, TTS setup guide, API reference) | ✅ Done |
| 3.2 | Demo & Review (this report, sample episodes, demo video) | 🔄 In Progress |
| 3.3 | Final Cleanup (logging, `.env.example`, pinned requirements, `v1.0.0-beta` tag) | ⏳ Not started |

## Known issues

Full detail in `.viepilot/TRACKER.md`'s "Known Issues" section. Summary, by whether
they're fixable in this codebase:

- **Upstream limitation, not fixable here:** the `scottish` accent resolves to the exact
  same Edge TTS voice as `british` — Microsoft's neural voice catalog has no dedicated
  Scottish voice at all. Disclosed via a UI tooltip (Task 2.5c).
- **Pre-existing, real, deliberately not yet fixed** (found during Task 2.6's audit,
  user chose to leave noted-only): `save_video_job`'s error path wipes previous
  successful file paths to `NULL` on a failed regenerate (narrow — only triggers on a
  regenerate-after-success that then fails); `init_db()`'s migration fallback assumes at
  most one non-idempotent statement per migration file (true today, a design note for
  future migrations).
- **Test infra only, not a product defect:** a known, accepted timing flake affects
  Gemini retry/backoff-pattern tests under an unusually slow full-suite run (always
  passes in isolation; did not recur in the most recent 533/533 run).

## Future improvements (deliberately deferred, not scheduled)

- **Progress cancellation** (Task 2.2) — stopping a generation mid-flight needs a real
  background-job/cancellation architecture; every current generation route is a
  synchronous request/response call. Recognized as a genuine architectural addition, not
  a quick fix — explicitly kept out of Phase 2's scope rather than rushed.
- **Real LivePortrait lip-sync inference** (Task 1.7) — avatar image *sourcing* is
  solved (user-upload only, delivered as Sub-task 1.7c); the actual lip-sync model
  integration itself is a separate, comparably-sized research effort to the OmniVoice
  investigation, not started.
- **`news`-genre CEFR calibration drift** (Task 2.1b) — the `news` genre consistently
  pulls idiom/grammar sophistication about half a CEFR level higher than
  `small_talk`/`interview` at the same level (A2/B1/B2 × `news` landed BORDERLINE in an
  18-sample real review). A prompt-tuning task, not a defect — logged, not acted on.
- **Phase 3's own remaining items** (3.2's demo video, 3.3 Final Cleanup) — see the
  feature checklist above.
