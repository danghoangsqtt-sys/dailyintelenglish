# Task 52.3 — BUG-048 text spacing and CHANGELOG order

Status: implemented_verified 2026-10-19.

## Objective

Restore the missing space before numbers in text written since 2026-10-16, user-facing first, and put the CHANGELOG Phase 49 section under `[Unreleased]`.

## Paths

- frontend/static/js/explainer_editor.js (UI string "the21" only; coordinate with 52.2 — same file, run 52.2 first or edit both in one pass)
- README.md
- docs/user/windows-installation.md
- docs/user/solo-explainer.md
- docs/operations/desktop-recovery-20261016.md
- CHANGELOG.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/phases/49-solo-explainer/**, .viepilot/phases/50-audit-recovery/**, .viepilot/phases/51-desktop-runtime-recovery/** (status/prose lines only)
- .viepilot/requests/BUG-048.md

## File-Level Plan

- Insert a space between a word and a following number in prose ("Phase49" → "Phase 49", "passed in787.66s" → "passed in 787.66s", "phát hành1.4.0-rc.1" → "phát hành 1.4.0-rc.1").
- Do **not** touch: code identifiers and slugs (`front21`, `die-vp-p49-...`, file paths, URLs, Git hashes, versions such as `v1.4.0-rc.1`, `B-25`), code blocks, or the numeric values themselves.
- Use a reviewed, file-by-file pass (scripted candidate list + manual diff review), not a blind global regex.
- CHANGELOG: move the "Added (source, Phase 49 tasks 49.6–49.10 …)" block from above the file intro into `## [Unreleased]`.

## Verification

Re-run the audit grep (word immediately followed by a digit) on the listed files: only intended identifiers remain. `git diff --word-diff` reviewed; no number changed. Markdown links still resolve.

## Verification result 2026-10-19

- Reviewed scripted pass (word+digit, then punctuation+digit after a letter, and "— N"), protecting code spans, link targets, URLs, HTML tags, fenced code, `file.ext:line` references and the historical page name `Step1-Config`. Kept as identifiers: MP3/MP4, FIX2*, Dots3, Jinja2, Qwen3, SHA256, AGPLv3, sqlite3, cu128, Rig3D, front21/Front21, CEFR "A2". Manual: `checkpoint e5b2893`, `Gate V48/V49`, `full 9:16`.
- Every changed line differs from the original only by inserted spaces (checked hunk-by-hunk); no number or identifier changed. UI string fixed in `explainer_editor.js` ("the 21 front presenter pictures"); `node --check` clean.
- CHANGELOG: Phase 49.6–49.10 "Added" block moved from above the intro into `[Unreleased]`, before the 49.5b recovery entry.
- Also touched by the `Gate V4x` fix: `.viepilot/phases/48-character-voices/PLAN.md`, `tasks/task-48.1.md`, `docs/operations/phase48-character-voices.md`.
- Not in scope (left as is): a digit directly followed by a word ("21ảnh"), and missing spaces after a period ("planned**.49.5b").
