# Phase 10 State — Backlog Cleanup

## Metadata
- **Phase:** 10
- **Slug:** 10-backlog-cleanup
- **Status:** complete
- **Started:** 2026-09-18
- **Closed:** 2026-09-18
- **Milestone Progress:** 2 / 2 tasks done. Opened via `/vp-debug` at the user's
  request to continue fixing the remaining backlog findings from the 2026-09-18
  audits — all 6 already fully diagnosed, no new investigation needed. Mid-phase,
  the user made a standing policy change ("từ bây giờ bạn thực hiện luôn không giao
  cho codex nữa") — PM self-implemented both tasks directly instead of delegating
  to Codex, a durable change from the AR-06 split used through Phase 9 (distinct
  from Task 8.1's one-time deviation). Task 10.1 fixed the 2 remaining real
  code-behavior bugs (BUG-018, BUG-019). Task 10.2 fixed the 4 pure documentation/
  metadata findings (BUG-014, BUG-015, ENH-006, ENH-007), plus one additional
  related inaccuracy found and fixed along the way (a false LivePortrait dependency
  edge in the Module Dependencies diagram, both embedded and sidecar copies).
- **Test Suite Status:** 617/619 pass (2026-09-18, after Task 10.1) — the 2
  failures are the project's known Gemini-retry/backoff timing flake class,
  confirmed passing instantly in isolation. See TRACKER.md.

---

## Tasks Status & Acceptance Evidence

### Task 10.1: Clear stale per-line audio cache on line regenerate; stop deleting avatar files before commit is confirmed — ✅ DONE (2026-09-18)
- **Status:** done
- `script_service.update_script_line` now clears `audio_cache_path`/
  `duration_seconds` when a line's text changes (BUG-018). Avatar uploads
  (`avatar_service.py`) now write each upload to a unique filename and never
  delete the previous file at finalize time; the actual old-file cleanup happens
  as a best-effort step in the API route only after the surrounding transaction's
  commit is confirmed to have succeeded (BUG-019). Self-implemented by PM per the
  user's standing policy change, held to the same doc-first, independent
  verification (including a real revert-and-confirm-failure check on the core
  regression test), and git-persistence gates as any Codex-implemented task. See
  `tasks/task-10.1.md` for the full record.

### Task 10.2: Documentation cleanup — stale task-card status fields, README, ARCHITECTURE.md — ✅ DONE (2026-09-18)
- **Status:** done
- 4 Phase 2 task cards' stale `Status` fields corrected (BUG-014). README.md's
  Phase 4 section brought up to date and a new section added for Phases 5-9
  (BUG-015). ARCHITECTURE.md's status-downgrade behavior documented for both
  Task 7.1 and Task 9.1 (ENH-006); WebSocket/OmniVoice/LivePortrait inaccuracies
  corrected and the embedded system-overview Mermaid diagram synced byte-for-byte
  with its sidecar (ENH-007) — plus the same LivePortrait inaccuracy found and
  fixed in the separate Module Dependencies diagram. Self-implemented by PM. See
  `tasks/task-10.2.md` for the full record.

**This closes Phase 10 (Backlog Cleanup) in full.** All 6 findings from the
2026-09-18 audits (Codex's parallel scan and PM's own read-only pass) are now
resolved. Combined with Phase 9's BUG-016/BUG-017, every finding from both audits
has been addressed.
