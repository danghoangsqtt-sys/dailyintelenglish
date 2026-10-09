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

- [ ] Insert beats are explicitly 3–6 seconds, action-led and not gratuitous.
- [ ] The pack has all D72 activities, filename, primary prompt, negative constraints and 16:9 framing rules.
