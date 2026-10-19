# Task 52.3 — BUG-048 text spacing and CHANGELOG order

Status: planned 2026-10-19.

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
