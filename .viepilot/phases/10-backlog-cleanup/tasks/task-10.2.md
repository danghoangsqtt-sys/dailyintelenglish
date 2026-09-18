# Task 10.2: Documentation cleanup — stale task-card status fields, README, ARCHITECTURE.md

## Meta
- **ID**: 10.2 (second task of Phase 10 — Backlog Cleanup)
- **Phase**: 10
- **Status**: planned
- **Priority**: low (4 real but purely cosmetic/documentation findings)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: `.viepilot/requests/BUG-014.md`, `BUG-015.md`, `ENH-006.md`, `ENH-007.md` —
all 4 found and confirmed real during PM's own 2026-09-18 read-only `/vp-audit` pass
and Codex's independent parallel pass. Bundled into one task per the Task 2.3/4.4/
5.3/6.1 precedent of grouping small, unrelated fixes rather than one task each — all
4 are pure documentation/metadata edits, no application code touched, no tests
required beyond confirming the files still parse/render correctly.

## Current state (already researched in each request file — do not re-derive)

1. **BUG-014**: `.viepilot/phases/02-testing-polish/tasks/task-2.1b.md`,
   `task-2.1c.md`, `task-2.5.md`, `task-2.6.md` each still say `**Status**:
   in_progress` in their Meta section despite each having its own `## PM Acceptance`
   section confirming completion. Fix: change each to `**Status**: done`.
2. **BUG-015**: `README.md`'s `#### Post-v1.0.0-beta Polish (Phase 4)` section still
   says "🔄 In Progress" (stale since early Phase 4, Task 4.2 at "1/7"). Phases
   4(remainder)/5/6/7/8/9 are entirely undocumented in README.md. Fix: update the
   Phase 4 section to "✅ Done" with its final task list, and add sections (or a
   consolidated summary) for Phases 5-9, matching the existing Phase 2/3 sections'
   style — summarize from `.viepilot/ROADMAP.md`'s accurate, up-to-date records
   rather than re-deriving from scratch.
3. **ENH-006**: `.viepilot/ARCHITECTURE.md`'s Project data model documents the
   `status` enum but not its transition rules — specifically not Task 7.1's
   script-edit downgrade behavior, nor Task 9.1's speaker-voice-settings downgrade
   behavior (which didn't exist yet when ENH-006 was first logged, but is now also
   real and should be documented in the same place). Fix: add a short note near the
   `status` field's documentation describing the forward-only rule and both
   downgrade exceptions.
4. **ENH-007**: `.viepilot/ARCHITECTURE.md` line 11's System Overview text diagram
   still says `↕ REST API / WebSocket (streaming)` — the real implementation is pure
   polling everywhere. The Mermaid data-flow diagram (~line 124-133) shows
   `E2[OmniVoice GPU\ngenerate per line]` and `F3[Lips-sync Avatar\nLivePortrait]` as
   active — Edge TTS is the sole official engine, LivePortrait was never
   implemented. The embedded `system-overview` Mermaid block diverges from its own
   sidecar file (`.viepilot/architecture/system-overview.mermaid`) by 2 edges
   (missing `LCS`/LearningContentService in the router fan-out and Gemini-dependency
   edges). Fix all 3.

## Objective

Pure documentation/metadata corrections — no application code, no tests beyond a
basic sanity check that Markdown/Mermaid still renders (no automated test suite
covers prose content in this project; visual confirmation is sufficient, matching
how `.viepilot/*.md`/`README.md`/`ARCHITECTURE.md` have always been maintained).

### Required decisions (already settled by PM, do not re-litigate)

1. For BUG-015's README update, summarize from `.viepilot/ROADMAP.md` — the
   accurate, already-maintained record — rather than re-deriving phase content from
   git history or task cards directly.
2. For ENH-007's Mermaid sync, verify which of the two versions (embedded vs.
   sidecar) is actually correct before picking a direction — PM's own diff found the
   sidecar includes `LCS` in both edges and the embedded version omits it; confirm
   this against the actual `app/api/*.py` router registrations before finalizing
   which one is edited to match the other.
3. Do not invent new diagram content beyond correcting the 3 specific inaccuracies
   listed — no new diagrams, no restructuring of ARCHITECTURE.md's existing
   sections.

## Proposed File-Level Plan

- `.viepilot/phases/02-testing-polish/tasks/task-2.1b.md`, `task-2.1c.md`,
  `task-2.5.md`, `task-2.6.md`: `Status` field only.
- `README.md`: Phase 4 section status + task list; new section(s) for Phases 5-9.
- `.viepilot/ARCHITECTURE.md`: status-transition note in the Project data model
  section; System Overview text diagram; data-flow Mermaid diagram; embedded
  system-overview Mermaid block synced with its sidecar.
- `.viepilot/requests/BUG-014.md`, `BUG-015.md`, `ENH-006.md`, `ENH-007.md`: PM will
  mark these done at acceptance — Codex should not edit their `Status` fields.

## Allowed files
- `.viepilot/phases/02-testing-polish/tasks/task-2.1b.md`
- `.viepilot/phases/02-testing-polish/tasks/task-2.1c.md`
- `.viepilot/phases/02-testing-polish/tasks/task-2.5.md`
- `.viepilot/phases/02-testing-polish/tasks/task-2.6.md`
- `README.md`
- `.viepilot/ARCHITECTURE.md`
- This task card, for plan/evidence updates.

## Verification checklist
- [ ] All 4 Phase 2 task cards show `Status: done`.
- [ ] README.md's Phase 4 section reflects its real final state; Phases 5-9 are each
  represented (individually or in a consolidated summary).
- [ ] ARCHITECTURE.md's Project data model documents both status-downgrade
  exceptions (script edit, speaker voice-settings edit).
- [ ] ARCHITECTURE.md no longer claims WebSocket streaming; no longer shows
  OmniVoice GPU/LivePortrait as active in the data-flow diagram.
- [ ] The embedded system-overview Mermaid block and its sidecar file match exactly.
- [ ] `git diff --check` clean, real output pasted. (No `ruff`/pytest run required —
  no Python/JS files touched; confirm via `git status --short` that only the files
  above changed.)

## PM Plan Review

(Pending — Codex to present pre-code plan per AR-06 before any implementation.)
