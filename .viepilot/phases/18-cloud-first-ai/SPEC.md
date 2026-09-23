# Phase 18 Specification — Cloud-First AI with Local Fallback (ENH-011)

The controlling contract is `docs/implementation/phase-18-cloud-first-ai.md`. Authority: owner
decisions D21–D24 (`docs/brainstorm/session-2026-09-23.md`). The phase **starts after Phase 17
closes.**

## Goal

A generic OpenAI-compatible cloud provider is the primary AI writer, with local qwen as the
automatic fallback. Each provider has its own time budget, and a circuit breaker protects against
a flaky free tier. The dedicated Gemini provider is removed. The key, URL and model are set in
Settings. The fallback rate is measured.

## Required gates

- **Doc-first:** each card's design is PM-approved before code.
- **Invariants 31–35:**
  - the key is never logged, returned or committed;
  - the fallback is always available within its own budget;
  - the kill switch means zero cloud calls;
  - thresholds stay pinned;
  - the UI carries the privacy note.
- **Gate B-9 (18.5):** `cloud_first` reaches B1 8-min 5/5 with no regression against Gate B-8.
  The fallback rate is reported.

## Session partition

As in Phase 16 §6. The Coder owns this folder after the handover commit. The PM runs Gate B-9
with the owner's key, which comes from `.env` and is never printed.
