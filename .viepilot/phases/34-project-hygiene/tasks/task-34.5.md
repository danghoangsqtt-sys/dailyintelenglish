# Task 34.5: Clean Ruff check (ENH-026)

## Plan

Remove the unused imports: `threading` in `scripts/run_gate_b12.py`, `sys` in `tests/test_shot_faces.py`, `time` in
`tests/test_shot_library_browser.py`. Re-run Ruff. Fix a new finding the same way only if it is an unused import; log anything else.

## Paths

- `scripts/run_gate_b12.py`
- `tests/test_shot_faces.py`
- `tests/test_shot_library_browser.py`

## Verification

`python -m ruff check app scripts tests` exits 0; the two test files still pass.
