# Task 32.6e — Storyboard guidance and generic prompt pack

## Objective

Teach storyboard generation to create useful 3–6 second inserts and provide production-ready prompts for the locked 20 generic activities.

## Paths

- `prompts/storyboard/storyboard.txt` — insert-beat instructions.
- `docs/operations/activity-library-prompt-pack.md` — 20 approved generic prompt specifications and import names.
- `docs/implementation/phase-32-talking-sprites.md` — finalized cutaway behaviour reference.
- `tests/test_storyboard_propose.py` — prompt-contract assertion where supported by existing tests.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_storyboard_propose.py -q`

## Acceptance Criteria

- [x] Insert beats are explicitly 3–6 seconds, action-led and not gratuitous.
- [x] The pack has all D72 activities, filename, primary prompt, negative constraints and 16:9 framing rules.

## Result — 2026-10-09

- The storyboard prompt now says every insert must target 3–6 seconds, use the smallest likely
  contiguous line range, lead with one reusable plain activity and serve comprehension rather
  than decoration.
- The canonical D72 pack distinguishes its locked 20-image baseline from the five later common
  additions and 80 professional verb visuals. It provides an exact import filename and tailored
  clothing/action prompt for every activity, plus shared 1280x720 framing and negative rules.
- Corrected stale filename drift (`outdoor`, `working-laptop`, restaurant/indoor contexts) to the
  exact names already present under `generic/common`.
- Real asset check: all 20 files exist; all are 1672x941 and within the importer's 16:9 tolerance
  (maximum ratio delta 0.000945). The detailed ChatGPT Web document also contains 20 unique names.
- Updated the Phase 32 implementation reference from the old 32.6 gate layout to 32.6a-f plus
  owner Gate B-22 at 32.7.
- Verification: `pytest tests/test_storyboard_propose.py -q` → 10 passed; targeted Ruff and
  `git diff --check` passed.
