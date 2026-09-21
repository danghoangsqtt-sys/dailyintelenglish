# Task 14.5 — Correct the Phase 13 Acceptance Report

- **Status:** pending
- **Owner:** PM
- **Priority:** P2
- **Dependency:** none (runs in parallel with 14.1–14.3)
- **Controlling detail:** plan §6 Task 14.5; brainstorm decision D7

## Objective

Keep the project record honest: `docs/operations/phase13-acceptance.md` states the Gate B
failure is "not a system/infrastructure defect" and that "the architecture works as
designed". Both claims are falsified by evidence gathered after the report was written.
The correction is **additive** — the original conclusion stays readable so the history
shows what was believed, when, and why it changed.

## Allowed files

`docs/operations/phase13-acceptance.md` only.

## Required content of the correction

1. A dated `## Correction (2026-09-21, PM/Tester review)` section placed immediately
   after `## Decision: **FAIL**`, stating:
   - the FAIL decision itself stands (no threshold was weakened, none is now);
   - finding A — the ±15%-per-section hard stop compounds a 66.7% per-section pass
     rate into 13.2% predicted / 11% observed job success; the completed job passed the
     product gate at −2.4% while sections were individually off-target; the internal gate
     was stricter than the product requirement (plan §4.3);
   - finding B — Gemini, the provider the report recommended shipping, was never run
     through Gate B; when run: 0/2, HTTP 503 with no backoff anywhere in the gateway,
     a Task 13.7 regression versus the pre-13.7 code (plan §1, brainstorm Topic 3);
   - finding C — `repair_count`, `fallback_used`, `actual_provider`, `model` are never
     written, so the report's "repair did not correct it" had no telemetry behind it;
   - what changes: Task 13.10 blocked (D1); Phase 14 opened; pointers to the brainstorm,
     the Phase 14 plan, and ADR-001 amendment A1.
2. Inline `> **Superseded — see Correction.**` annotations at the top of "Root cause"
   and "Recommendation". No sentence of the original text is deleted or reworded.
3. The "Gate B thresholds checked" table is left untouched (its numbers were correct).

## Verification

- `git diff --stat` shows one file; `git diff` shows additions only (zero removed lines);
  original paragraphs remain byte-identical.
- The correction cites only facts present in `docs/brainstorm/session-2026-09-21.md`
  or re-verified by the PM (PHASE-STATE preflight).

## Execution record (PM fills in)

- Commit:
