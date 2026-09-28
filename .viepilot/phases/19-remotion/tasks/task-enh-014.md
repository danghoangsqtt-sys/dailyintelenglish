# Task ENH-014 — Runner outro heuristic: widen markers + use `has_outro_last3` for gate decision

- **Status:** not started (doc-first card, awaiting Coder pickup — optional, low-priority filler)
- **Owner:** Coder
- **Priority:** P2 (medium per ENH-014, was flagged "must be decided before the next gate" —
  no next gate scheduled before T6 report, so effectively low-risk to close now while Coder
  is standby)
- **Dependency:** none
- **Controlling context:** `.viepilot/requests/ENH-014.md`; Phase 18 Gate B-11 report
  (`docs/operations/phase18-gate-b11.md`); already-existing `_has_outro_in_last_n`
  computation in `scripts/run_ai_operational_trial.py:310-322`
- **Not part of Phase 19 numbering:** report-window filler task; sits in the phase folder
  for admin convenience only.

## Goal

Fix the runner's outro heuristic false negatives that Gate B-11 flagged (2/5 B1 scripts
scored as "no outro" despite having real sign-off endings). The infrastructure to fix this
is already in the file — `_has_outro_in_last_n` was added in Task 17.2 diagnostic but never
wired into the gate decision. This task widens the marker set with the real missed phrases
AND switches the primary gate signal from single-last-line to last-3-lines.

**No API calls needed.** Pure Python + unit tests. No runner rerun. Coder can edit the
source (PM-only prohibition is about *running* the trial, not editing).

## Real evidence (verified from PM's read of Gate B-11 evidence 2026-09-28)

Missed real sign-off phrases from Gate B-7, B-8, B-11 evidence:
- "We truly **appreciate you tuning in** … look forward to seeing you in our **next session**"
- "Thank you for being part of our community … welcoming you back … **next week**"
- (Task 17.2 already recorded similar B-7 run 4, B-8 run 5 false negatives)

These are all real sign-offs a human reader would immediately recognize. The heuristic just
lacks the phrases.

## Allowed files

- **Modify** `scripts/run_ai_operational_trial.py`:
  - `_OUTRO_LINE_MARKERS` tuple (line ~291): widen with markers derived from the real
    missed phrases (see D19.ENH14-a below).
  - `analyze_script` return + the aggregate that consumes `has_outro`: switch the
    primary gate signal from `has_outro` (single last line) to `has_outro_last3` (last 3
    lines). Keep the single-last-line value in the record for backward-compat with older
    evidence JSONs; add a new top-level `outro_present_last3` alias in the aggregate so
    slide-worthy summary reads correctly.
- **New** `tests/test_run_ai_operational_trial_outro.py` — unit tests for `_has_outro`
  and `_has_outro_in_last_n` using the real B-7 / B-8 / B-11 endings verbatim. Assert
  every real ending returns `True` under the widened markers. Include one negative test
  (a mid-script small-talk line with no sign-off markers) to prove the heuristic doesn't
  overfire.
- `CHANGELOG.md` — one bullet under `[Unreleased]` / a new "Fixed" section.

**Not allowed:** any file under `app/`, `frontend/`, `video-renderer/`. No live runner
execution (that stays PM-only per your brief).

## Design decisions (Coder, doc-first — commit under `docs(review)` before code)

### D19.ENH14-a: Marker widening — which phrases

Recommend adding these substring markers to `_OUTRO_LINE_MARKERS`, each grounded in a
real observed ending:
- `"tuning in"` (from B-11: "appreciate you tuning in")
- `"joining us"` (common sign-off pattern)
- `"welcoming you back"` (from B-11)
- `"look forward"` (from B-11: "look forward to seeing you")
- `"appreciate you"` (from B-11: "truly appreciate you")
- `"next week"` (common — "see you next week")
- `"next episode"` / `"next session"` / `"next time"` (per ENH-014 proposal)

Cite the real ending text for each marker you add. If a proposed marker doesn't have
a real observed example, don't add it — the current markers were chosen based on real
sign-offs, this widening should hold the same discipline.

Justify why each marker is safe from false positives (e.g. "tuning in" is unlikely to
appear mid-script small-talk; "next week" could false-positive on future-tense mentions
inside dialogue — but combined with the last-3-lines restriction the false-positive risk
stays low). If any marker looks risky, drop it or move to a stricter regex.

### D19.ENH14-b: Which field becomes the gate signal

Two paths:
- (i) **Rename**: `has_outro` field now holds the last-3-lines value; delete the
  single-last-line variant. Cleaner but breaks any past-evidence-reader that expects the
  old semantics.
- (ii) **Add alongside**: keep `has_outro` (single-last, backward-compat) and
  `has_outro_last3` (already exists); rewire the gate-aggregate decision to consume
  `has_outro_last3` while both fields continue to be recorded per-run.

Recommend (ii) — it's additive, doesn't break `--reaggregate` on older evidence files
(a real feature the runner supports), and makes the semantic change visible in the
per-run record.

### D19.ENH14-c: Test-data setup

- Use `pytest.mark.parametrize` with real B-7, B-8, B-11 ending texts as test cases.
- If you don't have the exact real text handy, cite in the design commit whichever
  gate-evidence JSON files you'll read to extract them, or paste the exact strings from
  the ENH-014 request card and Gate B-11 report.
- One negative test: a mid-script line that shouldn't trigger. Recommend picking one
  from an actual generated script (any of the Gate B-11 evidence's non-last lines) —
  proves the heuristic doesn't false-positive on real dialogue.

### D19.ENH14-d: Verification without running the trial

- Unit tests (`pytest tests/test_run_ai_operational_trial_outro.py`) exercise the
  functions directly. No live server, no API calls, no GPU.
- `ruff check .` clean.
- Full suite still 1182/1182 (unchanged existing suite + N new tests).
- No `--reaggregate` needed — the fix is forward-looking, evidence-format-compatible
  because it uses an existing field.

## Verification

- New unit tests pass, revert-and-confirm-failure done on the widening (revert one added
  marker, confirm the specific real-ending test that needed it now fails).
- Full suite green.
- ruff clean.
- `app/` untouched.

## Evidence (Coder handover)

- Two shas (design + implementation).
- List of markers added with the real ending text each is grounded in.
- Full-suite + ruff lines.
- Which gate-signal field wiring path chosen (D19.ENH14-b i or ii).

## Definition of done

- Two commits, design before implementation.
- Widened markers + gate signal wired to `has_outro_last3`.
- Unit tests + revert-and-confirm-failure done.
- All checks green. `app/` untouched.
- Handover per Evidence checklist.

## PM note

This is a nice-to-close item, not a must-close. If it's more work than it looks, or if
you'd rather stay idle to reserve capacity for a possible T6 assist (backup video record,
sample regeneration), flag it and I'll defer. **The T6 report doesn't depend on this
being done** — the AI-speed story rests on Gate B-11 numbers which are already accepted.
