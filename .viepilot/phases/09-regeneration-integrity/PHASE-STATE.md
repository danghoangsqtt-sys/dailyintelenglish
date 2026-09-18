# Phase 9 State — Regeneration Integrity

## Metadata
- **Phase:** 9
- **Slug:** 09-regeneration-integrity
- **Status:** complete
- **Started:** 2026-09-18
- **Closed:** 2026-09-18
- **Milestone Progress:** 1 / 1 task done. Opened after the user had Codex run its own
  independent, parallel read-only `/vp-audit` pass alongside PM's own audit. Codex
  found 10 issues (0 critical, 1 high, 4 medium, 5 low); PM independently
  re-verified all 5 "important" ones by reading the actual source directly — all 5
  confirmed real, no false positives. User chose to fix the 2 most serious: BUG-017
  (a failed audio/video regeneration attempt destroyed the DB record of a still-valid
  previous success — real data loss) and BUG-016 (changing a speaker's voice settings
  didn't invalidate downstream project status — the same bug class as BUG-013). Both
  now fixed. BUG-018, BUG-019, and ENH-007 remain logged in `.viepilot/requests/` but
  out of scope for this phase per user decision.
- **Test Suite Status:** 613/615 pass (2026-09-18, after Task 9.1) — 2 failures, both
  confirmed non-regressive in isolation: the project's known Gemini-retry/backoff
  timing flake class, plus a newly-observed (first time this session) unrelated
  browser-timing flake in the music library waveform test, touching none of this
  task's files. See TRACKER.md.

---

## Tasks Status & Acceptance Evidence

### Task 9.1: Preserve prior job data on regeneration failure; downgrade status on voice-settings change — ✅ DONE (2026-09-18)
- **Status:** done
- New `audio_service.mark_audio_job_failed()`/`video_service.mark_video_job_failed()`
  narrowly UPDATE only `status`/`error_message`/`completed_at` on an existing job row
  on a failed regeneration attempt, preserving every other column (file paths,
  duration, timestamps, etc.) — falling back to a minimal error-only INSERT only when
  no job row exists yet (a genuine first-ever failure, matching prior behavior for
  that case). `download_audio`/`download_video`'s status gate correctly widened to
  keep a preserved prior success downloadable after a later failure, with a non-null
  path check preventing this from masking a genuine first-ever failure's 404. New
  `project_service.mark_speaker_voice_changed()` downgrades project status to
  `script_generated` when a speaker's voice settings change while status is
  `audio_generated`/`video_generated`/`complete`, and is a genuine no-op at `draft`/
  `script_generated` — implemented via a shared
  `_downgrade_downstream_to_script_generated()` helper that `mark_script_changed()`
  (Task 7.1) now also delegates to, with zero change to its own external behavior,
  correctly avoiding the naive-reuse trap this task card explicitly flagged in
  advance. Implemented by Codex, accepted by PM per AR-06. **Zero real defects found
  on PM review** — PM independently re-ran every verification command, read the full
  diff for all 6 production files, and confirmed the new tests include real
  end-to-end byte-level verification (actual generated MP3/MP4 bytes compared
  before/after a forced failure, not just DB-row assertions) and a fully-parametrized
  5-status regression guard for the speaker case. 613/615 full suite passes; the 2
  failures are both confirmed non-regressive in isolation (1 known Gemini-retry
  flake, 1 newly-observed unrelated browser-timing flake in an untouched file, noted
  honestly rather than silently grouped into the known class). See
  `tasks/task-9.1.md` for the full record.

**This closes Phase 9 (Regeneration Integrity) in full**, since Task 9.1 was its only
task.
