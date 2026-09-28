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

## Design decisions — Coder answers (2026-09-28)

**Grounding method:** read the real evidence directly rather than trusting paraphrases --
`docs/operations/phase18-gate-b11.md` (Gate B-11's committed report), the real (gitignored,
locally present, read-only) evidence JSONs under `data/quality_reviews/phase15/gate-b8/` and
`.../gate-b11/`, and for Gate B-8 specifically the real per-line script text from its
`trial-data/app.db` (a throwaway trial DB, not the real `data/app.db` -- reading it carries
none of the real-DB write restrictions).

**Card-vs-reality discrepancy found:** the ENH-014 request card's own summary paraphrases
Gate B-7 run 4's ending as "...we will be back very soon next episode," but Task 17.2's card
(which verified it directly against `trial-data/app.db`) records the real last 3 lines as
ending in "...your future health and happiness depends entirely on the choices you make right
now" -- no "next episode" anywhere. Task 17.2's version is the DB-verified one; the request
card's phrasing looks like an earlier, unverified paraphrase. **"next episode" is not added**
as a marker -- no real observed instance survives verification, and the card's own D19.ENH14-a
discipline says not to add a marker without one. "next session" (Gate B-11 run 1, verified
below) is added instead -- a real, different phrase that happens to cover the same kind of
sign-off.

### D19.ENH14-a: Marker widening -- verified per-case, not just per-phrase

Re-derived exactly which cases need *new markers* versus which are already fixed by the
last-3-lines switch alone, using the real recorded `has_outro`/`has_outro_last3` values:

| Case | `has_outro` | `has_outro_last3` | Needs new markers? |
|---|---|---|---|
| Gate B-7 run 4 | False | **True** (existing "take care", 2nd-to-last line) | No -- last3 switch alone fixes it |
| Gate B-8 run 5 | False | **True** (existing "thank you for", 2nd-to-last line, verified against real `trial-data/app.db` text: *"Thank you for listening to Daily Intel English Studio..."*) | No -- last3 switch alone fixes it |
| Gate B-11 run 2 | False | **True** (real evidence JSON confirms; report's own §2 parenthetical already said so) | No, but markers added anyway for defense-in-depth (see below) |
| **Gate B-11 run 1** | False | **False** | **Yes -- the only case where new markers are actually required.** Neither `has_outro` nor `has_outro_last3` catch it with today's markers; confirmed directly from the real evidence JSON (`data/quality_reviews/phase15/gate-b11/gate-b11-20260926T042435Z.json`, run 1: both flags `false`). |

New markers added to `_OUTRO_LINE_MARKERS`, each cited against real text
(`docs/operations/phase18-gate-b11.md` §2, PM-verified against the real endings):

- `"tuning in"` -- Run 1: *"We truly appreciate you **tuning in** to explore these health
  concepts with us."* Required for Run 1 (neither current flag catches it without this).
- `"look forward"` -- Run 1: *"We **look forward** to seeing you in our next session..."*
  Also required for Run 1 (belt-and-suspenders with "tuning in" -- either alone now fixes
  Run 1, both are real).
- `"next session"` -- Run 1: *"...in our **next session** at Daily Intel English Studio."*
- `"appreciate you"` -- Run 1: *"We truly **appreciate you** tuning in..."* Redundant with
  "tuning in" for this specific case, but a distinct real phrase (a future ending could say
  "we appreciate you" without "tuning in") -- kept for the same reason "tuning in" and "look
  forward" both stay even though either alone fixes Run 1.
- `"joining us"` -- Run 2: *"...for **joining us** on this enlightening episode..."* Not
  required (Run 2 already passes via last3 + existing "thank you for"), added for
  defense-in-depth per the card's own suggested list.
- `"welcoming you back"` -- Run 2: *"...we eagerly anticipate **welcoming you back** here..."*
  Same -- defense-in-depth, not required for any currently-known case.
- `"next week"` -- Run 2: *"...for another session **next week**."* Same.

**False-positive risk, checked per marker:**
- `"tuning in"`, `"look forward"`, `"next session"`, `"appreciate you"`, `"welcoming you
  back"` -- low risk; none are common mid-dialogue small-talk phrasing in this app's B1
  small-talk/interview/debate scripts, and all are scoped to the last 3 lines only.
- `"joining us"` -- the existing **intro** marker list already has `"thanks for joining"`
  (`intro_markers`, line ~393), but that's checked against the *first* line only, and this
  new outro marker is checked against the *last 3* lines only -- no overlap possible in a
  script with more than 3 lines (true for every real B1 8-minute script; the word-count gate
  alone requires far more than 3 lines).
- `"next week"` -- the one genuinely riskier marker (a mid-script line could plausibly say
  "let's talk about this next week" as forward-looking small talk, not a sign-off). Real
  mitigation: it only matters within the last 3 lines (D19.ENH14-b switches the gate signal
  to `has_outro_last3`), and a real B1 script's last 3 lines are dialogue wind-down content
  by construction (Task 17.2's own N6 sign-off requirement). Kept as a substring match per
  the card's recommendation, not tightened to a regex -- the last-3-lines scope is already
  the mitigation the card itself proposed.

### D19.ENH14-b: Gate-signal wiring -- (ii), additive

Chosen **(ii)**, exactly as the card recommends: `checks["outro_present"]` (the field that
feeds `all_checks_pass`) switches from `has_outro` to `has_outro_last3`. Both `has_outro` and
`has_outro_last3` keep being recorded in the per-run dict, unchanged in shape -- `--reaggregate`
on an older evidence file still works (every field already read via `.get(...)`, confirmed by
reading `compute_matrix_aggregates`'s own docstring: "every field is read with `.get(...)`,
never assumed present").

**Aggregate alias, one real gap found:** `compute_matrix_aggregates` currently has **no**
outro-related field at all (confirmed by reading the whole function) -- there's nothing to
"switch," only something to add. New key: **`outro_present_last3_rate`** (not the card's bare
`outro_present_last3` -- named with the `_rate` suffix to match every other aggregate's own
naming convention: `completion_rate`, `content_pass_rate`, `call_fallback_rate`,
`job_fallback_rate`). Computed the same way as `content_pass_rate`: fraction of `completed`
runs where `(r.get("content") or {}).get("has_outro_last3")` is true, `None` when there are no
completed runs (matching every other rate field's own `if completed else None` guard).

### D19.ENH14-c: Test-data setup

`pytest.mark.parametrize` over the real endings verified above:
- Gate B-11 run 1 (needs new markers): exact quoted text from `phase18-gate-b11.md` §2. The
  report doesn't preserve the original per-line split (the real project no longer exists in
  any locally-present DB -- checked `data/app.db` read-only, not found; Gate B-11 was a
  cloud-first run with no retained `trial-data/` snapshot, unlike B-7/B-8). The ellipsis in
  the report's own quote is treated as the real line boundary (consistent with how Run 2's
  same-report quote is confirmed by the evidence JSON to span 2 lines) -- disclosed here as
  an inference from real, committed text, not fabricated content.
- Gate B-11 run 2: same source, same line-boundary inference.
- Gate B-8 run 5: real per-line text fetched directly from `trial-data/app.db` (read-only),
  verified above -- exact, not inferred.
- Gate B-7 run 4: real per-line text already verified and quoted in Task 17.2's own card,
  reused verbatim here rather than re-fetched.
- **Negative test:** a real *non-last* line from Gate B-8 run 5's own script (fetched in the
  same read-only query): `"That sounds like a great idea for all of us to start right now and
  see the difference in just a few weeks."` -- real B1 small-talk dialogue, asserted to NOT
  trigger `_has_outro`/`_has_outro_in_last_n`, proving the widened marker set doesn't overfire
  on ordinary content.

### D19.ENH14-d: Verification without running the trial

Exactly as the card specifies -- direct unit-test calls to `_has_outro`/`_has_outro_in_last_n`,
no server, no network, no GPU, no `--reaggregate` needed (additive field, old evidence files
unaffected). `ruff check .` + full suite (1182 baseline + N new) confirmed at implementation
time.

## PM review — APPROVED (2026-09-28, session a01f96)

All four findings accepted verbatim: per-case verification via the trial DBs (safe territory,
distinct from the real `data/app.db`) confirmed as the right discipline over assuming the
card's switch-alone-fixes-all narrative; trusting Task 17.2's DB-verified quote over the
ENH-014 request's own paraphrase confirmed correct (not adding "next episode" without a
surviving real instance); `outro_present_last3_rate` naming approved (matches existing
aggregate `_rate` convention); Gate B-11 line-boundary inference from the committed,
owner-accepted report text confirmed as grounding-in-evidence, not fabrication -- call it out
openly in the test docstring, not just the design doc. No changes requested.

Proceed to implementation.

## PM note

This is a nice-to-close item, not a must-close. If it's more work than it looks, or if
you'd rather stay idle to reserve capacity for a possible T6 assist (backup video record,
sample regeneration), flag it and I'll defer. **The T6 report doesn't depend on this
being done** — the AI-speed story rests on Gate B-11 numbers which are already accepted.
